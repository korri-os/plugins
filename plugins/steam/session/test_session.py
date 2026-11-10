"""Run the real session state machine with filesystem IPC and real processes."""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).parent
TOOL = "proton-cachyos-11.0-20260601-slr-arm64"


def program(path, source):
    path.write_text(f"#!{sys.executable}\n" + source)
    path.chmod(0o755)


class SteamSessionTests(unittest.TestCase):
    def run_session(self, behavior, seeded=True, setup=None, installed=True, shm=None,
                    copy_behavior=None, platform="aarch64-linux", notify_socket=True, short_deadlines=False, notify_exit=0):
        arm = platform == "aarch64-linux"
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.root = root
        home = root / "steam"
        (home / "userdata/123/config").mkdir(parents=True)
        if installed:
            (home / "steamapps").mkdir()
            (home / "steamapps/appmanifest_401710.acf").write_text(
                '"AppState"\n{\n\t"appid"\t\t"401710"\n\t"StateFlags"\t\t"4"\n}\n')
        if setup:
            setup(home)
        if seeded and arm:
            (home / "steamrtarm64").mkdir()
            client = home / "steamrtarm64/steam"
            client.touch()
            client.chmod(0o755)
        (root / "bin").mkdir()
        program(root / "bin/systemd-notify", """import os
from pathlib import Path
import sys
with (Path(os.environ["STEAM_HOME"]) / "statuses").open("a") as stream:
    stream.write(sys.argv[1] + "\\n")
sys.exit(int(os.environ["NOTIFY_EXIT"]))
""")
        if copy_behavior:
            # Exercise the real cp after a controlled filesystem mutation at
            # the copy boundary. Production has no test hook or timing knob.
            program(root / "bin/cp", f"""import os
from pathlib import Path
import sys
home = Path(os.environ["STEAM_HOME"])
args = sys.argv[1:]
if '.korri/' in args[-1] and '.tmp.' in args[-1]:
    if {copy_behavior!r} == 'delete-source':
        (home / 'package/steam_client_steamdeck_stable_linuxarm64.manifest').unlink(missing_ok=True)
    else:
        args[-2] = str(home / 'missing-copy-source')
os.execv({shutil.which('cp')!r}, [{shutil.which('cp')!r}, *args])
""")
        (root / "fex-config").mkdir()
        # The ready artifact directories korrid hands the launch.
        self.rootfs = root / "cache/fex/rootfs/archlinux-fixture"
        self.proton = root / "cache/proton/cachyos/fixture-arm64"
        self.rootfs.mkdir(parents=True)
        self.proton.mkdir(parents=True)
        client = root / "bin" / ("steam-arm64-fhs" if arm else "steam")
        program(client, (HERE / "fixtures/session-client.py").read_text())
        program(root / "bin/steam-arm64-seed", (HERE / "fixtures/seed.py").read_text())
        program(root / "bin/steam-vdf-settings",
                (HERE / "vdf-settings.py").read_text().replace("@protonToolName@", TOOL))
        script = (HERE / "steam-session.sh").read_text()
        for placeholder in ("helpers", "settings"):
            script = script.replace(f"@{placeholder}@", str(root))
        # The values packages/default.nix substitutes for each platform.
        for placeholder, value in {
            "steamClient": str(client),
            "usesFex": "1" if arm else "0",
            "steamBeta": "steamdeck_stable" if arm else "",
            "desktopScaling": "1.5" if arm else "",
        }.items():
            script = script.replace(f"@{placeholder}@", value)
        script = script.replace("@protonToolName@", TOOL)
        script = script.replace("@failure@", str(HERE.resolve() / "steam-failure.sh"))
        # Exercise timeout branches without adding timing knobs to production.
        if short_deadlines:
            for seconds in (600, 180, 3600):
                script = script.replace(f"SECONDS + {seconds}", "SECONDS + 2")
        # Never touch the host's real shared memory.
        (root / "shm").mkdir()
        script = script.replace("/dev/shm", str(root / "shm"))
        if shm:
            shm(root / "shm")
        path = root / "session.sh"
        path.write_text(script)
        started = time.monotonic()
        result = subprocess.run(
            ["bash", str(path), "401710"], check=False, timeout=60, capture_output=True, text=True,
            env={
                **os.environ, "STEAM_HOME": str(home), "HOME": str(root), "CLIENT_BEHAVIOR": behavior,
                "PATH": str(root / "bin") + os.pathsep + os.environ["PATH"],
                "KORRI_PROTON_CACHYOS": str(self.proton),
                "NOTIFY_SOCKET": str(root / "notify") if notify_socket else "",
                "NOTIFY_EXIT": str(notify_exit),
                **({"KORRI_FEX_CONFIG": str(root / "fex-config"),
                    "KORRI_FEX_ROOTFS": str(self.rootfs)} if arm else {}),
            },
        )
        return result, home, time.monotonic() - started

    def assert_steps(self, home, keys):
        self.assertEqual((home / "statuses").read_text().splitlines(),
                         [f"--status=korri-step: {key}" for key in keys])

    def test_no_notify_socket_sends_no_status(self):
        result, home, _ = self.run_session("game", notify_socket=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((home / "statuses").exists())

    def test_creating_process_reports_game_before_game_process_added(self):
        result, home, _ = self.run_session("creating-process")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_steps(home, ["start-steam", "sign-in", "game"])
        self.assertIn("--status=korri-step: game", (home / "creating-status").read_text())

    def test_creating_process_falls_back_to_game_process_added(self):
        result, home, _ = self.run_session("no-creating-process")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_steps(home, ["start-steam", "sign-in", "game"])

    def test_ready_artifacts_configure_fex_and_proton_before_seeding(self):
        result, home, _ = self.run_session("game", seeded=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        # The seed and the client both see the rootfs korrid readied.
        seed = json.loads((home / "seed.json").read_text())
        self.assertEqual(seed, {"FEX_ROOTFS": str(self.rootfs)})
        client = json.loads((home / "client-env.json").read_text())
        self.assertEqual(client["FEX_ROOTFS"], str(self.rootfs))
        self.assertEqual(client["FEX_APP_CONFIG_LOCATION"], str(self.root / "fex-config") + "/")
        self.assertEqual(os.readlink(home / "compatibilitytools.d" / TOOL), str(self.proton))
        self.assertIn(f'"{TOOL}"', (home / "config/config.vdf").read_text())

    def test_x86_64_points_the_bootstrap_at_steam_home_without_fex(self):
        result, home, _ = self.run_session("game", platform="x86_64-linux")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((home / "seed.json").exists())
        self.assertFalse((home / "fex-data").exists())
        client = json.loads((home / "client-env.json").read_text())
        self.assertEqual(client, {"FEX_ROOTFS": None, "FEX_APP_CONFIG_LOCATION": None})
        for link in (self.root / ".steam/steam", self.root / ".steam/root",
                     self.root / ".local/share/Steam"):
            self.assertEqual(os.readlink(link), str(home))
        self.assertEqual(os.readlink(home / "compatibilitytools.d" / TOOL), str(self.proton))
        # The public channel: no channel file, no ARM64 manifest copy.
        self.assertFalse((home / "package/beta").exists())
        self.assertFalse((home / ".korri").exists())
        self.assertIn("AppID 401710 exited", result.stderr)
        self.assertTrue((home / "shutdown").exists())

    def test_x86_64_refuses_a_separate_steam_directory(self):
        def separate(home):
            (home.parent / ".local/share/Steam").mkdir(parents=True)
        result, home, _ = self.run_session("game", platform="x86_64-linux", setup=separate)
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertIn("is a separate Steam directory", result.stderr)
        self.assertFalse((home / "forwards").exists())

    def test_game_exit_waits_for_process_and_stops_steam(self):
        result, home, duration = self.run_session("game")
        self.assertEqual(result.returncode, 0, result.stderr)
        # An already seeded home still gets the link to the ready tool.
        self.assertFalse((home / "seed.json").exists())
        self.assertEqual(os.readlink(home / "compatibilitytools.d" / TOOL), str(self.proton))
        self.assert_steps(home, ["start-steam", "sign-in", "game"])
        self.assertGreaterEqual(duration, 2)
        self.assertIn("AppID 401710 exited", result.stderr)
        self.assertTrue((home / "shutdown").exists())
        self.assertEqual((home / "forwards").read_text(), "1")

    def test_restart_42_before_game_reforwards_appid(self):
        result, home, _ = self.run_session("restart")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("update restart (42)", result.stderr)
        self.assert_steps(home, ["start-steam", "sign-in", "game"])
        self.assertEqual((home / "forwards").read_text(), "2")
        self.assertTrue((home / "shutdown").exists())

    def test_forward_exit_42_restarts_and_reforwards_appid(self):
        result, home, _ = self.run_session("forward-restart")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((home / "forwards").read_text(), "2")
        self.assertIn("re-forwarding AppID (1/3)", result.stderr)
        self.assertTrue((home / "shutdown").exists())

    def test_forward_error_recovers_when_the_client_also_restarted(self):
        result, home, _ = self.run_session("forward-client-restart")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((home / "forwards").read_text(), "2")
        self.assertTrue((home / "shutdown").exists())

    def test_forward_restarts_stop_after_three_reforwards(self):
        result, home, _ = self.run_session("forward-restart-always")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertEqual((home / "forwards").read_text(), "4")
        self.assertIn("restart re-forward limit (3) exceeded", result.stderr)
        self.assertTrue((home / "shutdown").exists())

    def test_update_blocks_forward_even_when_a_ready_line_is_present(self):
        result, home, _ = self.run_session("update")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("startup update observed", result.stderr)
        self.assert_steps(home, ["start-steam", "update", "sign-in", "game"])
        self.assertTrue((home / "update-complete").exists())

    def test_dropped_forward_is_sent_again(self):
        result, home, duration = self.run_session("drop-first")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("did not act on AppID 401710; forwarding again (1/3)", result.stderr)
        self.assertEqual((home / "forwards").read_text(), "2")
        self.assertGreaterEqual(duration, 20)

    def test_uninstalled_app_waits_for_the_install(self):
        result, home, _ = self.run_session("game", installed=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AppID 401710 is not installed; waiting up to 3600 s", result.stderr)
        self.assert_steps(home, ["start-steam", "sign-in", "install", "game"])

    def test_a_question_from_steam_extends_the_launch_window(self):
        result, home, _ = self.run_session("eula")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_steps(home, ["start-steam", "sign-in", "answer", "game"])
        self.assertIn("Steam is waiting for an answer about AppID 401710; waiting up to 3600 s",
                      result.stderr)
        self.assertIn("AppID 401710 exited", result.stderr)

    def test_channel_and_installed_manifest_survive_the_client_deleting_them(self):
        manifest = '"linuxarm64"\n{\n\t"version"\t\t"1791918634"\n}\n'

        def installed_client(home):
            (home / "package").mkdir()
            (home / "package/beta").write_text("\n")
            (home / "package/steam_client_steamdeck_stable_linuxarm64.installed").write_text("x\n")
            (home / "package/steam_client_steamdeck_stable_linuxarm64.manifest").write_text(manifest)

        result, home, _ = self.run_session("game", setup=installed_client)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((home / "beta-seen").read_text(), "steamdeck_stable\n")
        self.assertEqual((home / "manifest-seen").read_text(), manifest)
        # The client deleted it during the session; the saved copy remains.
        package = home / "package/steam_client_steamdeck_stable_linuxarm64.manifest"
        self.assertFalse(package.exists())
        saved = home / ".korri/steam_client_steamdeck_stable_linuxarm64.manifest"
        self.assertEqual(saved.read_text(), manifest)

        def deleted_manifest(next_home):
            installed_client(next_home)
            (next_home / "package/steam_client_steamdeck_stable_linuxarm64.manifest").unlink()
            (next_home / ".korri").mkdir()
            (next_home / ".korri/steam_client_steamdeck_stable_linuxarm64.manifest").write_text(manifest)

        result, home, _ = self.run_session("game", setup=deleted_manifest)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("restoring the installed Steam client manifest", result.stderr)
        self.assertEqual((home / "manifest-seen").read_text(), manifest)

    def test_manifest_deletion_between_open_and_copy_retains_the_saved_bytes(self):
        manifest = '"linuxarm64"\n{\n\t"version"\t\t"1791918634"\n}\n'

        def installed_client(home):
            (home / "package").mkdir()
            (home / "package/steam_client_steamdeck_stable_linuxarm64.installed").write_text("x\n")
            (home / "package/steam_client_steamdeck_stable_linuxarm64.manifest").write_text(manifest)

        result, home, _ = self.run_session("game", setup=installed_client,
                                           copy_behavior="delete-source")
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = home / ".korri/steam_client_steamdeck_stable_linuxarm64.manifest"
        self.assertEqual(saved.read_text(), manifest)
        result, _, _ = self.run_session("game", setup=installed_client, copy_behavior="failure")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertIn("missing-copy-source", result.stderr)

    def test_leftover_steam_shared_memory_is_removed(self):
        uid = os.getuid()
        names = [f"u{uid}-Shm_0badc0de", f"u{uid}-ValveIPCSharedObj-Steam", "fex-1234-stats"]

        def leftovers(shm):
            for name in names + ["pulse-shm-1"]:
                (shm / name).write_text("x")

        result, _, _ = self.run_session("game", shm=leftovers)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in (self.root / "shm").iterdir()), ["pulse-shm-1"])

    def test_processes_steam_started_are_killed_when_the_session_ends(self):
        result, home, _ = self.run_session("leftover")
        self.assertEqual(result.returncode, 0, result.stderr)
        pid = int((home / "leftover.pid").read_text())
        deadline = time.monotonic() + 5
        while Path(f"/proc/{pid}").exists() and time.monotonic() < deadline:
            # Reap it if it is our zombie grandchild's zombie; otherwise wait.
            state = Path(f"/proc/{pid}/status").read_text() if Path(f"/proc/{pid}/status").exists() else ""
            if "State:\tZ" in state:
                break
            time.sleep(0.1)
        status = Path(f"/proc/{pid}/status")
        self.assertTrue(not status.exists() or "State:\tZ" in status.read_text(),
                        "a SIGTERM-ignoring process with SteamAppId survived the session")

    def test_repeated_sigterm_still_kills_leftovers(self):
        # Prepare the same tree run_session builds, but drive the process.
        self.run_session("game")
        home = self.root / "steam"
        for name in ("shutdown", "forwards", "leftover.pid"):
            (home / name).unlink(missing_ok=True)
        env = {
            **os.environ, "STEAM_HOME": str(home), "HOME": str(self.root),
            "CLIENT_BEHAVIOR": "leftover-hold",
            "PATH": str(self.root / "bin") + os.pathsep + os.environ["PATH"],
            "NOTIFY_SOCKET": str(self.root / "notify"),
            "NOTIFY_EXIT": "0",
            "KORRI_FEX_CONFIG": str(self.root / "fex-config"),
            "KORRI_FEX_ROOTFS": str(self.rootfs),
            "KORRI_PROTON_CACHYOS": str(self.proton),
        }
        session = subprocess.Popen(["bash", str(self.root / "session.sh"), "401710"],
                                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: session.poll() is None and session.kill())
        deadline = time.monotonic() + 30
        while not (home / "leftover.pid").exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        pid = int((home / "leftover.pid").read_text())
        session.send_signal(signal.SIGTERM)
        time.sleep(0.3)
        session.send_signal(signal.SIGTERM)
        session.communicate(timeout=30)
        status = Path(f"/proc/{pid}/status")
        deadline = time.monotonic() + 5
        while status.exists() and "State:\tZ" not in status.read_text() and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertTrue(not status.exists() or "State:\tZ" in status.read_text(),
                        "a second SIGTERM cut the cleanup short")

    def test_setgid_is_cleared_from_the_steam_home(self):
        def setgid_tree(home):
            (home / "steamapps/common").mkdir(parents=True, exist_ok=True)
            for directory in (home, home / "steamapps", home / "steamapps/common"):
                try:
                    directory.chmod(0o2770)
                except PermissionError:
                    # The Nix build sandbox refuses setgid, like the game unit.
                    self.skipTest("this sandbox refuses setgid directories")

        result, home, _ = self.run_session("game", setup=setgid_tree)
        self.assertEqual(result.returncode, 0, result.stderr)
        for directory in (home, home / "steamapps", home / "steamapps/common"):
            self.assertFalse(directory.stat().st_mode & 0o2000, directory)

    def assert_refusal(self, home, reason):
        statuses = (home / "statuses").read_text().splitlines()
        self.assertEqual(statuses[-1], f"--status=plugin-launch: {reason}")
        self.assertLessEqual(len(reason), 160)

    def test_launch_error_reports_steam_reason_before_cleanup(self):
        result, home, _ = self.run_session("launch-error")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assert_refusal(home, "Steam: this game is not owned by the signed-in account")
        self.assertTrue((home / "shutdown").exists())

    def test_content_and_process_logs_report_current_app_only(self):
        for behavior, expected in (
            ("content-error", "Steam: the game update failed because Steam could not write to disk"),
            ("process-error", "Steam: the game executable is missing"),
            ("other-app-error", "Signing in failed"),
        ):
            with self.subTest(behavior=behavior):
                result, home, _ = self.run_session(behavior)
                self.assertEqual(result.returncode, 126, result.stderr)
                self.assert_refusal(home, expected)

    def test_old_errors_are_ignored_and_truncated_logs_are_read(self):
        def old_errors(home):
            (home / "logs").mkdir()
            for log in ("console_log.txt", "content_log.txt", "gameprocess_log.txt"):
                (home / "logs" / log).write_text(
                    'GameAction [AppID 401710, ActionID 1] : LaunchApp failed with error "No subscription"\n' * 10)

        result, home, _ = self.run_session("forward-error", setup=old_errors)
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assert_refusal(home, "Signing in failed")
        for behavior in ("truncated-error", "replaced-error"):
            with self.subTest(behavior=behavior):
                result, home, _ = self.run_session(behavior, setup=old_errors)
                self.assertEqual(result.returncode, 126, result.stderr)
                self.assert_refusal(home, "Steam: the game update failed because Steam could not write to disk")

    def test_client_exit_and_login_timeout_have_plain_refusals(self):
        result, home, _ = self.run_session("client-exit")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assert_refusal(home, "Steam: the Steam client exited")

        def signed_out(home):
            shutil.rmtree(home / "userdata")

        result, home, _ = self.run_session("game", setup=signed_out, short_deadlines=True)
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assert_refusal(home, "Steam: still waiting for sign-in after 10 minutes")

    def test_launch_timeout_reports_update_state_or_last_step(self):
        for behavior, expected in (("no-launch", "Signing in failed"),
                                   ("update-required", "Steam: this game needs an update")):
            with self.subTest(behavior=behavior):
                result, home, _ = self.run_session(behavior, short_deadlines=True)
                self.assertEqual(result.returncode, 124, result.stderr)
                self.assert_refusal(home, expected)
                self.assertTrue((home / "shutdown").exists())

    def test_notify_failure_does_not_mask_the_failure_or_skip_cleanup(self):
        result, home, _ = self.run_session("launch-error", notify_exit=1)
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assert_refusal(home, "Steam: this game is not owned by the signed-in account")
        self.assertTrue((home / "shutdown").exists())
        result, home, _ = self.run_session("launch-error", notify_socket=False)
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertFalse((home / "statuses").exists())

    def test_forward_failure_is_classified_and_stops_steam(self):
        result, home, _ = self.run_session("forward-error")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertIn("AppID forward failed", result.stderr)
        self.assertTrue((home / "shutdown").exists())


if __name__ == "__main__":
    unittest.main()

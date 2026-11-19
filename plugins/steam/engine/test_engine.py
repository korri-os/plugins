"""steam-engine-session against a real FIFO, a host stand-in process and real files.

The host stand-in reads the session's commands from the channel FIFO and
answers with the host's event lines (korri-steam-host's own unit tests cover
the host). Nothing here reaches Steam, a display or the network.
"""
import json
import os
import re
import shutil
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).parent
STEAM = HERE.parent

HOST = r'''
import json, os, sys, time
channel = sys.argv[1]
behavior = sys.argv[2]
events = os.path.join(channel, "events.jsonl")
def emit(**event):
    with open(events, "a") as out:
        out.write(json.dumps(event, separators=(",", ":")) + "\n")
if behavior == "mismatch":
    emit(event="engine_mismatch", expected="aa", found="bb")
    sys.exit(1)
emit(event="logon_state", state=4, logged_on=True, connected=True, offline=False)
while True:
    with open(os.path.join(channel, "commands")) as fifo:
        for line in fifo:
            with open(os.path.join(channel, "received"), "a") as seen:
                seen.write(line)
            verb, word = line.split()
            if verb == "refused":
                emit(event="launch_refused", reason=word)
                continue
            appid = int(word)
            emit(event="command", command=verb, appid=appid, queued=False)
            if verb == "install" and behavior == "install-fails":
                emit(event="app_job_finished", appid=appid, kind="install",
                     result="install_refused", state=1, seconds=0)
            elif verb == "install":
                emit(event="app_job_started", appid=appid, kind="install")
                emit(event="app_progress", appid=appid, kind="install", state=1026)
                time.sleep(0.3)
                emit(event="app_job_finished", appid=appid, kind="install",
                     result="installed", state=4, seconds=1)
            elif verb == "launched":
                emit(event="sync_started", appid=appid, kind="launch")
                result = "conflict" if behavior == "conflict" else "synchronized"
                emit(event="sync_finished", appid=appid, kind="launch", result=result, state=2, seconds=1)
            elif verb == "exited":
                sys.exit(0)
'''


def appinfo(apps):
    """An appinfo.vdf (format 0x07564429) with the given apps' key/values."""
    strings = []

    def key(name):
        if name not in strings:
            strings.append(name)
        return struct.pack("<I", strings.index(name))

    def obj(values):
        out = b""
        for name, value in values.items():
            if isinstance(value, dict):
                out += b"\x00" + key(name) + obj(value)
            else:
                out += b"\x01" + key(name) + value.encode() + b"\x00"
        return out + b"\x08"

    records = b""
    for appid, values in apps.items():
        body = bytes(4 + 4 + 8 + 20 + 4 + 20) + obj({"appinfo": values})
        records += struct.pack("<II", appid, len(body)) + body
    records += struct.pack("<I", 0)
    table = 16 + len(records)
    out = struct.pack("<IIq", 0x07564429, 1, table) + records
    out += struct.pack("<I", len(strings)) + b"".join(s.encode() + b"\x00" for s in strings)
    return out


def launch_config(*entries, depots=None):
    app = {"common": {"name": "Game", "type": "Game"},
           "config": {"installdir": "Game", "launch": {str(i): e for i, e in enumerate(entries)}}}
    if depots:
        app["depots"] = {str(d): {"config": {"oslist": os}} if os else {} for d, os in depots.items()}
    return app


# VVVVVV's shape: shared 70301, Windows 70302, Linux 70303; both launch entries.
BOTH = dict(
    entries=({"executable": "bin\\game.exe", "arguments": "-x", "config": {"oslist": "windows"}},
             {"executable": "game.sh", "config": {"oslist": "linux"}}),
    depots={70301: None, 70302: "windows", 70303: "linux"},
)


def manifest_text(depots=()):
    inner = "".join(f'\t\t"{d}"\n\t\t{{\n\t\t\t"manifest"\t\t"1"\n\t\t}}\n' for d in depots)
    return ('"AppState"\n{\n\t"appid"\t\t"401710"\n\t"installdir"\t\t"Game"\n'
            f'\t"InstalledDepots"\n\t{{\n{inner}\t}}\n}}\n')


class LaunchEntryTests(unittest.TestCase):
    def pick(self, app, os_name="windows"):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "appinfo.vdf"
            path.write_bytes(appinfo({401710: app}))
            return subprocess.run(
                [sys.executable, str(HERE / "launch-entry.py"), str(path), "401710", "--os", os_name],
                capture_output=True, text=True, check=False,
            )

    def test_prefers_the_default_64_bit_windows_entry(self):
        result = self.pick(launch_config(
            {"executable": "game32.exe", "config": {"oslist": "windows", "osarch": "32"}},
            {"executable": "bin\\game.exe", "arguments": "-a \"b c\"", "config": {"oslist": "windows"}},
            {"executable": "game.sh", "config": {"oslist": "linux"}},
        ))
        self.assertEqual(result.returncode, 0, result.stderr)
        fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if not line.startswith("ARGV"))
        self.assertEqual(shlex.split(fields["EXE"]), ["bin/game.exe"])
        self.assertIn("ARGV=(-a 'b c')", result.stdout)

    def test_platforms_follow_the_installed_depots(self):
        app = launch_config(*BOTH["entries"], depots=BOTH["depots"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "appinfo.vdf"
            path.write_bytes(appinfo({401710: app}))
            manifest = Path(tmp) / "appmanifest.acf"
            for depots, order in (((70301, 70303), "linux"), ((70301, 70302), "windows linux"),
                                  ((70301,), "windows linux"), ((), "windows linux")):
                manifest.write_text(manifest_text(depots))
                result = subprocess.run(
                    [sys.executable, str(HERE / "launch-entry.py"), str(path), "401710",
                     "--platforms", str(manifest)], capture_output=True, text=True, check=True)
                self.assertEqual(result.stdout.strip(), order, depots)

    def test_no_entry_for_the_os_fails(self):
        app = launch_config({"executable": "game.sh", "config": {"oslist": "linux"}})
        self.assertNotEqual(self.pick(app).returncode, 0)
        self.assertEqual(self.pick(app, "linux").returncode, 0)


# What packages/engine.nix puts on the session program's PATH: coreutils,
# gnugrep, gnused, jq, python3, util-linux (flock); systemd-notify is faked.
SESSION_TOOLS = ["cat", "dirname", "head", "mkdir", "seq", "sleep", "stat", "tail",
                 "timeout", "tr", "grep", "sed", "jq", "python3", "flock"]


class SessionScriptTests(unittest.TestCase):
    def test_the_session_program_never_runs_a_bare_sh(self):
        for script in ("session.sh", "host-run.sh"):
            for number, line in enumerate((HERE / script).read_text().splitlines(), 1):
                code = line.split("#", 1)[0]
                self.assertIsNone(re.search(r"(^|[\s;|&(`'\"])sh(\s|$)", code),
                                  f"{script}:{number}: {line.strip()}")


class EngineSessionTests(unittest.TestCase):
    def run_session(self, behavior="normal", entry=None, both=False, installed=(), files=("bin/game.exe",)):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        channel = root / "channel"
        channel.mkdir()
        os.mkfifo(channel / "commands", 0o600)
        engine = root / "person/steam-engine"
        steam = engine / "steam"
        (steam / "appcache").mkdir(parents=True)
        (steam / "steamapps/common/Game/bin").mkdir(parents=True)
        (engine / "home").mkdir()
        (steam / "steamapps/appmanifest_401710.acf").write_text(manifest_text(installed))
        app = (launch_config(*BOTH["entries"], depots=BOTH["depots"]) if both else launch_config(
            entry or {"executable": "bin\\game.exe", "arguments": "-x", "config": {"oslist": "windows"}}))
        (steam / "appcache/appinfo.vdf").write_bytes(appinfo({401710: app}))
        game_dir = steam / "steamapps/common/Game"
        for name in files:
            (game_dir / name).write_text(
                f"#!{sys.executable}\nimport json, os, sys\n"
                f"open({str(Path(temporary.name) / 'game.json')!r}, 'w').write(json.dumps("
                "{'argv': sys.argv, 'native': True}))\n")
            (game_dir / name).chmod(0o755)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        notify = bin_dir / "systemd-notify"
        notify.write_text(f"#!{sys.executable}\nimport sys\nopen({str(root / 'statuses')!r}, 'a').write(sys.argv[1] + '\\n')\n")
        notify.chmod(0o755)
        fhs = root / "fhs/bin/korri-steam-engine-fhs"
        fhs.parent.mkdir(parents=True)
        fhs.write_text("#!/bin/sh\nexec \"$@\"\n")
        fhs.chmod(0o755)
        proton = root / "proton-tool"
        proton.mkdir()
        (proton / "proton").write_text(
            "import json, os, sys, time\n"
            f"open({str(root / 'game.json')!r}, 'w').write(json.dumps({{'argv': sys.argv[1:], 'cwd': os.getcwd(), "
            "'env': {k: os.environ.get(k) for k in ('SteamAppId', 'STEAM_COMPAT_DATA_PATH', 'Steam3Master', 'HOME', "
            "'STEAM_COMPAT_TOOL_PATHS', 'SDL_JOYSTICK_HIDAPI_STEAMXBOX')}}))\n"
            "time.sleep(0.5)\n")
        steps = subprocess.check_output(["bun", str(STEAM / "packages/session-steps.ts"), "engine"], text=True)
        (root / "steps.sh").write_text(steps)
        script = (HERE / "session.sh").read_text()
        for name, value in {"fhs": str(root / "fhs"), "steps": str(root / "steps.sh"),
                            "launchEntry": str(HERE / "launch-entry.py"),
                            "placeholder": str(HERE / "x-placeholder.py")}.items():
            script = script.replace(f"@{name}@", value)
        (root / "session.sh").write_text(script)
        host = subprocess.Popen([sys.executable, "-c", HOST, str(channel), behavior])
        self.addCleanup(host.kill)
        # The game unit's PATH has exactly the package's runtime inputs and no
        # sh (device proof: "timeout: failed to run command 'sh'"). Give the
        # session only the commands those inputs provide.
        tools = root / "tools"
        tools.mkdir()
        for name in SESSION_TOOLS:
            found = shutil.which(name)
            self.assertIsNotNone(found, name)
            (tools / name).symlink_to(found)
        env = {**os.environ, "PATH": f"{bin_dir}:{tools}",
               "STEAM_ENGINE_HOME": str(engine), "KORRI_STEAM_ENGINE_CHANNEL": str(channel),
               "KORRI_PROTON_CACHYOS": str(proton), "NOTIFY_SOCKET": str(root / "notify")}
        env.pop("DISPLAY", None)
        result = subprocess.run([shutil.which("bash"), str(root / "session.sh"), "401710"], env=env,
                                capture_output=True, text=True, timeout=60, check=False)
        self.root, self.channel = root, channel
        return result

    def wait_for(self, name, text):
        """The host stand-in reads the FIFO on its own; give it a moment."""
        path = self.channel / name
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if path.exists() and text in path.read_text():
                return path.read_text()
            time.sleep(0.05)
        return path.read_text() if path.exists() else ""

    def statuses(self):
        path = self.root / "statuses"
        return path.read_text().splitlines() if path.exists() else []

    def test_installs_syncs_plays_and_reports_the_exit(self):
        result = self.run_session()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.channel / "received").read_text(),
                         "install 401710\nlaunched 401710\nexited 401710\n")
        self.assertEqual(self.statuses(), ["--status=korri-step: update", "--status=korri-step: sync",
                                           "--status=korri-step: game"])
        game = json.loads((self.root / "game.json").read_text())
        steam = self.root / "person/steam-engine/steam"
        self.assertEqual(game["argv"], ["waitforexitandrun", f"{steam}/steamapps/common/Game/bin/game.exe", "-x"])
        self.assertEqual(game["cwd"], f"{steam}/steamapps/common/Game/bin")
        self.assertEqual(game["env"]["SteamAppId"], "401710")
        self.assertEqual(game["env"]["Steam3Master"], "127.0.0.1:57343")
        self.assertEqual(game["env"]["HOME"], str(self.root / "person/steam-engine/home"))
        self.assertEqual(game["env"]["STEAM_COMPAT_DATA_PATH"], f"{steam}/steamapps/compatdata/401710")
        # The lock file names this session's cgroup for the host's pid translation.
        self.assertTrue((self.channel / "session.lock").read_text().startswith("/"))

    def test_a_failed_install_is_reported_through_the_engine_host(self):
        result = self.run_session("install-fails")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertEqual(self.wait_for("received", "refused"),
                         "install 401710\nrefused install_failed\n")
        self.assertIn("--status=plugin-launch: Steam engine: Steam could not install or update the game",
                      self.statuses())
        events = self.wait_for("events.jsonl", "launch_refused")
        self.assertIn('"event":"launch_refused","reason":"install_failed"', events)
        self.assertFalse((self.root / "game.json").exists())

    def test_a_missing_launch_entry_is_reported_through_the_engine_host(self):
        result = self.run_session(entry={"executable": "game.exe", "config": {"oslist": "macos"}})
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertTrue(self.wait_for("received", "refused").endswith("refused no_launch_entry\n"))

    def test_a_linux_build_runs_its_linux_entry_natively(self):
        result = self.run_session(both=True, installed=(70301, 70303), files=("game.sh",))
        self.assertEqual(result.returncode, 0, result.stderr)
        game = json.loads((self.root / "game.json").read_text())
        self.assertTrue(game["native"])
        self.assertTrue(game["argv"][0].endswith("/Game/game.sh"))

    def test_a_missing_executable_is_never_started(self):
        # The Windows build is the installed one, but its .exe is not on disk.
        result = self.run_session(both=True, installed=(70301, 70302), files=())
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertFalse((self.root / "game.json").exists())
        self.assertTrue(self.wait_for("received", "refused").endswith("refused no_launch_entry\n"))

    def test_a_cloud_conflict_starts_no_game(self):
        result = self.run_session("conflict")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertIn("--status=plugin-launch: steam-cloud-conflict", self.statuses())
        self.assertFalse((self.root / "game.json").exists())
        self.assertEqual((self.channel / "received").read_text(), "install 401710\nlaunched 401710\n")

    def test_an_engine_that_is_not_the_pinned_build_refuses_the_launch(self):
        result = self.run_session("mismatch")
        self.assertEqual(result.returncode, 126, result.stderr)
        self.assertIn("--status=plugin-launch: Steam engine: this engine build is not available on this device",
                      self.statuses())
        self.assertFalse((self.channel / "received").exists())


if __name__ == "__main__":
    unittest.main()

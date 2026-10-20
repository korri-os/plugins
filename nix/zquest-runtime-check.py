#!/usr/bin/env python3
"""Exercise the packaged player through Core on an isolated Xvfb display."""

import atexit
import base64
import hashlib
import io
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time

from PIL import Image

package, engine, korrid, system, fixtures, public_fixture = sys.argv[1:]
package, engine = Path(package), Path(engine)
manifest = json.loads((package / "manifest.json").read_text())
launcher = Path(manifest["files"]["zplayer"])
executable = engine / "bin/zplayer"
header = executable.read_bytes()[:20]
assert header[:6] == b"\x7fELF\x02\x01", header
assert (
    struct.unpack_from("<H", header, 18)[0]
    == {
        "x86_64-linux": 62,
        "aarch64-linux": 183,
    }[system]
)
assert not (engine / "bin/zeditor").exists()
assert not (engine / "bin/zscript").exists()
resources = engine / "share/zquestclassic"
assert not (resources / "quests").exists()
for license_name in [
    "stduuid",
    "allegro5",
    "gme",
    "gme-gpl2",
    "poolSTL-Boost",
    "poolSTL-BSD",
    "poolSTL-MIT",
]:
    assert (
        resources / "licenses/pinned-dependencies" / f"{license_name}.txt"
    ).stat().st_size > 100
assert (resources / "licenses/zquest_classic.LICENSE.txt").stat().st_size > 100
subprocess.run([executable, "-version"], check=True, timeout=20)

root = Path(tempfile.mkdtemp(prefix="zquest-runtime-")).resolve()
print(f"ZQuest runtime evidence: {root}", flush=True)

# Exercise real audio initialization without hardware or a kernel sequencer.
# A private PulseAudio sink belongs only to this off-device check.
pulse_socket = root / "pulse.sock"
pulse_log = (root / "pulse.log").open("w")
pulse = subprocess.Popen(
    [
        "pulseaudio",
        "-n",
        "--daemonize=no",
        "--exit-idle-time=-1",
        "--use-pid-file=no",
        "--load=module-null-sink sink_name=zquest_test",
        f"--load=module-native-protocol-unix socket={pulse_socket} auth-anonymous=1",
    ],
    stdout=pulse_log,
    stderr=subprocess.STDOUT,
)


def stop_pulse():
    if pulse.poll() is None:
        pulse.terminate()
        try:
            pulse.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pulse.kill()
            pulse.wait()
    pulse_log.close()


atexit.register(stop_pulse)
for _ in range(100):
    if pulse_socket.exists():
        break
    assert pulse.poll() is None, (root / "pulse.log").read_text()
    time.sleep(0.1)
assert pulse_socket.exists(), (root / "pulse.log").read_text()
os.environ["PULSE_SERVER"] = f"unix:{pulse_socket}"


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def command(quest, account):
    request = {
        "runnerId": "@korri:zquest-classic/zplayer",
        "program": str(launcher),
        "contentPath": str(quest),
        "accountRoot": str(account),
        "cacheRoot": str(root / "cache"),
        "files": manifest["files"],
        "artifacts": {},
    }
    return [
        korrid,
        "plugin-launch",
        str(package / "plugin.ts"),
        json.dumps(request),
        json.dumps({"modifiers": []}),
    ]


def account(name):
    directory = root / name / "zquest-classic"
    directory.mkdir(parents=True)
    # Audio initialization stays enabled to catch the missing-ALSA-sequencer
    # crash seen on the Mini V2. The launcher must answer the upload question:
    # an unanswered modal would stop every input step below.
    (directory / "zc.cfg").write_text(
        "[zeldadx]\nnosound = 0\nreplay_upload = 0\n[korri_test]\nsentinel = keep-me\n"
    )
    return directory.parent


def wait_for(test, child, explanation, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if test():
            return
        if child.poll() is not None:
            raise AssertionError(
                f"Player exited {child.returncode}: {explanation}; logs in {root}"
            )
        time.sleep(0.1)
    raise AssertionError(f"Timed out: {explanation}; logs in {root}")


def capture_screen():
    return subprocess.check_output(["import", "-window", "root", "png:-"], timeout=10)


def screen_pixels():
    with Image.open(io.BytesIO(capture_screen())) as image:
        return image.convert("RGB").tobytes()


def key(name):
    if name == "F12":
        subprocess.run(["xdotool", "keydown", name], check=True, timeout=5)
        time.sleep(0.2)
        subprocess.run(["xdotool", "keyup", name], check=True, timeout=5)
        time.sleep(0.8)
        return
    # Menu input is acknowledged by the actual window, not a fixed sleep.
    # Hold until the window reacts, then release before the next action.
    before = screen_pixels()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        subprocess.run(["xdotool", "keydown", name], check=True, timeout=5)
        try:
            hold_until = time.monotonic() + 2
            while time.monotonic() < hold_until and screen_pixels() == before:
                time.sleep(0.1)
        finally:
            subprocess.run(["xdotool", "keyup", name], check=True, timeout=5)
        time.sleep(0.3)
        if screen_pixels() != before:
            time.sleep(0.5)
            return
    raise AssertionError(f"No visible response to {name}")


def snapshot_when_ready(directory, child):
    previous = set(directory.rglob("zc_screen*.png"))
    previous_frame = None

    def ready():
        nonlocal previous, previous_frame
        key("F12")
        current = set(directory.rglob("zc_screen*.png"))
        new = current - previous
        previous = current
        for snapshot in new:
            with Image.open(snapshot) as image:
                assert image.width >= 256 and image.height >= 168
                rgb = image.convert("RGB")
                colors = rgb.getcolors(image.width * image.height)
                frame = hashlib.sha256(rgb.tobytes()).digest()
                stable = frame == previous_frame
                previous_frame = frame
                if colors is not None and len(colors) > 8 and stable:
                    return True
        return False

    # Loading consumes input; its opening wipe can still accept F12. This known
    # generated room is static while idle, so two equal rendered frames establish
    # the end of that transition without assuming an architecture-specific delay.
    wait_for(ready, child, "native screenshot responds with a stable game frame")


def play(quest, owner, *, save=False, concurrent=False, complete=False):
    directory = owner / "zquest-classic"
    native_log = directory / "allegro.log"
    native_log.unlink(missing_ok=True)
    save_file = directory / "saves" / f"sha256:{digest(quest)}.sav"
    with (directory / "check-output.log").open("w") as log:
        child = subprocess.Popen(
            command(quest, owner),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            wait_for(
                lambda: (
                    native_log.exists()
                    and f"[QUEST METADATA]\nPath: {quest}"
                    in native_log.read_text(errors="replace")
                ),
                child,
                "selected quest loaded",
            )
            assert "Initializing sound driver... OK" in native_log.read_text()
            wait_for(
                lambda: save_file.exists() and save_file.stat().st_size > 100,
                child,
                "native save exists",
            )
            windows = subprocess.check_output(
                ["xdotool", "search", "--onlyvisible", "--name", "."], text=True
            ).splitlines()
            subprocess.run(
                ["xdotool", "windowfocus", "--sync", windows[-1]], check=True
            )
            time.sleep(1)
            if concurrent:
                before = digest(save_file)
                rejected = subprocess.run(
                    command(quest, owner), capture_output=True, text=True, timeout=20
                )
                assert rejected.returncode != 0, rejected.stdout
                assert "already running" in rejected.stderr, rejected.stderr
                assert digest(save_file) == before
            snapshot_when_ready(directory, child)
            if complete:
                before = digest(save_file)
                subprocess.run(["xdotool", "keydown", "Right"], check=True, timeout=5)
                time.sleep(0.8)
                subprocess.run(["xdotool", "keyup", "Right"], check=True, timeout=5)
                started = time.monotonic()
                captured_ending = False

                def finished():
                    nonlocal captured_ending
                    if (
                        digest(save_file) != before
                        and native_log.read_text(errors="replace").count(
                            "[QUEST METADATA]"
                        )
                        >= 2
                    ):
                        return True
                    # Capture the built-in presentation for inspection, not a
                    # user quest or a copied test image. Input stays responsive.
                    if not captured_ending and time.monotonic() - started > 35:
                        (directory / "ending.png").write_bytes(capture_screen())
                        captured_ending = True
                    subprocess.run(
                        ["xdotool", "keydown", "Return"], check=True, timeout=5
                    )
                    time.sleep(0.05)
                    subprocess.run(
                        ["xdotool", "keyup", "Return"], check=True, timeout=5
                    )
                    time.sleep(0.5)
                    return False

                wait_for(
                    finished,
                    child,
                    "built-in ending saved and returned to the quest",
                    timeout=180,
                )
                assert captured_ending and (directory / "saves/backup").is_dir()
                snapshot_when_ready(directory, child)
            if save:
                before = digest(save_file)
                for action in ["F6", "Return", "Down", "Return"]:
                    key(action)
                wait_for(
                    lambda: digest(save_file) != before,
                    child,
                    "in-game save changed persisted native state",
                )
                assert (directory / "saves/backup").is_dir()
                wait_for(
                    lambda: (
                        native_log.read_text(errors="replace").count("[QUEST METADATA]")
                        >= 2
                    ),
                    child,
                    "quest reloaded after in-game save",
                )
                snapshot_when_ready(directory, child)
            key("F10")
            key("Return")
            assert child.wait(timeout=20) == 0
            settings = directory / "zc.cfg"
            assert "sentinel = keep-me" in settings.read_text()
            # The player rewrites its config on exit; the kiosk keys must stay.
            assert loaded.read_config(settings, "zeldadx", "clicktofreeze") == "0"
            assert loaded.read_config(settings, "zeldadx", "replay_upload") == "0"
            scheme = loaded.read_config(settings, "Controls", "global_control_scheme")
            controls = directory / "controls.cfg"
            assert loaded.read_config(controls, scheme, "btn_menu") == "0"
            assert loaded.read_config(controls, scheme, "joystick_name") == loaded.SEAT
            return save_file
        except Exception:
            screenshot = capture_screen()
            (directory / "failure.png").write_bytes(screenshot)
            print(
                "ZQUEST_FAILURE_SCREEN=" + base64.b64encode(screenshot).decode(),
                flush=True,
            )
            if native_log.exists():
                print(native_log.read_text(errors="replace"), flush=True)
            print(
                (directory / "check-output.log").read_text(errors="replace"), flush=True
            )
            raise
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()


loader = importlib.machinery.SourceFileLoader("zquest_launcher", str(launcher))
spec = importlib.util.spec_from_loader(loader.name, loader)
loaded = importlib.util.module_from_spec(spec)
loader.exec_module(loaded)

# Kiosk settings change only their own keys. "Default" is reset by the player,
# so a fresh account gets upstream's first generated scheme name instead.
fresh = root / "kiosk-fresh"
fresh.mkdir()
loaded.configure(fresh)
assert (fresh / "zc.cfg").read_text() == (
    "[zeldadx]\nreplay_upload_prompt = 1\nclicktofreeze = 0\n"
    "[Controls]\nglobal_control_scheme = Custom\n"
)
assert (fresh / "controls.cfg").read_text() == (
    "[Custom]\nbtn_menu = 0\njoystick_name = Korri Seat P1\nbtn_s = 8\nbtn_ex2 = 10\n"
)
kept = root / "kiosk-kept"
kept.mkdir()
(kept / "zc.cfg").write_text(
    "# note\n[zeldadx]\nclicktofreeze = 1\nsentinel = keep\n\n"
    "[Controls]\nglobal_control_scheme = Mine\n"
)
(kept / "controls.cfg").write_text(
    "[Default]\nbtn_menu=9\n[Mine]\nbtn_menu=9\njoystick_index=0\nbtn_s=10\n"
    "key_a=26\n\n[Other]\nkey_a=1\n"
)
(kept / "controls.cfg").chmod(0o640)
loaded.configure(kept)
assert (kept / "zc.cfg").read_text() == (
    "# note\n[zeldadx]\nclicktofreeze = 0\nsentinel = keep\n"
    "replay_upload_prompt = 1\n\n[Controls]\nglobal_control_scheme = Mine\n"
)
assert (kept / "controls.cfg").read_text() == (
    "[Default]\nbtn_menu=9\n[Mine]\nbtn_menu = 0\njoystick_index=0\nbtn_s = 8\n"
    "key_a=26\njoystick_name = Korri Seat P1\nbtn_ex2 = 10\n\n"
    "[Other]\nkey_a=1\nbtn_menu = 0\njoystick_name = Korri Seat P1\nbtn_s = 8\n"
    "btn_ex2 = 10\n"
)
assert (kept / "controls.cfg").stat().st_mode & 0o777 == 0o640
assert sorted(path.name for path in kept.iterdir()) == ["controls.cfg", "zc.cfg"]

# An original generated room exercises the public player without a copied
# template, tiles, music or quest. The fixture never enters the runtime closure.
quest = root / "Quest '; $(exit 19).qst"
shutil.copyfile(public_fixture, quest)
original_hash = digest(quest)
owner = account("Player One '; $(exit 21)")
save = play(quest, owner, save=True, concurrent=True)
saved_hash = digest(save)
assert digest(quest) == original_hash

# Move the input so the old path is absent. The same save must load, not merely
# a new empty slot. The engine patch also updates the path within loaded state.
moved = root / "renamed.QST"
quest.rename(moved)
assert play(moved, owner) == save
assert digest(save) == saved_hash
assert len(list((owner / "zquest-classic/saves").glob("*.sav"))) == 1

# A second account gets a new slot without touching the first account's state.
other_owner = account("Player Two")
other_save = play(moved, other_owner)
assert other_save != save
assert digest(save) == saved_hash

# This LZSS quest remains valid with trailing bytes. Treat the changed whole
# file as a distinct release even though its native quest data is unchanged.
with moved.open("ab") as changed:
    changed.write(b"\x00")
updated_save = play(moved, owner)
assert updated_save != save
assert digest(save) == saved_hash
assert len(list((owner / "zquest-classic/saves").glob("*.sav"))) == 2

# The original room's native win-flag variant exercises the actual built-in
# ending, replacement fonts/graphics, START acknowledgement and save/reload.
play(Path(public_fixture).with_name("public-win.qst"), account("Ending"), complete=True)

# Reject unsupported or missing inputs before creating state.
os.mkfifo(root / "pipe.qst")
for invalid in [root / "missing.qst", root / "archive.zip", root / "pipe.qst"]:
    if invalid.suffix == ".zip":
        invalid.write_bytes(b"not a quest")
    unused = root / "unused-account"
    result = subprocess.run(
        command(invalid, unused), capture_output=True, text=True, timeout=20
    )
    assert result.returncode != 0
    assert not unused.exists()

# User-authored resources must never be overwritten, including foreign links.
protected = account("Protected")
assets = protected / "zquest-classic/assets"
assets.mkdir()
(assets / "user-file").write_text("preserve")
result = subprocess.run(
    command(moved, protected), capture_output=True, text=True, timeout=20
)
assert result.returncode != 0 and "Refusing to replace" in result.stderr
assert (assets / "user-file").read_text() == "preserve"

# Exercise the actual packaged resource setup too: owned links can be repaired,
# foreign links cannot.
repair = root / "resource-repair"
repair.mkdir()
(repair / "assets").symlink_to("/nix/store/old-zquest/share/zquestclassic/assets")
loaded.prepare_resources(repair)
assert (repair / "assets").resolve() == resources / "assets"
(repair / "assets").unlink()
(repair / "assets").symlink_to(root)
try:
    loaded.prepare_resources(repair)
    raise AssertionError("foreign resource link was replaced")
except ValueError:
    pass
assert (repair / "assets").resolve() == root

# Exercise the new missing-tiles refusal through the real reader, followed by
# a successful generated-quest load. Native qe_missing_tiles is appended as 15
# in core/qst.h; old numeric error codes remain unchanged.
load_account = account("Tile requirements") / "zquest-classic"
loaded.prepare_resources(load_account)
for input_path, expected in (
    (Path(public_fixture).with_name("public-missing-tiles.qst"), 15),
    (Path(public_fixture), 0),
):
    result = subprocess.run(
        [executable, "-headless", "-load-and-quit", str(input_path)],
        cwd=load_account,
        env=dict(os.environ, ZC_DISABLE_CHDIR="1"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=45,
    )
    assert result.returncode == expected, result.stdout

# Assert upstream's recorded script execution on the real interpreter. Only
# graphics hashes use the static public-font baseline in zquest-fixtures.nix;
# script traces, RNG, timing and controls retain upstream's expectations.
# These fetched test fixtures are not in the distributable plugin closure.
script_account = account("Script replay") / "zquest-classic"
loaded.prepare_resources(script_account)
loaded.configure(script_account)
replay_result = subprocess.run(
    [
        executable,
        "-headless",
        "-assert",
        str(Path(fixtures) / "auto_scopes.zplay"),
        "-replay-exit-when-done",
        "-replay-output-dir",
        str(script_account),
    ],
    cwd=script_account,
    env=dict(os.environ, ZC_DISABLE_CHDIR="1"),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    timeout=90,
)
assert replay_result.returncode == 0, replay_result.stdout
assert "[Test] done" in replay_result.stdout, replay_result.stdout
print(
    f"ZQuest {system}: native launch, input, screenshot, save/reload, rename, account isolation and refusal checks passed"
)

"""Real native Pyxel execution; only original or explicitly reviewed cartridges.

Usage (inside xvfb-run): runtime.py PACKAGE [EXTERNAL_CONTENT EXPECTED_SHA256]
External mode requires a reviewed exact hash and proves native fullscreen window
startup and clean exit. It makes no claim of arbitrary Python isolation.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).parent


def runtime(package, external=None, expected_hash=None, start_probe=None, korrid=None):
    package = Path(package)
    manifest = json.loads((package / "manifest.json").read_text())
    supplied = (
        json.loads(os.environ["KORRI_NATIVE_PROBE_INPUT"])
        if os.environ.get("KORRI_NATIVE_PROBE_INPUT")
        else None
    )
    if supplied:
        assert korrid and external, (
            "A supplied real route requires Core and reviewed content"
        )
        assert supplied["runnerId"] == "@korri:pyxel/pyxel", (
            "Supplied runner differs from selected package"
        )
        assert Path(supplied["contentPath"]).resolve() == Path(external).resolve(), (
            "Supplied route differs from selected content"
        )
    program = supplied["program"] if supplied else manifest["files"]["pyxel"]
    proof = None
    if external or os.environ.get("KORRI_NATIVE_PROOF_DIR"):
        proof = Path(
            os.environ.get("KORRI_NATIVE_PROOF_DIR")
            or tempfile.mkdtemp(prefix="korri-native-proof-")
        )
        proof.mkdir(parents=True, exist_ok=True)
        print(f"Retained native proof: {proof}")
    with tempfile.TemporaryDirectory(prefix="pyxel-native-") as temporary:
        work = Path(temporary)
        media = work / "read-only media"
        media.mkdir()
        content = media / "Selected '; $(touch injected).pyxapp"
        if external:
            assert expected_hash, (
                "External Python execution requires its reviewed SHA256"
            )
            assert (
                hashlib.sha256(Path(external).read_bytes()).hexdigest() == expected_hash
            )
            if supplied:
                content = Path(supplied["contentPath"])
            else:
                shutil.copyfile(external, content)
        else:
            with zipfile.ZipFile(content, "w") as archive:
                archive.writestr("fixture/.pyxapp_startup_script", "main.py")
                archive.writestr("fixture/main.py", (HERE / "fixture.py").read_bytes())
                archive.writestr("fixture/sibling.py", "COLOR = 3\n")
        if not supplied:
            content.chmod(0o444)
            media.chmod(0o555)
        before = hashlib.sha256(content.read_bytes()).hexdigest()

        def launch(account, chosen=content, original=True):
            root = work / account
            marker = root / "save/.pyxel/korri/nativefixture/alive-after-start"
            if original:
                marker.unlink(missing_ok=True)
            request = {
                "runnerId": "@korri:pyxel/pyxel",
                "program": program,
                "contentPath": str(chosen),
                "accountRoot": str(root),
                "saveRoot": str(root / "save"),
                "cacheRoot": str(root / "cache"),
                "files": manifest["files"],
                "artifacts": {},
            }
            if supplied:
                request = supplied  # Exact resolve_linux_route/launch_route output.
                root = Path(request["accountRoot"])
            # Use the exact deployed effect-free declaration, not a parallel plan.
            try:
                prepared = subprocess.run(
                    [
                        "bun",
                        str(HERE.parent / "libretro/native-check/plan.ts"),
                        str(package),
                        json.dumps(request),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
            except subprocess.TimeoutExpired:
                raise AssertionError(
                    "Launch preparation exceeded its deadline"
                ) from None
            assert prepared.returncode == 0, (
                "Launch preparation failed: " + prepared.stderr
            )
            plan = json.loads(prepared.stdout)
            for directory in plan["directories"]:
                Path(directory).mkdir(parents=True, exist_ok=True)
            trigger = work / "start-trigger"
            trigger.unlink(missing_ok=True)
            command = (
                [
                    korrid,
                    "plugin-run",
                    str(package / "plugin.ts"),
                    json.dumps(request),
                    json.dumps({"modifiers": []}),
                    "native-acceptance",
                ]
                if korrid
                else [plan["command"], *plan["args"]]
            )
            environment = {**os.environ, **plan["env"], "SDL_AUDIODRIVER": "dummy"}
            environment.pop("KORRI_NATIVE_PROBE_INPUT", None)
            process = subprocess.Popen(
                command,
                cwd=plan["cwd"],
                env={
                    **environment,
                    **(
                        {
                            "LD_PRELOAD": start_probe,
                            "KORRI_TEST_START_TRIGGER": str(trigger),
                        }
                        if start_probe
                        else {}
                    ),
                },
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                # Core's unmodified no-hook plan execs the native program in place.
                native_pid = process.pid
                window = subprocess.run(
                    [
                        "xdotool",
                        "search",
                        "--sync",
                        "--onlyvisible",
                        "--pid",
                        str(native_pid),
                    ],
                    text=True,
                    capture_output=True,
                    # Loaded CI runners took longer than 15 s to map it.
                    timeout=60,
                    check=True,
                ).stdout.splitlines()[0]
                subprocess.run(
                    ["xdotool", "windowfocus", "--sync", window], check=True, timeout=5
                )
                # Test the actual native SDL window state, not wrapper text.
                # The window manager applies native fullscreen asynchronously;
                # a fixed 0.25 s wait failed on a loaded CI runner.
                deadline = time.monotonic() + 10
                while True:
                    state = subprocess.check_output(
                        ["xprop", "-id", window, "_NET_WM_STATE"], text=True
                    )
                    if (
                        "_NET_WM_STATE_FULLSCREEN" in state
                        or time.monotonic() >= deadline
                    ):
                        break
                    time.sleep(0.05)
                assert "_NET_WM_STATE_FULLSCREEN" in state, state
                before_frame = -1
                if original:
                    for attempt in range(100):
                        if marker.is_file():
                            before_frame = int(marker.read_text())
                            break
                        time.sleep(0.05)
                    assert before_frame >= 0, "No native update frames"
                if start_probe:
                    trigger.touch()
                time.sleep(1.5)
                assert process.poll() is None, "Pyxel exited on Start or startup"
                if proof:
                    subprocess.run(
                        [
                            "magick",
                            "import",
                            "-window",
                            window,
                            str(proof / "pyxel.png"),
                        ],
                        check=True,
                        timeout=10,
                    )
                if original:
                    assert int(marker.read_text()) > before_frame, (
                        "Native updates stopped after Start"
                    )
                subprocess.run(
                    ["xdotool", "key", "--clearmodifiers", "Escape"],
                    check=True,
                    timeout=5,
                )
                try:
                    stdout, stderr = process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    raise AssertionError("Pyxel did not exit after Escape") from None
                if proof:
                    (proof / "pyxel-load.log").write_text(stdout + stderr)
                assert process.returncode == 0, stdout + stderr
                if start_probe:
                    assert (
                        "BITSY_TEST_START_DOWN" in stderr
                        and "BITSY_TEST_START_UP" in stderr
                    ), stderr
                return root
            finally:
                if process.poll() is None:
                    process.kill()
                stdout, stderr = process.communicate()
                if process.returncode:
                    print(stdout + stderr, file=sys.stderr)

        a = launch("Account A '; $(touch injected)", original=not external)
        if not external:
            assert (
                a / "save/.pyxel/korri/nativefixture/fixture-save.txt"
            ).read_text() == "1"
            assert (a / "save/.pyxel/korri/nativefixture/native-save.txt").is_file()
            launch("Account A '; $(touch injected)")
            assert (
                a / "save/.pyxel/korri/nativefixture/fixture-save.txt"
            ).read_text() == "2"
            b = launch("Account B")
            assert (
                b / "save/.pyxel/korri/nativefixture/fixture-save.txt"
            ).read_text() == "1"
        assert hashlib.sha256(content.read_bytes()).hexdigest() == before
        if supplied:
            print(
                "Pyxel: exact supplied route, reviewed selected content, native screenshot and clean exit passed"
            )
            return
        assert list(media.iterdir()) == [content]
        assert not list(work.rglob("injected"))
        # Fail before executing code for missing/non-file/unsupported input.
        for arguments in [
            [],
            [str(work / "absent.pyxapp")],
            [str(media)],
            ["relative.pyxapp"],
            [str(content), str(content)],
            [str(work / "source.py")],
        ]:
            rejected = subprocess.run(
                [program, *arguments],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            assert rejected.returncode != 0, arguments
        corrupt = work / "corrupt.pyxapp"
        corrupt.write_text("not a ZIP")
        markerless = work / "markerless.pyxapp"
        with zipfile.ZipFile(markerless, "w") as archive:
            archive.writestr("fixture/not-startup.txt", "no entry point")
        outside = work / "outside.py"
        sentinel = work / "outside-executed"
        outside.write_text(f"from pathlib import Path; Path({str(sentinel)!r}).touch()")
        malformed = [corrupt, markerless]
        for label, marker in [
            ("absolute", str(outside)),
            ("traversing", "../../outside.py"),
            ("missing", "missing.py"),
        ]:
            broken = work / f"{label}.pyxapp"
            with zipfile.ZipFile(broken, "w") as archive:
                archive.writestr("fixture/.pyxapp_startup_script", marker)
                archive.writestr("fixture/main.py", "raise Exception('not selected')")
            malformed.append(broken)
        ambiguous = work / "ambiguous.pyxapp"
        with zipfile.ZipFile(ambiguous, "w") as archive:
            for app in ("one", "two"):
                archive.writestr(f"{app}/.pyxapp_startup_script", "main.py")
                archive.writestr(f"{app}/main.py", outside.read_text())
        malformed.append(ambiguous)
        for broken in malformed:
            rejected = subprocess.run(
                [program, str(broken)],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            assert rejected.returncode != 0, str(broken)
            assert not sentinel.exists(), "Executed code outside selected application"
    print(
        "Pyxel: original-format multi-module startup, fullscreen, Start/exit, read-only media, saves and refusals passed"
    )


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[2] in ("x86_64-linux", "aarch64-linux"):
        # This is an acceptance allowlist, never a restriction on local play.
        reviewed = os.environ.get(
            "KORRI_PYXEL_REVIEWED_SHA256",
            "250ababacc8f8b50a0e12c30e966b81e6aea1d8559e065a9a734baf59ba82be9",
        )
        runtime(sys.argv[1], sys.argv[4], reviewed, korrid=sys.argv[3])
    else:
        runtime(
            sys.argv[1],
            *(sys.argv[2:4]),
            start_probe=os.environ.get("KORRI_START_PROBE"),
        )

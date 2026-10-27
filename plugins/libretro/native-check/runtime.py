"""Execute launch.prepare from an exact installed plugin, then its real frontend.

Usage (inside xvfb-run): runtime.py PACKAGE CORE CONTENT [--external]
The same entry point accepts an acquired original-format file. No content is
rewritten. --external skips fixture-specific save-counter assertions only.
Requires bun, python3 and the exact package closure; no Core build is required.
"""

import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent


def run(package, core, content, external=False, korrid=None, architecture=None):
    manifest = json.loads((Path(package) / "manifest.json").read_text())
    supplied = (
        json.loads(os.environ["KORRI_NATIVE_PROBE_INPUT"])
        if os.environ.get("KORRI_NATIVE_PROBE_INPUT")
        else None
    )
    if supplied:
        assert korrid, "A supplied real route requires Core plugin-run"
        assert supplied["runnerId"] == f"@korri:{core}/{core}", (
            "Supplied runner differs from selected package"
        )
        assert Path(supplied["contentPath"]).resolve() == Path(content).resolve(), (
            "Supplied route differs from selected content"
        )
        external = True
    native = supplied["corePath"] if supplied else manifest["files"][core]
    machine = struct.unpack_from("<H", Path(native).read_bytes(), 18)[0]
    assert machine in (62, 183), (
        f"Expected native Linux x86_64/aarch64 ELF, got {machine}"
    )
    if architecture:
        assert machine == {"x86_64-linux": 62, "aarch64-linux": 183}[architecture]
    source = Path(content).resolve()
    before = hashlib.sha256(source.read_bytes()).digest()
    neighbors = {p.name for p in source.parent.iterdir()}
    proof = None
    if external or os.environ.get("KORRI_NATIVE_PROOF_DIR"):
        proof = Path(
            os.environ.get("KORRI_NATIVE_PROOF_DIR")
            or tempfile.mkdtemp(prefix="korri-native-proof-")
        )
        proof.mkdir(parents=True, exist_ok=True)
        print(f"Retained native proof: {proof}")
    probe_env = dict(os.environ)
    probe_env.pop("KORRI_NATIVE_PROBE_INPUT", None)
    if proof:
        probe_env["KORRI_NATIVE_FRAME"] = str(proof / f"{core}.png")
    if not external:
        probe_env["KORRI_NATIVE_FIXTURE"] = core
    probe = subprocess.run(
        [sys.executable, str(HERE / "core-probe.py"), native, str(source)],
        check=False,
        env=probe_env,
        # Loaded CI runners took longer than 35 s (run 40512977042).
        timeout=120,
        capture_output=True,
        text=True,
    )
    if proof:
        (proof / "core-load.log").write_text(probe.stdout + probe.stderr)
    assert probe.returncode == 0, probe.stdout + probe.stderr
    print(probe.stdout, end="")
    print(probe.stderr, end="", file=sys.stderr)
    if core == "pzretro":
        assert "Successful Compilation" in probe.stdout + probe.stderr, (
            "PuzzleScript did not compile"
        )
    with tempfile.TemporaryDirectory(prefix=f"{core}-frontend-") as temporary:
        work = Path(temporary)

        def launch(account, selected=source):
            root = work / account
            request = {
                "runnerId": f"@korri:{core}/{core}",
                "program": manifest["files"]["retroarch"],
                "corePath": native,
                "contentPath": str(selected),
                "accountRoot": str(root),
                "saveRoot": str(root / "save"),
                "cacheRoot": str(root / "cache"),
                "files": manifest["files"],
                "artifacts": {},
                "overrides": {
                    "settings": {
                        "drivers": {
                            "video": "sdl2", "audio": "null",
                            "input": "sdl2", "joypad": "sdl2",
                        },
                        "video": {"fullscreen": False},
                        "saves": {"auto-save-state": core == "pzretro", "auto-load-state": False},
                    }
                },
            }
            if supplied:
                request = (
                    supplied  # Preserve every actual producer field, not only identity.
                )
                root = Path(request["accountRoot"])
                root.mkdir(parents=True, exist_ok=True)
            try:
                prepared = subprocess.run(
                    ["bun", str(HERE / "plan.ts"), str(package), json.dumps(request)],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            except subprocess.TimeoutExpired:
                raise AssertionError(
                    "Launch preparation exceeded its deadline"
                ) from None
            assert prepared.returncode == 0, (
                "Launch preparation failed: " + prepared.stderr
            )
            plan = json.loads(prepared.stdout)
            if not supplied:
                for directory in plan["directories"]:
                    Path(directory).mkdir(parents=True, exist_ok=True)
                for file in plan["files"]:
                    Path(file["path"]).write_text(file["content"])
            bounded = ["--verbose", "--max-frames", "180"]
            command = (
                [
                    korrid,
                    "plugin-run",
                    str(Path(package) / "plugin.ts"),
                    json.dumps(request),
                    json.dumps({"modifiers": [], "args": {"append": bounded}}),
                    "native-acceptance",
                ]
                if korrid
                else [plan["command"], *plan["args"], *bounded]
            )
            environment = {**os.environ, **plan["env"], "HOME": str(root)}
            environment.pop("KORRI_NATIVE_PROBE_INPUT", None)
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    cwd=root,
                    env=environment,
                    capture_output=True,
                    text=True,
                    # --max-frames bounds the run; this only catches a hang.
                    timeout=120,
                )
            except subprocess.TimeoutExpired:
                raise AssertionError(
                    "Native frontend exceeded its bounded startup deadline"
                ) from None
            log = result.stdout + result.stderr
            if proof:
                (
                    proof
                    / ("frontend.log" if selected == source else "missing-content.log")
                ).write_text(log)
            assert result.returncode == 0, log
            assert "[Core]" in log and "[Content]" in log, log
            assert "Failed to load content" not in log, log
            assert not list(work.rglob("injected"))
            return root, log

        first, _ = launch("Account A '; $(touch injected)")
        if not external:
            saves = list((first / "save").rglob("*.srm"))
            if core != "pzretro":
                assert len(saves) == 1, list((first / "save").rglob("*"))
                saved = saves[0].read_bytes()
                # WASM-4 stores a little-endian uint16 disk-size word before disk bytes.
                offset = 2 if core == "wasm4" else 0
                assert saved[offset] == 1, saved[:16]
                launch("Account A '; $(touch injected)")
                assert saves[0].read_bytes()[offset] == 2
                second, _ = launch("Account B")
                assert next((second / "save").rglob("*.srm")).read_bytes()[offset] == 1
            else:
                assert list((first / "save").rglob("*.auto")), (
                    "PuzzleScript did not serialize state"
                )
                assert not (work / "Account B").exists()
        if not supplied:
            # Selected missing files must fail, never enter a native chooser.
            try:
                launch("Missing", work / "absent.game")
            except AssertionError as error:
                assert (
                    "Failed to load content" in str(error)
                    or "could not read" in str(error).lower()
                ), str(error)
            else:
                raise AssertionError("Missing selected content was accepted")
    assert hashlib.sha256(source.read_bytes()).digest() == before, "Media changed"
    # Original fixture media is an exclusive read-only directory. An acquired
    # file's parent can also contain live host state and probe output.
    if not external:
        assert {p.name for p in source.parent.iterdir()} == neighbors, (
            "Media directory changed"
        )
    print(
        f"{core}: selected-file frontend launch, clean bounded exit, unchanged media and account saves passed"
    )


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[2] in ("x86_64-linux", "aarch64-linux"):
        package, architecture, korrid, content = sys.argv[1:]
        manifest = json.loads((Path(package) / "manifest.json").read_text())
        core = next(
            key
            for key in ("tic80", "wasm4", "lowresnx", "pzretro")
            if key in manifest["files"]
        )
        run(
            package,
            core,
            content,
            external=True,
            korrid=korrid,
            architecture=architecture,
        )
    else:
        run(*sys.argv[1:4], external="--external" in sys.argv[4:])

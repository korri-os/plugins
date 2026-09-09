#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 nix
"""Test export's public CLI with an existing store output on a build machine.

Requires a readable Nix store. Never disables signature checks, signs the source
store, publishes, or builds anything. Pass one prebuilt /nix/store output.
"""

from pathlib import Path
import subprocess
import sys
import tempfile

script = Path(__file__).with_name("github-cache.py")
if len(sys.argv) != 2:
    sys.exit("usage: github-cache-export-test.py PREBUILT_STORE_OUTPUT")
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    key, public = root / "secret", root / "public"
    subprocess.run(
        [
            "nix-store",
            "--generate-binary-cache-key",
            "export-test-1",
            str(key),
            str(public),
        ],
        check=True,
    )
    key.chmod(0o600)
    subprocess.run(
        [
            sys.executable,
            str(script),
            "export",
            str(root / "cache"),
            "--key-file",
            str(key),
            sys.argv[1],
        ],
        check=True,
    )
    notes = list((root / "cache").glob("*.narinfo"))
    assert notes, "export wrote no Nix metadata"
    assert all("Sig: export-test-1:" in note.read_text() for note in notes)
    subprocess.run(
        [
            sys.executable,
            str(script),
            "prepare",
            str(root / "cache"),
            str(root / "prepared"),
            "--nar-base-url",
            "https://example.com/releases/download/batch/",
        ],
        check=True,
    )
    assert len(list((root / "prepared" / "metadata").glob("*.narinfo"))) == len(notes)
    assert key.read_text() not in "".join(note.read_text() for note in notes)
print("PASS: export CLI signed a prebuilt closure and prepare preserved its metadata")

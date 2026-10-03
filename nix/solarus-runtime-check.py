#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3
"""Exercise the packaged native engine through Core's actual launch executor."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile


package, system, korrid, headless, fixture = sys.argv[1:]
package = Path(package)
manifest = json.loads((package / "manifest.json").read_text())
engine = Path(manifest["files"]["solarus"])
native = Path(manifest["packages"]["solarus"])
with engine.open("rb") as executable:
    elf = executable.read(20)
assert elf[:6] == b"\x7fELF\x02\x01"
assert (
    struct.unpack_from("<H", elf, 18)[0]
    == {
        "x86_64-linux": 62,
        "aarch64-linux": 183,
    }[system]
)
assert (
    "GNU GENERAL PUBLIC LICENSE"
    in (native / "share/licenses/solarus/COPYING").read_text()
)
assert "Olivier" in (native / "share/licenses/solarus/license-details.md").read_text()

with tempfile.TemporaryDirectory(prefix="solarus-runtime-") as temporary:
    work = Path(temporary)
    desktop = work / "desktop"
    desktop.mkdir()
    desktop_save = desktop / ".solarus/korri_plugin_test/save1.dat"
    desktop_save.parent.mkdir(parents=True)
    desktop_save.write_text("launches = 91\n")
    env = {
        **os.environ,
        "HOME": str(desktop),
        "SDL_VIDEODRIVER": "dummy",
        "SDL_AUDIODRIVER": "dummy",
        "XDG_STATE_HOME": str(work / "legacy-state"),
    }

    def execute(command):
        result = subprocess.run(
            command, cwd=work, env=env, capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout + result.stderr

    assert "quest_path" in execute([str(engine), "-help"])
    data = work / "source quest/data"
    shutil.copytree(fixture, data)
    archive = work / "My quest '; $(touch injected) %.solarus"
    # Nix source mtimes are Unix epoch; ZIP timestamps start in 1980.
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, strict_timestamps=False
    ) as output:
        for item in sorted(data.iterdir()):
            output.write(item, item.name)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    first = work / "accounts/Player One '; $(touch injected)"
    second = work / "accounts/Player Two"

    def launch(content, account, expected):
        request = {
            "runnerId": "@korri:solarus/solarus",
            # The test-only executable adds upstream's -no-video/-no-audio flags
            # and execs the actual engine. Production uses manifest.files.solarus.
            "program": headless,
            "contentPath": str(content),
            "accountRoot": str(account),
            "files": manifest["files"],
        }
        output = execute(
            [korrid, "plugin-launch", str(package / "plugin.ts"), json.dumps(request)]
        )
        assert "Solarus 2.1.4" in output, output
        assert f"KORRI_SOLARUS_SAVE={expected}" in output, output
        assert "KORRI_SOLARUS_LOOP" in output, output
        assert "Error:" not in output and "Fatal:" not in output, output
        save = account / ".solarus/korri_plugin_test/save1.dat"
        assert f"launches = {expected}" in save.read_text()
        return save

    # New account roots are provisioned by Core. Reload from an independent
    # process, then prove the other account starts without that save.
    first_save = launch(archive, first, 1)
    launch(archive, first, 2)
    first_bytes = first_save.read_bytes()
    launch(archive, second, 1)
    assert first_save.read_bytes() == first_bytes
    launch(archive, first, 3)

    # Upstream accepts a direct data directory and data.solarus.zip. They are
    # launchable explicitly, but the plugin does not claim all directories/ZIPs.
    launch(data, first, 4)
    zipped = work / "data.solarus.zip"
    shutil.copyfile(archive, zipped)
    launch(zipped, first, 5)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest
    assert desktop_save.read_text() == "launches = 91\n"
    assert not (work / "legacy-state").exists()
    assert not list(work.rglob("injected"))
    assert sorted(item.name for item in data.iterdir()) == [
        "main.lua",
        "project_db.dat",
        "quest.dat",
    ]

    # Upstream returns zero for a missing quest. Check its diagnostic and prove
    # it never enters our quest or overwrites the last successful save.
    before = first_save.read_bytes()
    invalid = work / "invalid.solarus"
    invalid.write_bytes(b"not a quest archive")
    for bad in [invalid, work / "absent.solarus"]:
        request = {
            "runnerId": "@korri:solarus/solarus",
            "program": headless,
            "contentPath": str(bad),
            "accountRoot": str(first),
            "files": manifest["files"],
        }
        output = execute(
            [korrid, "plugin-launch", str(package / "plugin.ts"), json.dumps(request)]
        )
        assert "No quest was found" in output, output
        assert "KORRI_SOLARUS_SAVE=" not in output
        assert first_save.read_bytes() == before

print(
    f"Solarus {system}: native ELF, archive/directory launch, save/reload and supplied-root isolation passed"
)
print(
    "Headless fixture only. Physical input, audible sound and real-game completion are not verified."
)

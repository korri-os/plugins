"""Run the actual packaged C/embedded-JS engine via Core, on a build host."""

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

package, system, korrid, fixture = sys.argv[1:]
package = Path(package)
manifest = json.loads((package / "manifest.json").read_text())
engine = manifest["files"]["bitsybox"]
native = Path(manifest["packages"]["bitsybox"])
elf = Path(engine).read_bytes()[:20]
assert elf[:6] == b"\x7fELF\x02\x01"
assert (
    struct.unpack_from("<H", elf, 18)[0]
    == {
        "x86_64-linux": 62,
        "aarch64-linux": 183,
    }[system]
)
notices = native / "share/licenses/bitsybox"
assert (
    (notices / "Anti-Capitalist-1.4.txt")
    .read_text()
    .startswith("ANTI-CAPITALIST SOFTWARE LICENSE (v 1.4)")
)
assert (
    "Copyright (c) 2016-present, Bitsy authors"
    in (notices / "Bitsy-MIT.txt").read_text()
)
assert (
    "Copyright (c) 2013-2019 by Duktape authors"
    in (notices / "Duktape-notices.txt").read_text()
)
assert sorted(p.name for p in (native / "bin").iterdir()) == ["bitsybox"]
assert not list(native.rglob("*.bitsy"))
assert not list(package.rglob("*.bitsy"))

with tempfile.TemporaryDirectory(prefix="bitsy-runtime-") as temporary:
    work = Path(temporary)
    media = work / "media"
    folder = media / ("long path " * 9) / ("second path " * 9) / ("third path " * 9)
    folder.mkdir(parents=True)
    selected = folder / "Selected '; $(touch injected) %.bitsy"
    shutil.copyfile(fixture, selected)
    assert len(str(selected)) > 256
    selected.chmod(0o444)
    account = work / "account"
    before = {
        str(p.relative_to(media)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in media.rglob("*")
        if p.is_file()
    }

    def request(content):
        return {
            "runnerId": "@korri:bitsybox/bitsybox",
            "program": engine,
            "contentPath": str(content),
            "accountRoot": str(account),
            "saveRoot": str(account / "saves"),
            "cacheRoot": str(work / "cache"),
            "files": manifest["files"],
            "artifacts": {},
        }

    command = [
        korrid,
        "plugin-run",
        str(package / "plugin.ts"),
        json.dumps(request(selected)),
        json.dumps({"modifiers": []}),
        "fixture",
    ]
    process = subprocess.Popen(
        command,
        cwd=work,
        env={**os.environ, "SDL_AUDIODRIVER": "dummy"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        window = subprocess.run(
            ["xdotool", "search", "--sync", "--name", "^BITSYBOX$"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        ).stdout.splitlines()[0]
        # Keep a real native world alive for a bounded interval, not just an SDL init.
        time.sleep(1)
        assert process.poll() is None
        subprocess.run(
            ["xdotool", "windowfocus", "--sync", window], check=True, timeout=5
        )
        subprocess.run(
            ["xdotool", "key", "--clearmodifiers", "Escape"], check=True, timeout=5
        )
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, stdout + stderr
        assert "bitsy::world loaded" in stdout, stdout + stderr
        assert "Error:" not in stdout and "error:" not in stdout, stdout + stderr
        assert "Update Bitsy Error" not in stdout, stdout + stderr
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
    assert account.is_dir()  # Provisioned by the real launch executor.
    assert list(account.iterdir()) == []  # No new saves/config policy.
    after = {
        str(p.relative_to(media)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in media.rglob("*")
        if p.is_file()
    }
    assert before == after
    assert not list(work.rglob("injected"))
    assert sorted(str(p.relative_to(media)) for p in media.rglob("*")) == sorted(
        [
            str(p.relative_to(media))
            for p in [folder.parent.parent, folder.parent, folder, selected]
        ]
    )

    empty = work / "empty.bitsy"
    empty.touch()
    invalid = work / "invalid.bitsy"
    invalid.write_text("not a native Bitsy world")
    binary = work / "binary.bitsy"
    binary.write_bytes(b"not text\0")
    fifo = work / "fifo.bitsy"
    os.mkfifo(fifo)
    unreadable = work / "unreadable.bitsy"
    shutil.copyfile(fixture, unreadable)
    unreadable.chmod(0)
    # Bad driver proves each failure occurs before SDL initialization.
    for arguments in [
        [],
        ["relative.bitsy"],
        [str(selected), str(selected)],
        *[
            [str(p)]
            for p in [
                work / "absent.bitsy",
                work,
                empty,
                invalid,
                binary,
                fifo,
                unreadable,
            ]
        ],
    ]:
        result = subprocess.run(
            [engine, *arguments],
            check=False,
            cwd=work,
            env={**os.environ, "SDL_VIDEODRIVER": "korri-invalid-driver"},
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode != 0, (arguments, result.stdout, result.stderr)
        assert "SDL initialization error" not in result.stdout, (
            arguments,
            result.stdout,
            result.stderr,
        )
        assert "Usage:" in result.stderr or "Bitsy" in result.stderr, result.stderr

print(
    f"Bitsybox {system}: native world, >256-byte literal path, menu-exit, invalid-file refusal and no media writes passed"
)

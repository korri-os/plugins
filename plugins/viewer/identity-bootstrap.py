"""Run as the runtime user. Only the public client certificate crosses stdout.

Adapted from plugins/moonlight/identity-bootstrap.py for Korri's viewer. The
viewer makes its identity on `pair` (Identity::load_or_generate, before it
reads the server pin), not on Moonlight's `list`, and it makes no
uniqueid.dat: without one it uses Moonlight's fixed ID. A uniqueid.dat that
Moonlight left in the shared key directory is checked like the others.
"""
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


def private_file(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size == 0:
        raise ValueError("viewer identity files must be runtime-owned private regular files")


def public_certificate(executable, keydir):
    directory = keydir.lstat()
    if not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.geteuid() or stat.S_IMODE(directory.st_mode) != 0o700:
        raise ValueError("viewer identity directory must be runtime-owned and mode 0700")
    files = [keydir / name for name in ("client.pem", "key.pem")]
    if not any(path.exists() for path in files):
        environment = dict(os.environ, KORRI_MOONLIGHT_SERVER_CERTIFICATE="/dev/null")
        # The identity is made before the pin is read. The empty pin then
        # stops the viewer before it can contact any host.
        subprocess.run([executable, "pair", "-keydir", str(keydir), "-port", "9", "127.0.0.1"],
                       env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=10, check=False)
    for path in files:
        private_file(path)
    unique = keydir / "uniqueid.dat"
    if unique.exists() or unique.is_symlink():
        private_file(unique)
    # Never open key.pem. Its only consumer is the viewer in the runtime unit.
    with files[0].open("rb") as certificate:
        data = certificate.read(12289)
    if len(data) > 12288 or re.fullmatch(rb"-----BEGIN CERTIFICATE-----\r?\n(?:[A-Za-z0-9+/=]+\r?\n)+-----END CERTIFICATE-----\r?\n?", data) is None:
        raise ValueError("viewer public certificate is malformed or exceeds its bound")
    return data


if __name__ == "__main__":
    try:
        if len(sys.argv) != 3:
            raise ValueError("identity bootstrap requires executable and keydir")
        sys.stdout.buffer.write(public_certificate(sys.argv[1], Path(sys.argv[2])))
    except (OSError, ValueError, subprocess.SubprocessError):
        print("viewer identity bootstrap failed", file=sys.stderr)
        sys.exit(1)

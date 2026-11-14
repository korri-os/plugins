"""The helper against a fixture key directory and against the real viewer."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

helper, viewer = sys.argv[1], sys.argv[2]
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    keydir = root / "identity"
    keydir.mkdir(mode=0o700)
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(keydir / "key.pem"),
                    "-out", str(keydir / "client.pem"), "-days", "1", "-subj", "/CN=fixture"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for path in keydir.iterdir():
        path.chmod(0o600)
    certificate = (keydir / "client.pem").read_bytes()
    private_lines = (keydir / "key.pem").read_bytes().splitlines()
    result = subprocess.run([helper, "/not-invoked", str(keydir)], capture_output=True, check=True)
    assert result.stdout == certificate
    assert result.stderr == b""
    assert all(line not in result.stdout for line in private_lines)
    # Moonlight's uniqueid.dat in the shared directory is held to the same rule.
    (keydir / "uniqueid.dat").write_text("0123456789ABCDEF")
    (keydir / "uniqueid.dat").chmod(0o644)
    result = subprocess.run([helper, "/not-invoked", str(keydir)], capture_output=True)
    assert result.returncode != 0 and result.stdout == b""
    (keydir / "uniqueid.dat").chmod(0o600)
    assert subprocess.run([helper, "/not-invoked", str(keydir)], capture_output=True, check=True).stdout == certificate
    # Public private-key modes fail without any certificate output.
    (keydir / "key.pem").chmod(0o644)
    result = subprocess.run([helper, "/not-invoked", str(keydir)], capture_output=True)
    assert result.returncode != 0 and result.stdout == b""
    assert all(line not in result.stderr for line in private_lines)

    # The real viewer makes a new identity; the empty pin stops it before any host.
    fresh = root / "fresh"
    fresh.mkdir(mode=0o700)
    result = subprocess.run([helper, viewer, str(fresh)], capture_output=True, check=True)
    assert result.stdout == (fresh / "client.pem").read_bytes()
    assert result.stdout.startswith(b"-----BEGIN CERTIFICATE-----")
    assert sorted(path.name for path in fresh.iterdir()) == ["client.pem", "key.pem"]
    for path in fresh.iterdir():
        assert os.stat(path).st_mode & 0o777 == 0o600
    # A second run reuses it.
    again = subprocess.run([helper, viewer, str(fresh)], capture_output=True, check=True)
    assert again.stdout == result.stdout
    # A half identity is not completed or replaced.
    (fresh / "client.pem").unlink()
    result = subprocess.run([helper, viewer, str(fresh)], capture_output=True)
    assert result.returncode != 0 and result.stdout == b""
    assert not (fresh / "client.pem").exists()

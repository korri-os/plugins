import os
from pathlib import Path
import subprocess
import sys
import tempfile

helper = sys.argv[1]
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    keydir = root / "identity"
    keydir.mkdir(mode=0o700)
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(keydir / "key.pem"),
                    "-out", str(keydir / "client.pem"), "-days", "1", "-subj", "/CN=fixture"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (keydir / "uniqueid.dat").write_text("fixture-client")
    for path in keydir.iterdir():
        path.chmod(0o600)
    certificate = (keydir / "client.pem").read_bytes()
    private_lines = (keydir / "key.pem").read_bytes().splitlines()
    result = subprocess.run([helper, "/not-invoked", str(keydir)], capture_output=True, check=True)
    assert result.stdout == certificate
    assert result.stderr == b""
    assert all(line not in result.stdout for line in private_lines)
    # Symlinks and public private-key modes fail without any certificate output.
    (keydir / "key.pem").chmod(0o644)
    result = subprocess.run([helper, "/not-invoked", str(keydir)], capture_output=True)
    assert result.returncode != 0 and result.stdout == b""
    assert all(line not in result.stderr for line in private_lines)

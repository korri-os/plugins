"""Real self-signed TLS: accept broker's certificate; reject another server."""
import http.server
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import threading

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for name in ("authorized", "other"):
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                        "-subj", f"/CN={name}", "-keyout", str(root / f"{name}.key"),
                        "-out", str(root / f"{name}.pem"), "-days", "1"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (root / "client.pem").write_bytes((root / "authorized.pem").read_bytes())
    (root / "key.pem").write_bytes((root / "authorized.key").read_bytes())

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"authorized TLS response"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def handle(self):
            try:
                super().handle()
            except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
                pass  # The refused TLS peer can close before sending HTTP.

        def log_message(self, *args):
            pass

    for name, accepted in (("authorized", True), ("other", False)):
        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(root / f"{name}.pem", root / f"{name}.key")
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            env = {k: v for k, v in os.environ.items() if k.lower() not in {"http_proxy", "https_proxy", "all_proxy"}}
            env.update(NO_PROXY="127.0.0.1", no_proxy="127.0.0.1", KORRI_MOONLIGHT_SERVER_CERTIFICATE=str(root / "authorized.pem"))
            url = f"https://127.0.0.1:{server.server_port}/"
            result = subprocess.run([sys.argv[1], str(root), url], env=env, timeout=5)
            assert (result.returncode == 0) == accepted, name
            env["KORRI_MOONLIGHT_SERVER_CERTIFICATE"] = str(root / "missing.pem")
            assert subprocess.run([sys.argv[1], str(root), url], env=env, timeout=5).returncode != 0
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
print("matching broker certificate accepted; other and missing pins refused")

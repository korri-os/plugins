import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from rpc import Rpc


class RpcTests(unittest.TestCase):
    def test_real_localhost_wire_and_busy_observation(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append((self.path, self.headers.get("Authorization"), body))
                result = {
                    "_tag": body["_tag"],
                    "outcome": {
                        "_tag": "Ok",
                        "payload": {"observationFailure": {"code": "Unavailable"}},
                    },
                }
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

            def log_message(self, *_args):
                pass

        with (
            tempfile.TemporaryDirectory() as root,
            ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server,
        ):
            path = Path(root) / "capability"
            path.write_text("test-only-not-a-real-capability\n")
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                rpc = Rpc(server.server_port, path)
                with self.assertRaisesRegex(RuntimeError, "observation failed"):
                    rpc.require_idle()
                self.assertEqual(requests[0][0], "/rpc")
                self.assertEqual(
                    requests[0][1], "Bearer test-only-not-a-real-capability"
                )
                self.assertEqual(
                    requests[0][2], {"_tag": "app.session.status", "payload": {}}
                )
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()

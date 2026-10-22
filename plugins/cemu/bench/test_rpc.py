import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from bench import Rpc, RpcError, require_idle


class RpcTests(unittest.TestCase):
    def test_real_http_contract_and_idle_failures(self):
        requests = []
        observed_paths = []
        outcomes = [
            {"_tag": "Ok", "payload": {}},
            {"_tag": "Err", "payload": {"code": "NoActiveSession", "message": "idle"}},
            {
                "_tag": "Err",
                "payload": {"code": "SessionCompleted", "message": "finished"},
            },
            {"_tag": "Ok", "payload": {"active": {"launchId": "other"}}},
            {"_tag": "Ok", "payload": {"pendingLaunches": [{"launchId": "other"}]}},
            {
                "_tag": "Err",
                "payload": {"code": "ObservationFailed", "message": "unknown"},
            },
        ]

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                observed_paths.append(self.path)
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append((self.headers.get("Authorization"), body))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {"_tag": body["_tag"], "outcome": outcomes.pop(0)}
                    ).encode()
                )

            def log_message(self, *_):
                pass

        with (
            tempfile.TemporaryDirectory() as tmp,
            ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server,
        ):
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            try:
                key = Path(tmp) / "capability"
                key.write_text("test-capability")
                rpc = Rpc(server.server_port, key)
                for _ in range(3):
                    require_idle(rpc)
                for _ in range(2):
                    with self.assertRaisesRegex(RuntimeError, "Refusing"):
                        require_idle(rpc)
                with self.assertRaises(RpcError):
                    require_idle(rpc)
                self.assertEqual(observed_paths, ["/rpc"] * 6)
                self.assertEqual(len(requests), 6)
                for auth, body in requests:
                    self.assertEqual(auth, "Bearer test-capability")
                    self.assertEqual(
                        body, {"_tag": "app.session.status", "payload": {}}
                    )
            finally:
                server.shutdown()
                worker.join()


if __name__ == "__main__":
    unittest.main()

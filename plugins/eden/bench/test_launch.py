import argparse
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from bench import collect


class LaunchFailureTests(unittest.TestCase):
    def test_start_failure_stops_exact_reservation_and_writes_failed_report(self):
        calls = []
        launch = "acceptance-test-only"

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                request = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"]))
                )
                calls.append(request)
                tag = request["_tag"]
                if tag == "app.session.start":
                    outcome = {"_tag": "Err", "payload": {"code": "UnsupportedRunner"}}
                else:
                    payload = (
                        {"launchId": launch}
                        if tag == "app.session.reserve"
                        else {"phase": "stopped"}
                        if tag == "app.session.stop"
                        else {}
                    )
                    outcome = {"_tag": "Ok", "payload": payload}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"_tag": tag, "outcome": outcome}).encode())

            def log_message(self, *_args):
                pass

        with (
            tempfile.TemporaryDirectory() as root,
            ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server,
        ):
            base = Path(root)
            credential = base / "capability"
            credential.write_text("test-only-not-a-real-capability")
            args = argparse.Namespace(
                input_script=None,
                eden_log=None,
                port=server.server_port,
                capability_file=credential,
                mangohud_dir=base,
                output=base / "report",
                game="test-game",
                runner="test-runner",
                seconds=180,
            )
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                with self.assertRaisesRegex(RuntimeError, "UnsupportedRunner"):
                    collect(args)
                self.assertEqual(
                    [call["_tag"] for call in calls],
                    [
                        "app.session.status",
                        "app.session.reserve",
                        "app.session.start",
                        "app.session.stop",
                        "app.session.status",
                    ],
                )
                self.assertEqual(calls[-2]["payload"], {"expectedLaunchId": launch})
                report = (args.output / "report.md").read_text()
                self.assertIn("FAILED", report)
                self.assertIn("unavailable", report)
                self.assertNotIn(credential.read_text(), report)
                cleanup = json.loads((args.output / "cleanup.json").read_text())
                self.assertEqual(
                    cleanup,
                    {
                        "remaining_cgroup": {},
                        "new_emulators_or_wrappers": {},
                        "observer_remaining": False,
                        "error": "",
                    },
                )
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()

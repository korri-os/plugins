import json
import tempfile
import threading
import unittest
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from bench import (
    Rpc,
    RpcError,
    namespace_pid,
    require_idle,
    end_exact,
    verify_native_idle,
    wait_for_exit,
)


class RpcTests(unittest.TestCase):
    def test_terminal_failure_requires_conclusive_native_idle(self):
        verify_native_idle("", False)
        with self.assertRaisesRegex(RuntimeError, "activity remains"):
            verify_native_idle("korri-game-active.service loaded active running", False)
        with self.assertRaisesRegex(RuntimeError, "activity remains"):
            verify_native_idle("", True)

    def test_private_pid_namespace_identity(self):
        self.assertEqual(
            namespace_pid("Name:\tretroarch\nNSpid:\t20407\t38\n", 20407), 38
        )
        self.assertEqual(namespace_pid("Name:\tfixture\n", 500), 500)

    def serve(self, replies):
        """Answer each request with the next outcome and record it."""
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(body)
                response = {"_tag": body["_tag"], "outcome": replies.pop(0)}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            def log_message(self, *_):
                pass

        tmp = tempfile.TemporaryDirectory()
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever)
        worker.start()

        def stop():
            server.shutdown()
            server.server_close()
            worker.join()
            tmp.cleanup()

        self.addCleanup(stop)
        key = Path(tmp.name) / "capability"
        key.write_text("test-capability")
        return Rpc(server.server_port, key), requests

    def test_end_uses_current_korrid_tag_and_phases(self):
        def ok(phase):
            return {"_tag": "Ok", "payload": {"phase": phase}}

        gone = {
            "_tag": "Err",
            "payload": {"code": "NoActiveSession", "message": "no host launch"},
        }
        rpc, requests = self.serve([ok("ended")])
        self.assertEqual(end_exact(rpc, "owned-launch", poll_seconds=0), [])
        self.assertEqual(
            requests,
            [
                {
                    "_tag": "app.session.end",
                    "payload": {"expectedLaunchId": "owned-launch"},
                }
            ],
        )
        # A pending end that finishes between polls reports the launch gone.
        rpc, requests = self.serve([ok("pending"), ok("pending"), gone])
        self.assertEqual(end_exact(rpc, "owned-launch", poll_seconds=0), [])
        self.assertEqual(len(requests), 3)
        # Without a pending reply first, a gone launch is the caller's decision.
        rpc, _ = self.serve([gone])
        with self.assertRaises(RpcError) as raised:
            end_exact(rpc, "owned-launch", poll_seconds=0)
        self.assertEqual(raised.exception.code, "NoActiveSession")
        # The removed reply phase is not accepted as success.
        rpc, _ = self.serve([ok("stopped")])
        with self.assertRaisesRegex(ValueError, "Unknown app.session.end phase"):
            end_exact(rpc, "owned-launch", poll_seconds=0)

    def test_wait_for_exit_polls_until_native_idle(self):
        calls = []

        def guard():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("activity remains")

        self.assertEqual(wait_for_exit("korri-game-absent.service", guard, 5, 0), "")
        self.assertEqual(len(calls), 3)

        def busy():
            raise RuntimeError("activity remains")

        self.assertEqual(
            wait_for_exit("korri-game-absent.service", busy, 0.02, 0.005),
            "activity remains",
        )

    def test_stop_recovery_uses_status_only_and_requires_native_idle(self):
        requests = []
        status_codes = ["HostRecoveryBlocked", "HostLaunchFailed"]

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(body)
                code = (
                    "HostRecoveryBlocked"
                    if body["_tag"] == "app.session.end"
                    else status_codes.pop(0)
                )
                response = {
                    "_tag": body["_tag"],
                    "outcome": {
                        "_tag": "Err",
                        "payload": {"code": code, "message": code},
                    },
                }
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

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
                warnings = end_exact(
                    rpc,
                    "owned-launch",
                    partial(verify_native_idle, "", False),
                    recovery_seconds=1,
                    poll_seconds=0.005,
                )
                self.assertEqual(len(warnings), 1)
                self.assertIn("resolved by korrid", warnings[0])
                self.assertEqual(
                    [request["_tag"] for request in requests],
                    ["app.session.end", "app.session.status", "app.session.status"],
                )
                self.assertEqual(
                    requests[0]["payload"], {"expectedLaunchId": "owned-launch"}
                )
                # Leaving RecoveryBlocked is insufficient while a native cgroup is populated.
                requests.clear()
                status_codes[:] = ["HostLaunchFailed"] * 100
                with self.assertRaisesRegex(RuntimeError, "recovery did not clear"):
                    end_exact(
                        rpc,
                        "owned-launch",
                        partial(verify_native_idle, "", True),
                        recovery_seconds=0.03,
                        poll_seconds=0.005,
                    )
                self.assertEqual(
                    sum(request["_tag"] == "app.session.end" for request in requests),
                    1,
                )
                # An unresolved core recovery block must not trigger any native mutation.
                requests.clear()
                status_codes[:] = ["HostRecoveryBlocked"] * 100
                with self.assertRaisesRegex(RuntimeError, "no journal/reset/restart"):
                    end_exact(
                        rpc,
                        "owned-launch",
                        partial(verify_native_idle, "", False),
                        recovery_seconds=0.03,
                        poll_seconds=0.005,
                    )
                self.assertTrue(
                    all(
                        request["_tag"] == "app.session.status"
                        for request in requests[1:]
                    )
                )
            finally:
                server.shutdown()
                worker.join()

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

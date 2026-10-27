"""Exercise real process/window waits under Xvfb, including a frontend hang."""

import subprocess
import sys
import time
import unittest

from runtime import wait_for_window


class WindowWaitTest(unittest.TestCase):
    def test_exited_frontend_fails_without_spending_the_window_deadline(self):
        with subprocess.Popen(
            [sys.executable, "-c", "raise SystemExit(23)"]
        ) as process:
            process.wait()
            started = time.monotonic()
            with self.assertRaisesRegex(AssertionError, "exited.*23"):
                wait_for_window(process, timeout=5)
            self.assertLess(time.monotonic() - started, 1)

    def test_live_frontend_without_a_window_still_fails(self):
        with subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"]
        ) as process:
            try:
                with self.assertRaisesRegex(AssertionError, "No visible Pyxel window"):
                    wait_for_window(process, timeout=0.2)
                self.assertIsNone(process.poll())
            finally:
                process.terminate()


if __name__ == "__main__":
    unittest.main()

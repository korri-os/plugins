"""Exercise runtime.sh itself, with local sockets and controlled native commands."""
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(sys.argv.pop(1)) if len(sys.argv) > 1 else Path(__file__).with_name("runtime.sh")


class RuntimeArguments(unittest.TestCase):
    def run_runtime(self, contents):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "user"
            (runtime / "pulse").mkdir(parents=True)
            sockets = []
            try:
                for path in [runtime / "korri-wayland", root / "sway.sock", runtime / "pulse/native"]:
                    listener = socket.socket(socket.AF_UNIX)
                    listener.bind(str(path))
                    sockets.append(listener)
                tools = root / "tools/bin"
                tools.mkdir(parents=True)
                programs = {
                    "pw-metadata": "print('Found \"default\" metadata')",
                    "swaymsg": "print('[{\"active\": true, \"name\": \"test\", \"current_mode\": {\"width\": 640, \"height\": 480}}]')",
                    "sunshine": "import json, sys; print(json.dumps(sys.argv[1:]))",
                }
                for name, body in programs.items():
                    executable = tools / name
                    executable.write_text(f"#!{sys.executable}\n{body}\n")
                    executable.chmod(0o755)
                args_file = root / "sunshine.args"
                if contents is not None:
                    args_file.write_text(contents)
                text = SOURCE.read_text()
                replacements = {
                    "@coreutils@/bin/": "", "@gnugrep@/bin/": "", "@jq@/bin/": "",
                    "@pipewire@": str(tools.parent), "@sway@": str(tools.parent), "@sunshine@": str(tools.parent),
                    "@apps@": str(root / "apps.json"), "/run/user/1000": str(runtime),
                    "/run/korri-compositor/sway-ipc.sock": str(root / "sway.sock"),
                    "/run/korri-launch-services/korri-sunshine.args": str(args_file),
                    "/home/korri": str(root / "home"),
                }
                for before, after in replacements.items():
                    text = text.replace(before, after)
                result = subprocess.run([shutil.which("bash"), "-c", text], text=True, capture_output=True, check=True, timeout=5)
                return json.loads(result.stdout), str(root)
            finally:
                for listener in sockets:
                    listener.close()

    def test_absent_and_empty_file_keep_native_arguments_without_encoder_auto(self):
        for contents in [None, ""]:
            with self.subTest(contents=contents):
                args, root = self.run_runtime(contents)
                self.assertEqual(args, [f"{root}/home/.config/sunshine/sunshine.conf", "log_path=/dev/null", "capture=kms", "capture_rt_priority=5", f"file_apps={root}/apps.json"])

    def test_only_valid_lines_are_appended_as_single_arguments_in_order(self):
        args, _ = self.run_runtime("encoder=v4l2m2m\nmin_log_level=debug\n\nBad_key=ignored\nbad-key=ignored\n=empty-key\nmissing-equals\n key=space\nkey name=space\nexternal_ip=has spaces = and \\\\backslash\ncontroller=disabled\nkey=\n0_ok=value\nsw_tune=$(touch /should-not-run)\nqp=31")
        self.assertEqual(args[5:], ["encoder=v4l2m2m", "min_log_level=debug", "external_ip=has spaces = and \\\\backslash", "controller=disabled", "key=", "0_ok=value", "sw_tune=$(touch /should-not-run)", "qp=31"])
        self.assertNotIn("encoder=auto", args)

    def test_newline_cannot_be_part_of_an_argument(self):
        args, _ = self.run_runtime("encoder=rkmpp\ncontinuation without equals\nqp=28\n")
        self.assertEqual(args[5:], ["encoder=rkmpp", "qp=28"])
        self.assertTrue(all("\n" not in arg for arg in args))


if __name__ == "__main__":
    unittest.main()

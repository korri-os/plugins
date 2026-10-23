import configparser
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from p1_controls import Device, configure, find_seat, uses_defaults

CRUDINI = sys.argv.pop(1)
TEMPLATE = Path(__file__).with_name("p1-controls.ini")
GUID = "030000005e0400008e02000014010000"


class P1ControlsTests(unittest.TestCase):
    def native(self, root: str, flag: str = "true") -> Path:
        path = Path(root) / "qt-config.ini"
        path.write_text(
            "[Controls]\n"
            "player_0_button_a=engine:keyboard,code:67\n"
            f"player_0_button_a\\default={flag}\n"
            "player_1_button_a=engine:keyboard,code:99\n"
            "player_1_button_a\\default=false\n"
            "[Renderer]\nresolution_setup=2\n"
        )
        return path

    def test_default_with_seat_uses_native_ui_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = self.native(root)
            self.assertEqual(
                configure(path, Device("Korri Seat P1", GUID, 2), TEMPLATE, CRUDINI),
                "configured",
            )
            native = configparser.ConfigParser(interpolation=None)
            native.read(path)
            self.assertEqual(
                native.get("Controls", "player_0_button_a").strip('"'),
                f"engine:sdl,port:2,guid:{GUID},button:1",
            )
            self.assertFalse(
                native.getboolean("Controls", "player_0_button_a\\default")
            )
            self.assertIn(
                "axis_x:0,axis_y:1", native.get("Controls", "player_0_lstick")
            )
            self.assertEqual(native.get("Controls", "player_0_motionleft"), "[empty]")
            self.assertEqual(
                native.get("Controls", "player_1_button_a"), "engine:keyboard,code:99"
            )
            self.assertEqual(native.get("Renderer", "resolution_setup"), "2")
            self.assertFalse(native.has_option("Controls", "player_0_body_color_left"))

    def test_person_changed_p1_is_byte_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = self.native(root, "false")
            before = path.read_bytes()
            self.assertEqual(
                configure(path, Device("Korri Seat P1", GUID, 0), TEMPLATE, CRUDINI),
                "kept",
            )
            self.assertEqual(path.read_bytes(), before)

    def test_missing_seat_keeps_native_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = self.native(root)
            before = path.read_bytes()
            self.assertEqual(configure(path, None, TEMPLATE, CRUDINI), "missing")
            self.assertEqual(path.read_bytes(), before)

    def test_new_account_without_control_keys_is_default(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "qt-config.ini"
            path.write_text("[Data%20Storage]\nsave_directory=/existing\n")
            self.assertTrue(uses_defaults(path))
            self.assertEqual(
                configure(path, Device("Korri Seat P1", GUID, 0), TEMPLATE, CRUDINI),
                "configured",
            )

    def test_any_person_set_p1_field_prevents_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = self.native(root)
            path.write_text(
                path.read_text().replace(
                    "[Renderer]", "player_0_connected\\default=false\n[Renderer]"
                )
            )
            self.assertFalse(uses_defaults(path))

    def test_only_the_named_p1_seat_is_selected(self) -> None:
        devices = [Device("Korri Seat P2", GUID, 0), Device("Korri Seat P1", GUID, 1)]
        self.assertEqual(find_seat(devices), devices[1])
        self.assertIsNone(find_seat(devices[:1]))
        self.assertIsNone(find_seat(devices + [Device("Korri Seat P1", GUID, 2)]))

    def test_unavailable_probe_logs_one_line_and_does_not_fail_launch(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = self.native(root)
            before = path.read_bytes()
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("p1_controls.py")),
                    str(path),
                    str(TEMPLATE),
                    "/missing-sdl2",
                    "/missing-sdl3",
                    CRUDINI,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(len(result.stderr.splitlines()), 1)
            self.assertIn("keeping Eden's native defaults", result.stderr)
            self.assertEqual(path.read_bytes(), before)

    def test_user_set_launch_does_not_require_a_probe(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = self.native(root, "false")
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("p1_controls.py")),
                    str(path),
                    str(TEMPLATE),
                    "/missing-sdl2",
                    "/missing-sdl3",
                    CRUDINI,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")

    def test_invalid_native_flags_do_not_echo_values(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = self.native(root, "private-native-value")
            with self.assertRaises(ValueError) as raised:
                uses_defaults(path)
            self.assertNotIn("private-native-value", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

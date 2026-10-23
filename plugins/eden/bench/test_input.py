import tempfile
import unittest
from pathlib import Path

from input import read_events


class InputTests(unittest.TestCase):
    def test_native_evemu_script_validates_before_creating_device(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "pad.events"
            path.write_text("# evemu\nE: 0.000 0001 0130 1\nE: 0.100 0001 0130 0\n")
            self.assertEqual(
                read_events(path), [(0.0, 1, 0x130, 1), (0.1, 1, 0x130, 0)]
            )

    def test_rejects_keyboard_guide_out_of_range_and_reverse_time(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "pad.events"
            for text in (
                "E: 0 0001 001c 1",
                "E: 0 0001 013c 1",
                "E: nan 0001 0130 1",
                "E: 0 0003 0000 99999",
                "E: 1 0001 0130 1\nE: 0 0001 0130 0",
                "",
            ):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    read_events(path)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from gamepad import read_script
from metrics import fps_bins, summarize


class MeasurementTests(unittest.TestCase):
    def test_counts_only_selected_presentations_and_keeps_zero_seconds(self):
        events = [
            (100.1, 7, 0),
            (100.2, 7, 1),
            (100.3, 7, 2),
            (101.2, 9, 0),
            (102.5, 7, 0),
            (103.0, 7, 0),
        ]
        self.assertEqual(fps_bins(events, 7, 100, 3), [2, 0, 1])

    def test_nearest_rank_percentiles_and_min(self):
        self.assertEqual(
            summarize(list(range(1, 101))),
            {"samples": 100, "median": 50.5, "p10": 10, "p1": 1, "min": 1},
        )

    def test_no_samples_is_not_zero_fps(self):
        with self.assertRaises(ValueError):
            summarize([])

    def test_native_evemu_input_and_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.events"
            path.write_text(
                "# native evemu\nE: 0.000000 0001 0130 1\nE: 0.100000 0001 0130 0\n"
            )
            self.assertEqual(read_script(path), [(0.0, 1, 304, 1), (0.1, 1, 304, 0)])
            for text in [
                "E: 0.1 0001 0001 1",
                "E: 1 0001 0130 2",
                "E: -1 0001 0130 1",
                "E: 1 0001 0130 1\nE: 0 0001 0130 0",
            ]:
                path.write_text(text)
                with self.assertRaises(ValueError):
                    read_script(path)


if __name__ == "__main__":
    unittest.main()

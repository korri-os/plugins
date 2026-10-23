import tempfile
import unittest
from pathlib import Path

from metrics import Presentation, fps_window, read_presentations, summarize


class MetricsTests(unittest.TestCase):
    def test_nearest_rank_percentiles_and_even_median(self):
        self.assertEqual(
            summarize(list(range(1, 101))), {"median": 50.5, "p10": 10, "p1": 1}
        )
        self.assertEqual(summarize([0]), {"median": 0, "p10": 0, "p1": 0})

    def test_invalid_samples_do_not_produce_a_report(self):
        for values in ([], [-1], [float("nan")], [float("inf")]):
            with self.assertRaises(ValueError):
                summarize(values)

    def test_discard_100_seconds_count_only_selected_window_and_exclude_skip(self):
        events = [
            Presentation("frame", second + index / 60, 7, 0)
            for second in range(1, 281)
            for index in range(60)
        ]
        events += [Presentation("frame", 100.5, 7, 2)] * 10
        window, values = fps_window(events, 100, 180)
        self.assertEqual(window, 7)
        self.assertEqual(values, [60] * 180)

    def test_zero_bins_are_real_stalls_not_removed(self):
        events = [Presentation("frame", 99.5, 7, 0), Presentation("frame", 100.5, 7, 1)]
        self.assertEqual(fps_window(events, 100, 3)[1], [1, 0, 0])
        with self.assertRaisesRegex(ValueError, "No game frames"):
            fps_window(events[:1], 100, 3)

    def test_destroyed_or_replaced_game_window_fails(self):
        events = [Presentation("frame", 99.5, 7, 0), Presentation("frame", 100.5, 7, 0)]
        with self.assertRaisesRegex(ValueError, "destroyed"):
            fps_window(events + [Presentation("destroy", 101, 7, 0)], 100, 3)
        with self.assertRaisesRegex(ValueError, "replaced"):
            fps_window(events + [Presentation("frame", 101, 8, 0)], 100, 3)

    def test_live_csv_discards_partial_row_and_rejects_bad_values(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "present.csv"
            path.write_text(
                "event,ust_us,window,mode\nframe,1000000,7,0\nframe,2000000,"
            )
            self.assertEqual(read_presentations(path), [Presentation("frame", 1, 7, 0)])
            path.write_text("event,ust_us,window,mode\nframe,wrong,7,0\n")
            with self.assertRaises(ValueError):
                read_presentations(path)


if __name__ == "__main__":
    unittest.main()

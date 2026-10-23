import argparse
import json
import tempfile
import unittest
from pathlib import Path

from bench import Rpc, run
from gameplay_gate import GameplayGate, NotMeasured, Reference
from reporting import fps_section, not_measured_report


class GameplayGateTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parent / "references"
        self.reference = Reference.load(root / "botw-1920x1080.json")
        self.frames = json.loads((root / "botw-1920x1080-checks.json").read_text())

    def test_recorded_frame_statistics_classify_without_images(self):
        for frame in self.frames:
            with self.subTest(frame=frame["label"]):
                self.assertEqual(
                    self.reference.classify(frame["statistics"]), frame["label"]
                )

    def test_warmup_requires_ordered_title_loading_gameplay_and_end_check(self):
        frames = {frame["label"]: frame["statistics"] for frame in self.frames}
        gate = GameplayGate(self.reference, started=0, timeout=20)
        gate.observe(frames["title"], 2)
        self.assertFalse(gate.title_ready)
        gate.observe(frames["title"], 3)
        self.assertTrue(gate.title_ready)
        gate.begin_input(3)
        gate.observe(frames["gameplay"], 4)
        self.assertFalse(gate.ready)
        gate.observe(frames["loading"], 5)
        gate.observe(frames["gameplay"], 6)
        gate.observe(frames["gameplay"], 7)
        self.assertTrue(gate.ready)
        gate.finish(frames["gameplay"], 30)
        self.assertEqual(gate.timings["titleAt"], 3)
        self.assertEqual(gate.timings["loadingAt"], 5)
        self.assertEqual(gate.timings["gameplayAt"], 7)
        with self.assertRaisesRegex(NotMeasured, "end"):
            gate.finish(frames["title"], 30)

    def test_title_and_loading_timeout_never_publish_numbers(self):
        frames = {frame["label"]: frame["statistics"] for frame in self.frames}
        gate = GameplayGate(self.reference, started=0, timeout=10)
        with self.assertRaisesRegex(NotMeasured, "title"):
            gate.observe(frames["gameplay"], 11)
        gate = GameplayGate(self.reference, started=0, timeout=10)
        gate.observe(frames["title"], 1)
        gate.observe(frames["title"], 2)
        gate.begin_input(2)
        with self.assertRaisesRegex(NotMeasured, "loading"):
            gate.observe(frames["title"], 13)
        report = not_measured_report("loading timeout", gate.timings, "not launched")
        self.assertIn("Status: not measured", report)
        self.assertIn("title at: 2", report)
        self.assertIn("loading at: not observed", report)
        for forbidden in ("median", "p10", "p1", "| min", "## FPS"):
            self.assertNotIn(forbidden, report)
        self.assertEqual(fps_section("gate failed", {}), [])

    def test_real_run_boundary_writes_not_measured_without_fps_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capability = root / "capability"
            capability.write_text("test-capability")
            args = argparse.Namespace(
                reference=Path(__file__).parent / "references/botw-1920x1080.json",
                game="different-game",
            )
            with self.assertRaisesRegex(ValueError, "different game"):
                run(Rpc(1, capability), args, root / "run", "invalid")
            report = (root / "run/report.md").read_text()
            self.assertIn("Status: not measured", report)
            self.assertNotIn("## FPS", report)
            self.assertNotIn("median", report)
            self.assertFalse((root / "run/fps.json").exists())

    def test_wrong_capture_size_and_unknown_frame_fail_closed(self):
        frame = dict(self.frames[0]["statistics"])
        frame["width"] = 123
        with self.assertRaisesRegex(NotMeasured, "resolution"):
            self.reference.classify(frame)
        frame = dict(self.frames[0]["statistics"])
        frame["rgb"] = [0] * len(frame["rgb"])
        frame["titleCoverage"] = 0
        self.assertEqual(self.reference.classify(frame), "unknown")


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from gamepad import Gamepad
from gameplay_gate import FrameCapture, Reference
from save_proof import SaveProof, game_data


class RecordingPad(Gamepad):
    def __init__(self, output: Path, write_save: bool):
        self.events: list[tuple[float, int, int, int]] = []
        self.output = output
        self.write_save = write_save
        self.confirm = 0

    def send(self, event):
        self.events.append(event)
        if event[2:] == (0x131, 1):
            self.confirm += 1
            if self.confirm == 2 and self.write_save:
                self.output.write_bytes(b"new in-game save")


class RecordedFrameCapture(FrameCapture):
    def capture(self):
        root = Path(__file__).parent / "references"
        return next(
            frame["statistics"]
            for frame in json.loads((root / "botw-1920x1080-checks.json").read_text())
            if frame["label"] == "gameplay"
        )


class SaveProofTests(unittest.TestCase):
    def test_hash_mtime_and_native_save_root_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            native = root / "3" / "game_data.sav"
            native.parent.mkdir()
            native.write_bytes(b"original game progress")
            before = game_data(root)
            native.write_bytes(b"new game progress")
            after = game_data(root)
            self.assertNotEqual(
                before["3/game_data.sav"]["sha256"], after["3/game_data.sav"]["sha256"]
            )
            self.assertNotEqual(
                before["3/game_data.sav"]["mtimeNs"],
                after["3/game_data.sav"]["mtimeNs"],
            )
            proof = SaveProof(root, root)
            proof.verify_declaration(
                {1: {"argv": ["plugin-launch", json.dumps({"saveRoot": str(root)})]}}
            )
            with self.assertRaisesRegex(RuntimeError, "declared saveRoot"):
                proof.verify_declaration({1: {"argv": ["Cemu"]}})
            native.unlink()
            with self.assertRaisesRegex(RuntimeError, "No game_data"):
                game_data(root)

    def test_bounded_route_uses_all_tabs_and_needs_changed_hash_and_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            native = root / "game_data.sav"
            native.write_bytes(b"original")
            proof = SaveProof(root, root, wait=lambda _: None)
            pad = RecordingPad(native, write_save=True)
            reference = Reference.load(
                Path(__file__).parent / "references/botw-1920x1080.json"
            )
            capture = RecordedFrameCapture(reference, "korri", root, "unused")
            tree: dict[int, dict[str, object]] = {
                1: {"argv": [json.dumps({"saveRoot": str(root)})]}
            }
            proof.save(pad, capture, tree)
            self.assertTrue(proof.changed)
            pressed = [event[2] for event in pad.events if event[3] == 1]
            self.assertEqual(pressed, [0x13B] + [0x137] * 10 + [0x131, 0x131, 0x13B])
            unchanged = SaveProof(root, root, wait=lambda _: None, timeout_s=0)
            with self.assertRaisesRegex(RuntimeError, "Save route unproven"):
                unchanged.save(RecordingPad(native, write_save=False), capture, tree)

    def test_symlink_is_not_a_save_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "original"
            original.write_bytes(b"not a native save")
            (root / "game_data.sav").symlink_to(original)
            with self.assertRaisesRegex(RuntimeError, "Unsafe"):
                game_data(root)


if __name__ == "__main__":
    unittest.main()

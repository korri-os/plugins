import json
import tempfile
import unittest
from pathlib import Path

from speaker import Speaker

SINK = "alsa_output.platform-sound.HiFi__Speaker__sink"


class FakeWpctl:
    """Answers `wpctl` like PipeWire, for one sink that may be renumbered."""

    def __init__(self, muted: bool, node: str = "53"):
        self.muted = muted
        self.node = node
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> str:
        self.commands.append(command)
        args = command[command.index("wpctl") + 1 :]
        if args == ["status", "-n"]:
            return (
                "Audio\n ├─ Sinks:\n"
                f" │  *   {self.node}. {SINK} [vol: 0.18]\n"
                f" │      54. {SINK}_monitor_other [vol: 1.00]\n"
            )
        if args[0] == "get-volume":
            assert args[1] == self.node
            return "Volume: 0.18" + (" [MUTED]" if self.muted else "") + "\n"
        if args[0] == "set-mute":
            assert args[1] == self.node
            self.muted = args[2] == "1"
            return ""
        raise AssertionError(args)


class SpeakerTests(unittest.TestCase):
    def test_restores_previous_unmuted_state(self):
        fake = FakeWpctl(muted=False)
        with tempfile.TemporaryDirectory() as tmp:
            speaker = Speaker(SINK, "korri", Path("/run/user/1000"), Path(tmp), fake)
            speaker.mute()
            self.assertTrue(fake.muted)
            # Something unmutes the sink and renumbers it; hold mutes it again.
            fake.muted = False
            fake.node = "61"
            speaker.hold()
            self.assertTrue(fake.muted)
            speaker.restore()
            self.assertFalse(fake.muted)
            state = json.loads((Path(tmp) / "speaker.json").read_text())
            self.assertEqual(
                state,
                {"sink": SINK, "restored": True, "mutedBefore": False, "remuted": 1},
            )
            self.assertIn("previous state (unmuted) restored", speaker.summary())
        self.assertEqual(
            fake.commands[0][:6],
            ["runuser", "-u", "korri", "--", "env", "XDG_RUNTIME_DIR=/run/user/1000"],
        )

    def test_keeps_a_sink_that_was_already_muted_muted(self):
        fake = FakeWpctl(muted=True)
        with tempfile.TemporaryDirectory() as tmp:
            speaker = Speaker(SINK, "korri", Path("/run/user/1000"), Path(tmp), fake)
            speaker.mute()
            speaker.mute()  # a second run keeps the first recorded state
            speaker.restore()
            self.assertTrue(fake.muted)
            self.assertTrue(speaker.before)

    def test_untouched_sink_is_not_restored(self):
        fake = FakeWpctl(muted=False)
        with tempfile.TemporaryDirectory() as tmp:
            speaker = Speaker(SINK, "korri", Path("/run/user/1000"), Path(tmp), fake)
            speaker.hold()
            speaker.restore()
        self.assertEqual(fake.commands, [])
        self.assertEqual(speaker.summary(), "not changed")

    def test_missing_sink_and_unsafe_names_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "not found"):
                Speaker(
                    "alsa_output.absent",
                    "korri",
                    Path("/run"),
                    Path(tmp),
                    FakeWpctl(False),
                ).mute()
            with self.assertRaisesRegex(ValueError, "node name"):
                Speaker("sink; rm", "korri", Path("/run"), Path(tmp), FakeWpctl(False))


if __name__ == "__main__":
    unittest.main()

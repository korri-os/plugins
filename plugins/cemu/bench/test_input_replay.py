import io
import unittest

from input_replay import replay_script


class ManualClock:
    def __init__(self):
        self.value = 0.0

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class InputReplayTests(unittest.TestCase):
    def test_advance_repeats_until_loading_then_sends_no_more_presses(self):
        clock = ManualClock()
        events: list[tuple[float, int, int, int]] = []
        loaded = False

        def observe():
            nonlocal loaded
            loaded = sum(event[3] == 1 for event in events) >= 3

        replay_script(
            [(0, 1, 0x131, 1), (0.15, 1, 0x131, 0), (2, 0, 0, 0)],
            events.append,
            observe,
            lambda: loaded,
            lambda: None,
            io.StringIO(),
            repeat_until_loading=True,
            now=clock.now,
            sleep=clock.sleep,
        )
        self.assertEqual(sum(event[3] == 1 for event in events), 3)
        self.assertTrue(loaded)
        self.assertLess(clock.now(), 7)

    def test_no_loading_is_bounded_and_controls_were_released(self):
        clock = ManualClock()
        events: list[tuple[float, int, int, int]] = []
        with self.assertRaisesRegex(RuntimeError, "60-second bounded advance"):
            replay_script(
                [(0, 1, 0x131, 1), (0.15, 1, 0x131, 0), (2, 0, 0, 0)],
                events.append,
                lambda: None,
                lambda: False,
                lambda: None,
                io.StringIO(),
                repeat_until_loading=True,
                now=clock.now,
                sleep=clock.sleep,
            )
        self.assertLessEqual(clock.now(), 60.1)
        self.assertEqual([event for event in events if event[1] == 1][-1][3], 0)

    def test_slow_capture_does_not_collapse_a_press_release_hold(self):
        clock = ManualClock()
        sent = []
        replay_script(
            [(2, 1, 0x131, 1), (2.15, 1, 0x131, 0)],
            lambda event: sent.append((clock.now(), event)),
            lambda: clock.sleep(3),
            lambda: False,
            lambda: None,
            io.StringIO(),
            now=clock.now,
            sleep=clock.sleep,
        )
        self.assertGreaterEqual(sent[1][0] - sent[0][0], 0.149)


if __name__ == "__main__":
    unittest.main()

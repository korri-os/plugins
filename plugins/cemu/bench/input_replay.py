"""Replay native input. Optional bounded advance stops on observed loading, not time."""

import json
import time
from collections.abc import Callable
from typing import TextIO

from gamepad import Event


def replay_script(
    script: list[Event],
    send: Callable[[Event], None],
    observe: Callable[[], None],
    loading: Callable[[], bool],
    check_timeout: Callable[[], None],
    output: TextIO,
    *,
    repeat_until_loading: bool = False,
    poll_seconds: float = 1,
    now: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    if not script:
        if repeat_until_loading:
            raise ValueError("Repeating advance requires an input script")
        return
    events = list(script)
    if repeat_until_loading and events[-1][0] < 2:
        events.append((2, 0, 0, 0))
    started = now()
    next_capture = started
    cycle_start = started
    while True:
        late = 0.0
        for event in events:
            due = cycle_start + event[0] + late
            while now() < due:
                check_timeout()
                if repeat_until_loading and not loading() and now() >= started + 60:
                    raise RuntimeError(
                        "Loading not observed within 60-second bounded advance"
                    )
                if now() >= next_capture and due - now() > 0.5:
                    observe()
                    next_capture = now() + poll_seconds
                else:
                    sleep(min(0.05, max(0, due - now())))
            # Slow captures must not compress a subsequent press/release to zero hold time.
            late += max(0, now() - due)
            if not (repeat_until_loading and loading() and event[3] != 0):
                send(event)
                output.write(
                    json.dumps(
                        {
                            "scheduled_s": due - started,
                            "sent_s": now() - started,
                            "type": event[1],
                            "code": event[2],
                            "value": event[3],
                        }
                    )
                    + "\n"
                )
                output.flush()
        if not repeat_until_loading or loading():
            return
        if now() >= started + 60:
            raise RuntimeError("Loading not observed within 60-second bounded advance")
        cycle_start = now()

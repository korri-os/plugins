"""Replay native evemu events through a distinct bench-only Linux uinput pad.

No seat impersonation, device grab, InputPlumber reconfiguration or policy write.
Normal Korri seat admission still decides whether the game receives the events.
"""

import math
import time
from collections.abc import Callable
from pathlib import Path

from evdev import AbsInfo, UInput, ecodes

Event = tuple[float, int, int, int]
BUTTONS = set(range(0x130, 0x13F)) - {0x13C}  # never Guide
AXES = {
    0: (-32768, 32767),
    1: (-32768, 32767),
    2: (0, 255),
    3: (-32768, 32767),
    4: (-32768, 32767),
    5: (0, 255),
    16: (-1, 1),
    17: (-1, 1),
}


def read_events(path: Path) -> list[Event]:
    events: list[Event] = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 5 or fields[0] != "E:":
            raise ValueError("Expected native evemu E: timestamp type code value")
        at, kind, code, value = (
            float(fields[1]),
            int(fields[2], 16),
            int(fields[3], 16),
            int(fields[4]),
        )
        if (
            not math.isfinite(at)
            or not 0 <= at <= 3600
            or (events and at < events[-1][0])
        ):
            raise ValueError("Invalid evemu timestamp")
        if not (
            (kind == 0 and code == value == 0)
            or (kind == 1 and code in BUTTONS and value in (0, 1))
            or (kind == 3 and code in AXES and AXES[code][0] <= value <= AXES[code][1])
        ):
            raise ValueError("Only gamepad evemu events are allowed")
        events.append((at, kind, code, value))
    if not events:
        raise ValueError("Empty input script")
    return events


def replay(events: list[Event], session_alive: Callable[[], bool]) -> None:
    capabilities: dict[int, list[int] | list[tuple[int, AbsInfo]]] = {
        ecodes.EV_KEY: sorted(BUTTONS),
        ecodes.EV_ABS: [
            (code, AbsInfo(0, low, high, 0, 0, 0)) for code, (low, high) in AXES.items()
        ],
    }
    # The native Xbox profile admits this synthetic Bluetooth identity. This
    # test route is not a product input route or proof of the game's player slot.
    with UInput(
        # evdev 1.9.2 types omit its documented (axis, AbsInfo) event form.
        capabilities,  # type: ignore[arg-type]
        name="Eden benchmark gamepad",
        phys="eden-bench/input0",
        bustype=5,
        vendor=0x045E,
        product=0x02D1,
        version=0x0114,
    ) as pad:
        time.sleep(2)
        start = time.monotonic()
        try:
            for at, kind, code, value in events:
                time.sleep(max(0, start + at - time.monotonic()))
                if not session_alive():
                    raise RuntimeError("Exact session exited during input replay")
                pad.write(kind, code, value)
                if kind:
                    pad.syn()
        finally:
            for code in BUTTONS:
                pad.write(ecodes.EV_KEY, code, 0)
            for code in AXES:
                pad.write(ecodes.EV_ABS, code, 0)
            pad.syn()

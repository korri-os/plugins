"""Game X11 Present completions, not Gamescope's output refresh counter."""

import math
import statistics
from collections.abc import Sequence


def fps_bins(
    events: Sequence[tuple[float, int, int]], window: int, start: float, seconds: int
) -> list[int]:
    bins = [0] * seconds
    for timestamp, event_window, mode in events:
        # X Present mode 2 = Skip. Copy, Flip and SuboptimalCopy were presented.
        if (
            event_window == window
            and mode != 2
            and start <= timestamp < start + seconds
        ):
            bins[int(timestamp - start)] += 1
    return bins


def summarize(values: Sequence[float]) -> dict[str, float]:
    if not values:
        raise ValueError("No measurement samples")
    ordered = sorted(values)
    return {
        "samples": len(values),
        "median": statistics.median(ordered),
        "p10": ordered[math.ceil(len(ordered) * 0.10) - 1],
        "p1": ordered[math.ceil(len(ordered) * 0.01) - 1],
        "min": ordered[0],
    }

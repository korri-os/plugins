"""Game-window X11 Present completions, not Gamescope's refresh rate."""

import csv
import io
import math
import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Presentation:
    event: str
    at: float  # X server UST microseconds converted to monotonic seconds
    window: int
    mode: int


def read_presentations(path: Path) -> list[Presentation]:
    data = path.read_bytes()
    # Read one snapshot; do not interpret the writer's incomplete final line.
    if not data.endswith(b"\n"):
        data = data.rsplit(b"\n", 1)[0] + b"\n" if b"\n" in data else b""
    rows: list[Presentation] = []
    for row in csv.DictReader(io.StringIO(data.decode())):
        try:
            item = Presentation(
                row["event"],
                int(row["ust_us"]) / 1_000_000,
                int(row["window"]),
                int(row["mode"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid X Present observer row") from exc
        if (
            item.event not in ("frame", "destroy")
            or item.at <= 0
            or item.window <= 0
            or item.mode not in range(4)
        ):
            raise ValueError("Invalid X Present observer values")
        rows.append(item)
    return rows


def fps_window(
    events: Sequence[Presentation], start: float, seconds: int
) -> tuple[int, list[int]]:
    if seconds <= 0 or not math.isfinite(start):
        raise ValueError("Invalid measurement window")
    warmup = Counter(
        e.window
        for e in events
        if e.event == "frame" and e.mode != 2 and start - 10 <= e.at < start
    )
    if not warmup:
        raise ValueError(
            "No renderer-window Present completions near the end of warmup"
        )
    selected = warmup.most_common(1)[0][0]
    bins: list[Counter[int]] = [Counter() for _ in range(seconds)]
    for event in events:
        if not start <= event.at < start + seconds:
            continue
        if event.event == "destroy" and event.window == selected:
            raise ValueError(
                "Selected renderer window was destroyed during measurement"
            )
        if event.event == "frame" and event.mode != 2:
            bins[int(event.at - start)][event.window] += 1
    if any(bucket and bucket.most_common(1)[0][0] != selected for bucket in bins):
        raise ValueError(
            "Renderer window replaced or presenting window became ambiguous"
        )
    values = [bucket[selected] for bucket in bins]
    if not sum(values):
        raise ValueError("No game frames in measurement; compositor refresh is not FPS")
    return selected, values


def summarize(values: Sequence[float]) -> dict[str, float]:
    if not values or any(not math.isfinite(x) or x < 0 for x in values):
        raise ValueError("Expected finite nonnegative FPS samples")
    ordered = sorted(values)
    return {
        "median": statistics.median(ordered),
        "p10": ordered[math.ceil(len(ordered) * 0.10) - 1],
        "p1": ordered[math.ceil(len(ordered) * 0.01) - 1],
    }

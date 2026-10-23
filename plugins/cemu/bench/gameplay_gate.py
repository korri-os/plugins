"""Fail-closed frame gates. Only numeric fingerprints leave the capture boundary."""

import hashlib
import io
import json
import math
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, cast

from PIL import Image

Label = Literal["title", "loading", "gameplay", "unknown"]
Statistics = dict[str, object]
DESCRIPTOR_SIZE = (31, 27)


class NotMeasured(RuntimeError):
    pass


def object_record(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("Expected an object")
    return cast(dict[str, object], value)


def numbers(value: object) -> list[float]:
    if (
        not isinstance(value, list)
        or not value
        or not all(
            isinstance(item, (int, float)) and math.isfinite(item) for item in value
        )
    ):
        raise ValueError("Expected finite numeric data")
    return [float(item) for item in value]


def distance(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Descriptor shape mismatch")
    return sum(abs(a - b) for a, b in zip(left, right, strict=True)) / len(left)


class Reference:
    def __init__(self, data: dict[str, object]):
        self.data = data
        self.game = str(data["game"])
        resolution = numbers(data["resolution"])
        if len(resolution) != 2 or any(
            not value.is_integer() or not 1 <= value <= 8192 for value in resolution
        ):
            raise ValueError("Invalid reference resolution")
        self.width, self.height = (int(value) for value in resolution)
        mask = numbers(data["titleMask"])
        if not 32 <= len(mask) <= 4096 or any(not value.is_integer() for value in mask):
            raise ValueError("Invalid title foreground mask")
        self.mask = [int(value) for value in mask]
        if any(index < 0 or index >= self.width * self.height for index in self.mask):
            raise ValueError("Title mask outside capture")
        self.examples: dict[str, list[list[float]]] = {}
        raw = object_record(data["examples"])
        for label in ("title", "loading", "gameplay"):
            examples = raw[label]
            if not isinstance(examples, list) or not examples:
                raise ValueError("Each gate needs reference examples")
            self.examples[label] = [numbers(example) for example in examples]
            if any(len(example) != 31 * 27 * 3 for example in self.examples[label]):
                raise ValueError("Expected 31 x 27 RGB reference")
        self.thresholds = object_record(data["thresholds"])
        for label in ("loading", "gameplay"):
            threshold = self.thresholds[label]
            if not isinstance(threshold, (int, float)) or not 0 < threshold < 255:
                raise ValueError("Invalid calibrated threshold")

    @classmethod
    def load(cls, path: Path) -> "Reference":
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("Reference exceeds 1 MiB")
        try:
            return cls(object_record(json.loads(path.read_text())))
        except KeyError as exc:
            raise ValueError("Incomplete numeric reference") from exc

    def statistics(self, data: bytes) -> Statistics:
        with Image.open(io.BytesIO(data)) as source:
            image = source.convert("RGB")
        if image.size != (self.width, self.height):
            raise NotMeasured("Capture resolution does not match per-game reference")
        pixels = image.load()
        assert pixels is not None
        coverage = sum(
            min(cast(tuple[int, int, int], pixels[i % self.width, i // self.width]))
            > 200
            for i in self.mask
        ) / len(self.mask)
        small = image.resize(DESCRIPTOR_SIZE, Image.Resampling.BICUBIC)
        return {
            "width": image.width,
            "height": image.height,
            "sha256": hashlib.sha256(data).hexdigest(),
            "rgb": list(small.tobytes()),
            "titleCoverage": coverage,
        }

    def classify(self, statistics: Statistics) -> Label:
        if (statistics["width"], statistics["height"]) != (self.width, self.height):
            raise NotMeasured("Capture resolution does not match per-game reference")
        rgb = numbers(statistics["rgb"])
        coverage = statistics["titleCoverage"]
        if not isinstance(coverage, (int, float)) or not 0 <= coverage <= 1:
            raise ValueError("Invalid foreground coverage")
        distances = {
            label: min(distance(rgb, example) for example in examples)
            for label, examples in self.examples.items()
        }
        nearest = min(distances, key=lambda label: distances[label])
        if coverage >= 0.95 and nearest == "title":
            return "title"
        if nearest in ("gameplay", "loading"):
            threshold = self.thresholds[nearest]
            assert isinstance(threshold, (int, float))
            if distances[nearest] <= threshold:
                return cast(Label, nearest)
        return "unknown"


class GameplayGate:
    def __init__(self, reference: Reference, started: float, timeout: float):
        self.reference = reference
        self.started = started
        self.timeout = timeout
        self.deadline = started + timeout
        self.phase = "title"
        self.matches = 0
        self.timings: dict[str, float | None] = {
            "titleAt": None,
            "loadingAt": None,
            "gameplayAt": None,
            "endGameplayAt": None,
        }

    @property
    def title_ready(self) -> bool:
        return self.phase == "input"

    @property
    def ready(self) -> bool:
        return self.phase == "verified"

    def begin_input(self, now: float) -> None:
        if not self.title_ready:
            raise NotMeasured("Input refused before title gate")
        self.phase = "loading"
        self.matches = 0
        self.deadline = now + self.timeout

    def check_timeout(self, now: float) -> None:
        if self.phase not in ("input", "verified") and now >= self.deadline:
            raise NotMeasured(f"{self.phase} gate timed out")

    def observe(self, statistics: Statistics, now: float) -> Label:
        self.check_timeout(now)
        label = self.reference.classify(statistics)
        if self.phase == "title":
            self.matches = self.matches + 1 if label == "title" else 0
            if self.matches >= 2:
                self.timings["titleAt"] = now - self.started
                self.phase = "input"
        elif self.phase == "loading" and label == "loading":
            self.timings["loadingAt"] = now - self.started
            self.phase = "gameplay"
            self.deadline = now + self.timeout
            self.matches = 0
        elif self.phase == "gameplay":
            self.matches = self.matches + 1 if label == "gameplay" else 0
            if self.matches >= 2:
                self.timings["gameplayAt"] = now - self.started
                self.phase = "verified"
        return label

    def finish(self, statistics: Statistics, now: float) -> None:
        if not self.ready or self.reference.classify(statistics) != "gameplay":
            raise NotMeasured("Gameplay gate failed at end of sample window")
        self.timings["endGameplayAt"] = now - self.started


class FrameCapture:
    def __init__(self, reference: Reference, user: str, runtime: Path, display: str):
        self.reference = reference
        self.user = user
        self.runtime = runtime
        self.display = display

    def capture(self) -> Statistics:
        data = subprocess.check_output(
            [
                "runuser",
                "-u",
                self.user,
                "--",
                "env",
                f"XDG_RUNTIME_DIR={self.runtime}",
                f"WAYLAND_DISPLAY={self.display}",
                "grim",
                "-",
            ],
            timeout=10,
        )
        return self.reference.statistics(data)

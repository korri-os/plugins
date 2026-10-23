"""Verify public evidence without exposing private paths or displaying images."""

import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

from metrics import fps_bins, summarize

PRIVATE_PATTERNS = (
    re.compile(r"/users/[a-f0-9]{64}\b"),
    re.compile(r'"--autolaunch",\s*"[a-f0-9]{32}"'),
    re.compile(r"\b10\.42\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"/srv/" r"lakes(?:/|\b)"),
    re.compile(r"/var/lib/korri-private-cache\.[A-Za-z0-9]+"),
    re.compile(r"/home/" r"(?!korri(?:/|\b))[^/\s<>]+"),
)


def is_private(text: str) -> bool:
    return any(pattern.search(text) for pattern in PRIVATE_PATTERNS)


def check_privacy(root: Path) -> int:
    count = 0
    for area in (root / "samples", root / "devices"):
        for path in sorted(area.rglob("*")):
            if not path.is_file():
                continue
            data = path.read_bytes()
            if path.suffix == ".gz":
                data = gzip.decompress(data)
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue  # PNGs are not displayed or treated as text.
            if is_private(text):
                raise ValueError(
                    f"Private identifier or path in {path.relative_to(root)}"
                )
            count += 1
    return count


def check_fps(root: Path) -> int:
    count = 0
    for path in sorted((root / "samples").rglob("fps.json")):
        recorded = json.loads(path.read_text())
        raw = gzip.decompress((path.parent / "present.csv.gz").read_bytes()).decode()
        events = [
            (int(row["ust_us"]) / 1e6, int(row["window"]), int(row["mode"]))
            for row in csv.DictReader(io.StringIO(raw))
        ]
        bins = fps_bins(
            events,
            recorded["window"],
            recorded["measurementStart"],
            recorded["seconds"],
        )
        if bins != recorded["fps"] or any(
            recorded[key] != value for key, value in summarize(bins).items()
        ):
            raise ValueError(f"FPS does not reproduce: {path.relative_to(root)}")
        count += 1
    return count


def check_checksums(root: Path) -> int:
    count = 0
    for manifest in sorted((root / "samples").rglob("SHA256SUMS")):
        for line in manifest.read_text().splitlines():
            expected, name = line.split("  ", 1)
            path = manifest.parent / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Stale checksum: {path.relative_to(root)}")
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "checks",
        nargs="*",
        choices=["privacy", "fps", "checksums"],
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    checks = {"privacy": check_privacy, "fps": check_fps, "checksums": check_checksums}
    for name in args.checks or checks:
        print(f"{name}: {checks[name](root)} verified")

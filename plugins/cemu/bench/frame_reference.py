"""Capture/calibrate numeric references without displaying or committing images."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image

from gameplay_gate import DESCRIPTOR_SIZE, Reference, distance


def calibrate(game: str, paths: dict[str, list[Path]], output: Path) -> None:
    images = {
        label: [Image.open(path).convert("RGB") for path in files]
        for label, files in paths.items()
    }
    sizes = {image.size for group in images.values() for image in group}
    if len(sizes) != 1 or any(
        not images.get(label) for label in ("title", "loading", "gameplay")
    ):
        raise ValueError("All three states need captures at exactly one resolution")
    width, height = sizes.pop()
    positives = [image.tobytes() for image in images["title"]]
    negatives = [image.tobytes() for image in images["gameplay"]]
    mask = [
        i
        for i in range(width * height)
        if all(min(data[i * 3 : i * 3 + 3]) > 200 for data in positives)
        and all(min(data[i * 3 : i * 3 + 3]) <= 200 for data in negatives)
    ]
    if len(mask) < 32:
        raise ValueError(
            "Insufficient stable title foreground; capture more distinct title backgrounds"
        )
    step = max(1, len(mask) // 1024)
    mask = mask[::step][:1024]
    examples = {
        label: [
            list(image.resize(DESCRIPTOR_SIZE, Image.Resampling.BICUBIC).tobytes())
            for image in group
        ]
        for label, group in images.items()
    }
    thresholds = {}
    calibration = {}
    for label in ("loading", "gameplay"):
        group = examples[label]
        intra = max(distance(a, b) for a in group for b in group)
        negative = min(
            distance(a, b)
            for a in group
            for other, others in examples.items()
            if other != label
            for b in others
        )
        if negative <= intra:
            raise ValueError(
                f"{label}: positive/negative descriptors overlap; narrow this scene/reference"
            )
        thresholds[label] = (negative + intra) / 2
        calibration[label] = {
            "maxPositiveDistance": intra,
            "minNegativeDistance": negative,
        }
    data: dict[str, object] = {
        "game": game,
        "resolution": [width, height],
        "descriptor": "31x27 RGB bicubic, MAE 0..255",
        "titleMask": mask,
        "examples": examples,
        "thresholds": thresholds,
        "calibration": calibration,
        "captureSha256": {
            label: [hashlib.sha256(path.read_bytes()).hexdigest() for path in group]
            for label, group in paths.items()
        },
    }
    reference = Reference(data)
    checks = []
    for label, files in paths.items():
        for path in files:
            stats = reference.statistics(path.read_bytes())
            if reference.classify(stats) != label:
                raise ValueError(
                    f"Calibration does not separate {label}; capture different foreground/scene"
                )
            checks.append({"label": label, "statistics": stats})
    output.write_text(json.dumps(data, separators=(",", ":")) + "\n")
    output.with_name(output.stem + "-checks.json").write_text(
        json.dumps(checks, separators=(",", ":")) + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("--user", default="korri")
    capture.add_argument("--runtime-dir", type=Path, default=Path("/run/user/1000"))
    capture.add_argument("--wayland-display", default="korri-wayland")
    capture.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Private PNG; never display or commit",
    )
    calibration = sub.add_parser("calibrate")
    calibration.add_argument("--game", required=True)
    for label in ("title", "loading", "gameplay"):
        calibration.add_argument("--" + label, type=Path, nargs="+", required=True)
    calibration.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "capture":
        with args.output.open("xb") as output:
            args.output.chmod(0o600)
            subprocess.run(
                [
                    "runuser",
                    "-u",
                    args.user,
                    "--",
                    "env",
                    f"XDG_RUNTIME_DIR={args.runtime_dir}",
                    f"WAYLAND_DISPLAY={args.wayland_display}",
                    "grim",
                    "-",
                ],
                stdout=output,
                check=True,
                timeout=10,
            )
    else:
        calibrate(
            args.game,
            {label: getattr(args, label) for label in ("title", "loading", "gameplay")},
            args.output,
        )


if __name__ == "__main__":
    main()

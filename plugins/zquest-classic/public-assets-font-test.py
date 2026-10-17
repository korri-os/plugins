#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p 'python3.withPackages (ps: [ ps.pillow ])'
"""Exercise real Tiny5 generation, exact pixels, unchanged metrics and input pins."""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exact_fitting_pixels(glyphs, objects):
    checked = 0
    for name, kind, body in objects:
        if kind != b"FONT":
            continue
        _, ranges = struct.unpack_from(">HH", body)
        pos = 4
        for _ in range(ranges):
            _, first, last = struct.unpack_from(">BII", body, pos)
            pos += 9
            for code in range(first, last + 1):
                width, height = struct.unpack_from(">HH", body, pos)
                pos += 4
                stride = (width + 7) // 8
                size = stride * height
                pixels = body[pos : pos + size]
                pos += size
                rendered = (
                    {132: 0x2190, 133: 0x2192}.get(code, code)
                    if name == "FONT_NES"
                    else code
                )
                if 127 <= rendered < 160:
                    rendered = 0xFFFD
                if rendered not in glyphs:
                    continue
                rows = glyphs[rendered]
                columns = [
                    x for row in rows for x, pixel in enumerate(row) if pixel == "#"
                ]
                if not columns:
                    assert not any(pixels)
                    continue
                left, right = min(columns), max(columns)
                if right - left + 1 > width or len(rows) > height:
                    assert any(pixels), (name, code, "lost undersized glyph")
                    continue
                # Independent packer: direct source-to-cell translation, no
                # Pillow, resize or generator bitmap-fitting function.
                expected = bytearray(size)
                xoff = (width - (right - left + 1)) // 2 - left
                yoff = (height - len(rows)) // 2
                for y, row in enumerate(rows):
                    for x, pixel in enumerate(row):
                        if pixel == "#":
                            x += xoff
                            expected[(y + yoff) * stride + x // 8] |= 0x80 >> (x % 8)
                assert pixels == expected, (name, code, "not exact source pixels")
                checked += 1
        assert pos == len(body)
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--allegro-library", type=Path)
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix="zquest-tiny5-font-validation-", dir="/tmp"))
    print(f"Evidence: {work}", flush=True)
    generator = load("public_assets", HERE / "public-assets.py")
    validator = load("public_assets_validate", HERE / "public-assets-validate.py")
    for name in ("first", "second"):
        subprocess.run(
            [
                sys.executable,
                str(HERE / "public-assets.py"),
                "--output",
                str(work / name),
                "--source",
                str(args.source),
                "--font",
                str(args.font),
            ],
            check=True,
            timeout=60,
        )
    first, second = work / "first", work / "second"
    files = [path.relative_to(first) for path in first.rglob("*") if path.is_file()]
    assert set(files) == {
        path.relative_to(second) for path in second.rglob("*") if path.is_file()
    }
    for relative in files:
        assert (first / relative).read_bytes() == (second / relative).read_bytes(), (
            relative
        )
    metrics = json.loads((HERE / "public-assets-metrics.json").read_text())
    validator.structural(first, metrics)
    checked = exact_fitting_pixels(
        generator.tiny5_glyphs(),
        validator.read_objects(first / "modules/classic/classic_fonts.dat", b"longtan"),
    )
    assert checked > 10000
    for filename in ("tiny5.glyphs.txt", "tiny5-OFL.txt"):
        damaged = work / (filename + "-damaged")
        damaged.mkdir()
        for original in ("public-assets.py", "tiny5.glyphs.txt", "tiny5-OFL.txt"):
            shutil.copyfile(HERE / original, damaged / original)
        with (damaged / filename).open("ab") as stream:
            stream.write(b"\n")
        rejected = load(
            filename.replace(".", "_") + "_damaged", damaged / "public-assets.py"
        )
        try:
            rejected.tiny5_glyphs()
        except ValueError as error:
            print(f"Rejected changed {filename}: {error}", flush=True)
        else:
            raise AssertionError(f"Accepted changed {filename}")
    if args.allegro_library:
        validator.upstream(first, args.allegro_library, metrics)
    print(
        f"Verified two byte-identical resource sets, {checked} exact fitting Tiny5 glyphs, "
        "all original metrics, no blank ASCII and both input-rejection gates.",
        flush=True,
    )


if __name__ == "__main__":
    main()

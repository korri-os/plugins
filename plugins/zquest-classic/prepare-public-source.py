#!/usr/bin/env python3
"""Construct the Linux player source/resource tree from reviewed inputs only.

The resulting source is also the engine's corresponding-source release input.
No original quest, sample bank, bitmap-font collection, or soundtrack is copied.
"""

import argparse
from pathlib import Path
import shutil

# Build inputs, not a second manifest for the plugin declaration.
SOURCE_DIRECTORIES = (
    "src",
    "include",
    "modules",
    "cmake",
    "third_party",
    "scripts",
    "packaging",
    "changelogs",
)
SOURCE_FILES = ("CMakeLists.txt", "LICENSE", "AUTHORS")
# Source/config under the engine license; separately licensed ZC Commons assets
# include their original license and credits. ProggyVector embeds its license.
RESOURCE_FILES = (
    "allegro5.cfg",
    "base_config/zc.cfg",
    "themes/mooshmood.ztheme",
    "ProggyVector-Regular.ttf",
    "assets/zc/ZC_Logo.png",
    "assets/zc/ZC_Icon_Medium_Player.png",
    "assets/zc/ZC_Forever_HD.mp3",
    "assets/zc/LICENSE.txt",
    "assets/zc/CREDITS.txt",
)


def prepare(source: Path, assets: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    for directory in SOURCE_DIRECTORIES:
        shutil.copytree(
            source / directory,
            output / directory,
            ignore=shutil.ignore_patterns("MacDMGBackground.png"),
        )
    for filename in SOURCE_FILES:
        shutil.copyfile(source / filename, output / filename)
    # This Linux-only release has no embedded XPM icon. zalleg loads the
    # separately licensed ZC Commons player icon at runtime instead.
    cmake = output / "CMakeLists.txt"
    text = cmake.read_text()
    for variable, filename in (
        ("ZELDAEXTRASOURCES", "zc_icon.c"),
        ("ZQUESTEXTRASOURCES", "zq_icon.c"),
        ("LAUNCHEREXTRASOURCES", "zl_icon.c"),
        ("UPDATEREXTRASOURCES", "zl_icon.c"),
    ):
        old = f"list(APPEND {variable} icons/{filename})"
        if text.count(old) != 1:
            raise ValueError(f"Expected exactly one embedded-icon declaration: {old}")
        text = text.replace(old, "# Linux uses the licensed runtime PNG icon.")
    cmake.write_text(text)
    resources = output / "resources"
    resources.mkdir()
    for relative in RESOURCE_FILES:
        target = resources / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / "resources" / relative, target)
    for path in sorted(assets.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(assets)
        target = resources / relative
        if target.exists():
            raise ValueError(
                f"Generated asset would replace a retained input: {relative}"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    # These raw resource names are deliberately absent from public source too.
    forbidden = ("*.nsf", "*.qst", "*.sub")
    for pattern in forbidden:
        if list(resources.rglob(pattern)):
            raise ValueError(f"Unexpected resource matching {pattern}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("assets", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    prepare(arguments.source, arguments.assets, arguments.output)


if __name__ == "__main__":
    main()

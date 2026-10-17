#!/usr/bin/env python3
"""Audit every file in an extracted public corresponding-source bundle.

This is a source-media gate, not a runtime-closure or general license scanner.
Unknown binary/media files fail closed, including files outside resources/.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

# These pinned files are the retained licensed inputs, not demo/test assets.
# ZC Commons credits/license, Tiny5 source/OFL and the TTF's extracted license
# remain mandatory.
RETAINED = {
    "engine/resources/ProggyVector-Regular.ttf": "dae80a9b9bb23a37f60465dd93de9365a8ddd43300adc304d96f91ce54c28dd5",
    "engine/resources/assets/zc/ZC_Forever_HD.mp3": "2fca988abe5cb97def6acc241e755a7b42414b8958e2ec0a2b66b1bbc2f0bda9",
    "engine/resources/assets/zc/ZC_Icon_Medium_Player.png": "99ed33d83449ca243c5266ee2b7a83f8d984d36376a8692ba4db0465aeb0c774",
    "engine/resources/assets/zc/ZC_Logo.png": "8ececb2b6b9768d2856a7579a2622b274364f06d71550530ac79f67572d772b7",
    "engine/resources/assets/zc/LICENSE.txt": "b69b172adb87f9674cfb541ae50f71dc0135fcf855f4349012d499c485350c1b",
    "engine/resources/assets/zc/CREDITS.txt": "42660e42827262432cba8f91d68caf3bf3c91c2fbff81330ce393626b5ca736e",
    # Exact text inputs vendored from Korri Pico's Tiny5 producer. These are
    # not new binary/media exceptions. Both standalone and original recipes
    # must carry the glyph source and its complete OFL notice.
    "tiny5.glyphs.txt": "38d7d58a644a3cc03d49e1c59ffab3be8eb0ea91c7e4a256983d8b487f849e6d",
    "recipe/tiny5.glyphs.txt": "38d7d58a644a3cc03d49e1c59ffab3be8eb0ea91c7e4a256983d8b487f849e6d",
    "tiny5-OFL.txt": "6fe7d64407c69d187748206265977654747d3e2fe9e38e45a62cd03ec4770df6",
    "recipe/tiny5-OFL.txt": "6fe7d64407c69d187748206265977654747d3e2fe9e38e45a62cd03ec4770df6",
}
# Allegro's library configuration data, icon and reference manual diagrams.
# Its giftware/zlib notices are retained. These are not the demo soundtrack.
OPTIONAL_RETAINED = {
    "engine/third_party/allegro_legacy/keyboard.dat": "ffc88999ad1cb3e752c0023b4109a761ca915cd5cae6098bea63d53d85a6eaa8",
    "engine/third_party/allegro_legacy/language.dat": "96256542daf5fa78b356293e6486a001c227f63560b0877dad1b176bbbb512a9",
    "engine/third_party/allegro_legacy/misc/icon.png": "b08a8a828875d9c32199c253455daf34cc41932a8076f3b1249292e9d33b8e2a",
    "engine/third_party/allegro_legacy/misc/icon.xpm": "4feb83f81775eec4446c4f005e6f8ffbe05b214b8b20166eabd5120f712db8c7",
    "dependencies/allegro5/misc/icon.png": "b08a8a828875d9c32199c253455daf34cc41932a8076f3b1249292e9d33b8e2a",
    "dependencies/allegro5/misc/icon.xpm": "4feb83f81775eec4446c4f005e6f8ffbe05b214b8b20166eabd5120f712db8c7",
    "dependencies/allegro5/docs/src/refman/images/LINE_CAP.png": "ec4d7012986d5a5b65c8024590fcaaa264ba70d190ef93370a3482749299c7e2",
    "dependencies/allegro5/docs/src/refman/images/LINE_CAP.svg": "c0c0857eaab1d8cab9de94cf4bb96e2ab5535ac31b50dcbb2d3806eb5d5160e9",
    "dependencies/allegro5/docs/src/refman/images/LINE_JOIN.png": "6e40894a8cbbca061fd61bd531d0b6be752b661f579eada33b97defe64893ac1",
    "dependencies/allegro5/docs/src/refman/images/LINE_JOIN.svg": "0ad10057ae56d8a5c0f13736cb41d6efc2bd85df49d02b3e9433f3f3499523a4",
    "dependencies/allegro5/docs/src/refman/images/audio.png": "89a389717b3d300d3fa237b034b6282bfbade0af02d5a541289ede86d386336f",
    "dependencies/allegro5/docs/src/refman/images/audio.svg": "9addbf51eda958e476258c7fdb7d60e4116bf0db20c37ed212b79f2a37bdc02d",
    "dependencies/allegro5/docs/src/refman/images/primitives1.png": "c5d68354a234fbaa2e80e65bb93478570aabcecb21d551cb9e66edd85815ce6d",
    "dependencies/allegro5/docs/src/refman/images/primitives1.svg": "1dfd334cc9c81df73423f4afb31b9ae8029c5b7c7f97e0afcb9d393e6266f598",
    "dependencies/allegro5/docs/src/refman/images/primitives2.png": "30d08f839c4d056173ae0c8328d23b98cef3d67c7e751a1cf2f67b8d585fb632",
    "dependencies/allegro5/docs/src/refman/images/primitives2.svg": "4129e048189164f5dab83c4778b8e6141b16957ad381c6acb7df3abd20e43057",
}
FORBIDDEN_SUFFIXES = set(
    ".nsf .nsfe .qst .sub .vgm .vgz .spc .gbs .gym .hes .kss .sap .rom .nes .sfc .smc".split()
)
MEDIA_SUFFIXES = FORBIDDEN_SUFFIXES | set(
    ".dat .mid .midi .mp3 .ogg .wav .voc .flac .mod .s3m .xm .it .opus .aiff .mp4 .ogv "
    ".png .jpg .jpeg .bmp .pcx .tga .gif .webp .dds .icns .ico .xpm .svg .ttf .otf .fnt "
    ".zip .gz .xz .7z .tar .jar .pdf .blend".split()
)
GENERATED = {
    "ASSET-LICENSES.md",
    "public-assets-font-license.txt",
    "sfx.dat",
    "modules/classic/classic_fonts.dat",
    "assets/cursor.bmp",
    "assets/gui_pal.bmp",
} | {
    f"assets/{name}.mid"
    for name in "dungeon ending gameover level9 overworld title triforce".split()
}


def is_media(path: Path, data: bytes) -> bool:
    return (
        path.suffix.lower() in MEDIA_SUFFIXES
        or b"\0" in data
        or data.startswith(
            (
                b"NESM\x1a",
                b"NSFE",
                b"OggS",
                b"fLaC",
                b"MThd",
                b"PK\x03\x04",
                b"\x1f\x8b",
            )
        )
    )


def audit(root: Path) -> str:
    resources = root / "engine/resources"
    provenance = json.loads((resources / "public-assets-provenance.json").read_text())
    if set(provenance["files"]) != GENERATED:
        raise ValueError("Unexpected generated-resource inventory")
    approved = (
        RETAINED
        | OPTIONAL_RETAINED
        | {
            f"engine/resources/{name}": digest
            for name, digest in provenance["files"].items()
        }
    )
    for name in RETAINED.keys() | {f"engine/resources/{name}" for name in GENERATED}:
        if not (root / name).is_file():
            raise ValueError(f"Missing retained source asset/notice: {name}")
    entries = []
    count = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError(f"Unsupported source entry: {relative}")
        if not path.is_file():
            continue
        count += 1
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise ValueError(f"Forbidden source media: {relative}")
        if relative in approved:
            if digest != approved[relative]:
                raise ValueError(f"Changed retained/generated asset: {relative}")
            entries.append(f"{digest}  {relative}\n")
        elif is_media(path, data):
            raise ValueError(f"Unreviewed source binary/media: {relative}")
    font_notices = (resources / "public-assets-font-license.txt").read_text()
    tiny5_notice = (root / "tiny5-OFL.txt").read_text().strip()
    if tiny5_notice not in font_notices:
        raise ValueError("Generated font notice omits the complete Tiny5 OFL")
    # Check the actual generated bank structure too, not just a self-reported
    # manifest. The validator expects only generated resources in its directory.
    with tempfile.TemporaryDirectory(prefix="zquest-source-assets-") as temporary:
        target = Path(temporary)
        for name in GENERATED | {"public-assets-provenance.json"}:
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(resources / name, destination)
        subprocess.run(
            [
                sys.executable,
                str(root / "public-assets-validate.py"),
                "--resources",
                str(target),
            ],
            check=True,
        )
    return (
        f"Source-media gate: scanned {count} files across the entire source bundle.\n"
        "No unapproved binary/media files or raw game music/quests found.\n"
        "This does not audit encoded C arrays, all source licenses, or runtime closures.\n"
        "Retained/generated asset SHA-256 inventory:\n" + "".join(entries)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = audit(args.source)
    if args.report:
        args.report.write_text(report)
    else:
        print(report, end="")


if __name__ == "__main__":
    main()

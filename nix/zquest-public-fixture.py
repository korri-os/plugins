#!/usr/bin/env python3
"""Generate an original, test-only ZQuest room; never read an existing quest.

Format reference: ZQuestClassic 882c906, src/core/qst_*.cpp and
src/zq/zq_class.cpp. Only the small, documented native section subsets below
are emitted. There is no template, borrowed tile, sound, music, or script.
SPDX-License-Identifier: CC0-1.0
The generator and all generated fixture content are dedicated to CC0-1.0.
"""

import argparse
import hashlib
from pathlib import Path
import struct


def pack(fmt, *values):
    return struct.pack("<" + fmt, *values)


def text(value, size):
    encoded = value.encode("ascii")
    assert len(encoded) < size
    return encoded.ljust(size, b"\0")


def section(tag, version, data):
    # Four-byte tag is big endian/ASCII; all scalar fields are little endian.
    return tag.encode("ascii") + pack("HHI", version, version, len(data)) + data


def header(*, embedded_tiles=True):
    # Header v5 avoids the later mandatory ZInfo section. The deprecated engine
    # version/build remain 2.55/61, as in the pinned native writer.
    data = pack("HB", 0x255, 61) + hashlib.md5(b"").digest()
    data += pack("HB", 0, 0)  # internal version; custom quest, not built-in
    data += text("1", 9) + bytes(9)
    data += text("Geometric runtime room", 65) + text("Korri test fixture", 65)
    data += bytes([0, int(embedded_tiles)]) + bytes(19)  # keyfile; tiles; flags
    data += bytes(2048) + b"\1"  # no template path; one map
    data += pack("8I", 2, 55, 0, 0, 0, 0, 0, 0)
    data += pack("H4B", 2026, 1, 1, 0, 0)
    data += bytes(256 * 3 + 1024 + 1 + 16 + 2 + 1024 + 256 * 2 + 6)
    return text("AG ZC Enhanced Quest File\n   ", 31) + section("HDR ", 5, data)


def tiles():
    # Native SaveScreenSettings uses 8x8 quarter-tile 2, the lower-left
    # quarter of 16x16 tile 0. Give it an original diamond cursor instead of
    # inheriting menu art from another quest. The other quarters stay blank.
    cursor = [
        14 if abs(x - 3) + abs(y - 11) <= 3 else 0 for y in range(16) for x in range(16)
    ]
    images = [cursor]
    # 1 is the player diamond. 2/3 duplicate it for native walk animation.
    # 4/5 are floor/solid wall geometry.
    diamond = [
        (14 if abs(x - 7) + abs(y - 7) <= 5 else 0)
        for y in range(16)
        for x in range(16)
    ]
    images += [diamond] * 3
    # Three small calibration pixels exercise more than eight rendered colors.
    accents = {(3, 3): 4, (4, 3): 5, (5, 3): 7}
    images.append(
        [
            2 if x in (0, 15) or y in (0, 15) else accents.get((x, y), 1)
            for y in range(16)
            for x in range(16)
        ]
    )
    images.append(
        [
            6 if 2 <= x <= 13 and 2 <= y <= 13 else 3
            for y in range(16)
            for x in range(16)
        ]
    )
    data = pack("I", len(images))
    for image in images:
        data += b"\1" + bytes(image[i] | (image[i + 1] << 4) for i in range(0, 256, 2))
    return section("TILE", 3, data)


def palettes():
    # Every native palette slot has the same original RGB ramp. No imported
    # palette names or cycles. v6 uses 8-bit channels, not VGA 6-bit channels.
    colors = [
        (0, 0, 0),
        (32, 48, 72),
        (48, 68, 96),
        (88, 108, 132),
        (112, 132, 156),
        (136, 152, 176),
        (160, 180, 200),
        (192, 208, 224),
        (32, 96, 112),
        (48, 120, 136),
        (64, 144, 160),
        (80, 168, 184),
        (160, 112, 32),
        (200, 152, 48),
        (248, 208, 80),
        (255, 248, 224),
    ]
    palette = bytes(channel for color in colors for channel in color)
    return section("CSET", 6, palette * 8749 + bytes(512 * 17) + pack("H", 0))


def misc_colors():
    # Native MCLR v4 (readmisccolors in qst_colors.cpp), not a config overlay.
    # ResetSaveScreenSettings takes normal/selected-flash text colors from
    # msgtext/caption. Explicit nonzero palette indices prevent black menus
    # when no previously loaded quest has supplied QMisc.colors.
    colors = (
        15,
        14,  # text, caption
        0,
        0,
        7,
        7,  # overw_bg, dngn_bg, dngn_fg, cave_fg
        3,
        14,
        15,
        3,  # bs_dk, bs_goal, compass_lt, compass_dk
        0,
        7,
        14,
        0,
        7,  # subscr_bg, triframe_color, hero_dot, bmap_bg/fg
        0,
        0,
        0,
        0,
        0,  # five decorative tile csets
        0,
        0,
        15,  # HCpieces_cset, subscr_shadow, msgtext
    )
    # Six unused decorative tile references; no borrowed interface artwork.
    return section("MCLR", 4, bytes(colors) + pack("6I", 0, 0, 0, 0, 0, 0))


def combos():
    # Combo v1: tile, flip, four solid quadrants, type, cset, animation,
    # next-combo, next-cset. All other properties take native empty defaults.
    data = pack("H", 3)
    for tile, solid in ((0, 0), (4, 0), (5, 15)):
        data += pack("H6BHB", tile, 0, solid, 0, 0, 0, 0, 0, 0)
    return section("CMBO", 1, data)


def maps(*, win_cell=None):
    # Map v40 stores only flagged fields. One valid screen, then 135 empty
    # screens. Enclosed 16x11 room; its central diamond is the player.
    data = pack("HB", 1, 1) + bytes(6 * 2 + 2 + 64)
    data += pack("BI", 1, 0x10 | 0x4000)  # valid; return point + combo grid
    data += bytes([120] * 4 + [80] * 4 + [120, 80])
    grid = [
        2 if x in (0, 15) or y in (0, 10) else 1 for y in range(11) for x in range(16)
    ]
    flags = bytearray(176)
    if win_cell is not None:
        x, y = win_cell
        if not (1 <= x <= 14 and 1 <= y <= 9):
            raise ValueError("win cell must be on the walkable interior")
        # Native mfZELDA=15: HeroClass::checkspecial2 calls win_game(), which
        # sets qWON and reaches ending(), not ending_scripted().
        flags[y * 16 + x] = 15
    data += pack("176H", *grid) + flags + bytes(176)  # flags and csets
    data += pack("HI", 0, 0)  # no FFCs, empty editor notes
    data += bytes(135)
    return section("MAP ", 40, data)


def dmaps():
    # DMap v1 has no scripts or custom subscreens. Overworld here means only
    # the native coordinate mode, not upstream content.
    data = pack("H", 1) + bytes([0, 0, 0, 0, 0, 0, 0, 1]) + bytes(8)
    data += bytes(21 + 21 + 73)  # name, title, intro
    data += bytes(4 * 3 + 56)  # minimap tiles/csets, enhanced music path
    return section("DMAP", 1, data)


def initial_state():
    # Init v37: no inventory, level flags, scripts, or saved screen data.
    # Unlike the huge older schema this is a small native scalar record.
    data = bytes(32 + 512 // 8 * 4) + pack("HBH", 512, 0, 0)
    data += pack("BHH", 1, 48, 48)  # life and maximum life: three hearts
    data += pack("3BH10B", 4, 0, 4, 48, 16, 32, 1, 1, 0, 0, 0, 0, 0, 0)
    data += pack("8i", 8, 8, 0, 0, 8, 15, 7, 0)
    data += pack("HBH", 65535, 0, 0)  # empty flags, native capacity
    data += bytes([0, 0, 0, 0, 0, 5])
    data += pack(
        "iiH3B3HiH2BiHH2Bi",
        1600,
        5,
        320,
        67,
        2,
        3,
        100,
        100,
        100,
        0,
        150,
        0,
        255,
        0,
        0,
        1,
        0,
        1,
        65000,
    )
    data += pack("HBH", 65535, 0, 0)  # empty generic-script bitstring
    data += pack("HBH", 512, 0, 0) * 5  # empty generic-script maps
    data += pack("IBI", 255 * 136, 0, 0)  # empty screen-data map
    return section("INIT", 37, data)


def hero():
    # Hero v1: six groups of four directions, casting, four held-item poses.
    # All point at our diamond; native movement needs no equipment or script.
    sprite = pack("HBB", 1, 0, 0)
    return section("LINK", 1, sprite * (6 * 4 + 1 + 4))


def generate(*, embedded_tiles=True, win_cell=None):
    # Retain a normally framed TILE section in the negative fixture so the
    # native section dispatcher calls readtiles. That reader must reject the
    # header's missing-tiles flag before attempting any default-tile fallback.
    tile_section = tiles() if embedded_tiles else section("TILE", 3, pack("I", 0))
    return b"".join(
        (
            header(embedded_tiles=embedded_tiles),
            tile_section,
            palettes(),
            misc_colors(),
            combos(),
            maps(win_cell=win_cell),
            dmaps(),
            initial_state(),
            hero(),
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--variant", choices=("room", "missing-tiles", "win"), default="room"
    )
    args = parser.parse_args()
    data = generate(
        embedded_tiles=args.variant != "missing-tiles",
        win_cell=(10, 5) if args.variant == "win" else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"{hashlib.sha256(data).hexdigest()}  {args.output}")


if __name__ == "__main__":
    main()

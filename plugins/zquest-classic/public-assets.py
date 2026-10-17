#!/usr/bin/env python3
"""Generate quest-free ZQuest compatibility resources; no network or device access.

Format references: pinned third_party/allegro_legacy/src/{datafile,file}.c.
Only public-assets-metrics.json (numeric advances), the two slot headers, zdefs.h,
the pinned licensed Tiny5 glyph table, and licensed ProggyVector TTF are read.
No upstream bitmap/sample/datafile is read. Outputs use uncompressed Allegro packfiles with uncompressed object chunks.
"""

import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import struct

from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version
from PIL import features

REVISION = "882c906b17e35b4105188e6305ae2929aeba30e3"
FONT_SHA256 = "dae80a9b9bb23a37f60465dd93de9365a8ddd43300adc304d96f91ce54c28dd5"
TINY5_SHA256 = "38d7d58a644a3cc03d49e1c59ffab3be8eb0ea91c7e4a256983d8b487f849e6d"
TINY5_LICENSE_SHA256 = (
    "6fe7d64407c69d187748206265977654747d3e2fe9e38e45a62cd03ec4770df6"
)
HERE = Path(__file__).resolve().parent
MIDIS = ("dungeon", "ending", "gameover", "level9", "overworld", "title", "triforce")
RATE = 22050

# One non-melodic cue per compatibility slot: duration ms, start/end Hz,
# noise mix (0..256), description. No notes, transcriptions or upstream samples.
CUES = [
    (110, 900, 250, 180, "air flick"),  # ARROW
    (200, 420, 1300, 30, "rising electrical sweep"),  # BEAM
    (600, 100, 35, 230, "low noise impact"),  # BOMB
    (230, 350, 600, 100, "rotating buzz"),  # BRANG
    (330, 1170, 1170, 0, "single bell-like tone"),  # CHIME
    (90, 1850, 900, 80, "metal click"),  # CHINK
    (480, 310, 870, 0, "completion swell"),  # CLEARED
    (430, 130, 65, 165, "rough low breath"),  # DODONGO
    (180, 180, 75, 200, "wooden latch"),  # DOOR
    (280, 440, 110, 115, "falling impact"),  # EDEAD
    (100, 230, 100, 160, "short hit"),  # EHIT
    (120, 810, 610, 15, "alert pulse"),  # ER
    (420, 120, 80, 240, "filtered fire hiss"),  # FIRE
    (620, 85, 45, 150, "deep rumble"),  # GANON
    (180, 510, 230, 225, "short breath"),  # GASP
    (190, 145, 55, 190, "heavy knock"),  # HAMMER
    (210, 650, 170, 170, "spring snap"),  # HOOKSHOT
    (35, 1050, 1000, 0, "text tick"),  # MSG
    (200, 210, 95, 95, "damage buzz"),  # OUCH
    (130, 760, 1100, 0, "pickup chirp"),  # PICKUP
    (100, 260, 175, 110, "placement tap"),  # PLACE
    (110, 1410, 990, 20, "light plink"),  # PLINK
    (100, 660, 850, 0, "refill pulse"),  # REFILL
    (750, 110, 65, 175, "rough roar"),  # ROAR
    (300, 360, 1020, 0, "continuous upward glide"),  # SCALE
    (900, 65, 65, 250, "water wash"),  # SEA
    (420, 480, 1250, 20, "discovery shimmer"),  # SECRET
    (360, 190, 940, 50, "spiral sweep"),  # SPIRAL
    (220, 180, 90, 160, "step scrape"),  # STAIRS
    (130, 880, 210, 205, "blade swish"),  # SWORD
    (560, 75, 105, 190, "low rasp"),  # VADER
    (210, 570, 1390, 25, "wand sweep"),  # WAND
    (500, 930, 930, 0, "single steady whistle"),  # WHISTLE
    (450, 510, 510, 0, "neutral sustained tone"),  # ZELDA
    (450, 160, 700, 30, "charge rise"),  # ZN1CHARGE
    (550, 250, 1100, 35, "strong charge rise"),  # ZN1CHARGE2
    (520, 160, 85, 235, "fire burst"),  # ZN1DIVINEFIRE
    (380, 750, 90, 40, "fall sweep"),  # ZN1FALL
    (450, 420, 1300, 90, "escape wash"),  # ZN1DIVINEESCAPE
    (290, 250, 85, 220, "fireball rush"),  # ZN1FIREBALL
    (100, 750, 350, 245, "grass rustle"),  # ZN1GRASSCUT
    (210, 130, 60, 145, "post thud"),  # ZN1HAMMERPOST
    (400, 290, 360, 80, "hover buzz"),  # ZN1HOVER
    (210, 1800, 1000, 155, "ice crack"),  # ZN1ICE
    (160, 230, 580, 10, "jump glide"),  # ZN1JUMP
    (180, 850, 330, 0, "lens close"),  # ZN1LENSOFF
    (180, 330, 850, 0, "lens open"),  # ZN1LENSON
    (350, 470, 690, 10, "shield swell"),  # ZN1DIVINEPROTECTION1
    (420, 690, 470, 15, "shield fade"),  # ZN1DIVINEPROTECTION2
    (420, 85, 60, 240, "block scrape"),  # ZN1PUSHBLOCK
    (230, 130, 45, 220, "stone impact"),  # ZN1ROCK
    (400, 750, 160, 150, "descending thrust"),  # ZN1ROCKETDOWN
    (400, 160, 750, 150, "ascending thrust"),  # ZN1ROCKETUP
    (290, 750, 250, 195, "circular swish"),  # ZN1SPINATTACK
    (360, 330, 110, 250, "water splash"),  # ZN1SPLASH
    (420, 390, 920, 35, "summon swell"),  # ZN1SUMMON
    (60, 1200, 900, 100, "hard tap"),  # ZN1TAP
    (75, 740, 510, 130, "soft tap"),  # ZN1TAP2
    (600, 170, 320, 235, "wind rush"),  # ZN1WHIRLWIND
    (160, 510, 290, 60, "cane pulse"),  # ZN2CANE
    (150, 420, 650, 20, "generic cue"),  # Z35
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def slots(source, filename, kind):
    text = (source / "src" / filename).read_text()
    entries = re.findall(r"#define\s+(\w+)\s+(\d+)\s*/\*\s*" + kind + r"\s*\*/", text)
    return {int(number): name for name, number in entries}


def packfile(objects, password=b""):
    """Allegro DAT_MAGIC, count, type + stored/unpacked length + object bytes.

    F_NOPACK_MAGIC is XOR-masked by encrypt_id(..., TRUE); file.c then XORs
    EVERY byte, including that header, with the repeating password. Chunks are
    not encrypted a second time. Positive unpacked lengths mean no compression.
    """
    data = b"ALL." + struct.pack(">I", len(objects))
    for name, kind, body in objects:
        encoded_name = name.encode("ascii")
        data += b"propNAME" + struct.pack(">I", len(encoded_name)) + encoded_name
        data += kind + struct.pack(">II", len(body), len(body)) + body
    magic = 0x736C682E
    if password:
        mask = 42
        for i, value in enumerate(password):
            mask ^= value << ((i & 3) * 8)
        for i in range(4):
            mask ^= password[i % len(password)] << (24 - i * 8)
        magic ^= mask
    data = struct.pack(">I", magic) + data
    if password:
        data = bytes(
            value ^ password[i % len(password)] for i, value in enumerate(data)
        )
    return data


def sample(slot, recipe):
    """Integer-only unsigned 16-bit PCM: triangle oscillator + filtered PRNG noise.

    Fixed seed per slot, 4 ms attack, linear decay to midpoint. The oscillator
    glides continuously: it does not encode a sequence of musical notes.
    """
    ms, first, last, mix, _ = recipe
    length = RATE * ms // 1000
    phase, noise, state = 0, 0, slot * 104729
    pcm = bytearray()
    for i in range(length):
        frequency = first + (last - first) * i // (length - 1)
        phase = (phase + frequency * 65536 // RATE) & 65535
        triangle = 32767 - 2 * abs(phase - 32768)
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        noise = (noise * 2 + ((state >> 16) - 32768)) // 3
        value = (triangle * (256 - mix) + noise * mix) // 256
        envelope = min(65536, i * 65536 // (RATE // 250))
        envelope = envelope * (length - 1 - i) // (length - 1)
        value = value * envelope // 65536 // 3
        pcm += struct.pack("<H", 32768 + value)
    assert len(set(pcm)) > 2
    return struct.pack(">HHI", 16, RATE, length) + pcm


def font_notices(data):
    """Extract full copyright and license name-table entries, without fontTools."""
    notices = []
    for i in range(struct.unpack_from(">H", data, 4)[0]):
        tag, _, offset, _ = struct.unpack_from(">4sIII", data, 12 + 16 * i)
        if tag != b"name":
            continue
        _, count, strings = struct.unpack_from(">HHH", data, offset)
        for j in range(count):
            platform, _, _, nameid, size, pos = struct.unpack_from(
                ">6H", data, offset + 6 + 12 * j
            )
            if nameid not in (0, 13):
                continue
            raw = data[offset + strings + pos : offset + strings + pos + size]
            text = raw.decode("utf-16-be" if platform in (0, 3) else "latin1").strip()
            if text not in notices:
                notices.append(text)
    result = "\n\n".join(notices) + "\n"
    if "BITSTREAM VERA LICENSE" not in result or "MIT LICENSE" not in result:
        raise ValueError("The font input has no complete expected license")
    return result


def tiny5_glyphs():
    """Read Pico's pinned, OFL-licensed seven-row bitmap producer format."""
    data = (HERE / "tiny5.glyphs.txt").read_bytes()
    if digest(data) != TINY5_SHA256:
        raise ValueError("Tiny5 glyph input is not the audited Pico table")
    license_data = (HERE / "tiny5-OFL.txt").read_bytes()
    if digest(license_data) != TINY5_LICENSE_SHA256:
        raise ValueError("Tiny5 license input is not the complete audited OFL")
    text = data.decode("utf-8")
    assert "\nmetrics ascent 6 descent 1\n" in text
    glyphs = {}
    for code, bitmap in re.findall(
        r"(?m)^([0-9A-F]{4,5}) [^\n]+\n((?:[.#]+\n){7})", text
    ):
        code = int(code, 16)
        rows = tuple(bitmap.splitlines())
        assert code not in glyphs and len({len(row) for row in rows}) == 1
        glyphs[code] = rows
    assert all(code in glyphs for code in range(32, 127))
    assert all(any("#" in row for row in glyphs[code]) for code in range(33, 127))
    return glyphs


def bitmap_glyph(rows, width, height):
    # Remove horizontal padding only. The seven-row canvas keeps the common
    # baseline and descenders; common 8px cells contain exact, unscaled pixels.
    ink = [
        (x, y)
        for y, row in enumerate(rows)
        for x, value in enumerate(row)
        if value == "#"
    ]
    cell = Image.new("1", (width, height))
    if ink:
        left = min(x for x, _ in ink)
        ink_width = max(x for x, _ in ink) - left + 1
        fitted_width, fitted_height = min(width, ink_width), min(height, len(rows))
        xoff, yoff = (width - fitted_width) // 2, (height - fitted_height) // 2
        # Truly undersized legacy cells use integer ink projection. OR every
        # source pixel into its destination, so a short punctuation stroke can
        # never disappear. This reduces detail but never changes the metrics.
        for x, y in ink:
            cell.putpixel(
                (
                    xoff + (x - left) * fitted_width // ink_width,
                    yoff + y * fitted_height // len(rows),
                ),
                1,
            )
    return cell.tobytes()


def make_fonts(font_path, metrics, names):
    tiny5 = tiny5_glyphs()

    # Keep the existing licensed raster path only for characters Tiny5 lacks.
    # Its baseline and metric fitting are unchanged.
    @lru_cache(maxsize=None)
    def raster_face(height):
        face = ImageFont.truetype(
            str(font_path), height, layout_engine=ImageFont.Layout.BASIC
        )
        _, top, _, bottom = face.getbbox("Ag", anchor="ls")
        return face, top, bottom

    @lru_cache(maxsize=None)
    def glyph(code, width, height):
        face, top, bottom = raster_face(height)
        image = Image.new("L", (height * 3, bottom - top))
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"  # FreeType's monochrome small-size hinting
        char = chr(code)
        bbox = face.getbbox(char, anchor="ls")
        draw.text((-min(0, bbox[0]), -top), char, font=face, fill=255, anchor="ls")
        # Crop horizontally only. Keep the shared vertical baseline/descenders.
        ink = image.getbbox()
        if ink:
            image = image.crop((ink[0], 0, ink[2], image.height))
            available = max(1, width - (width > 3))
            advance = max(1, face.getlength(char))
            ink_width = max(1, min(available, round(image.width * available / advance)))
            image = image.resize((ink_width, height), Image.Resampling.BOX)
            cell = Image.new("L", (width, height))
            cell.paste(image, ((width - ink_width) // 2, 0))
        else:
            cell = Image.new("L", (width, height))
        # Very short strokes (e.g. '-' in a 4x6 cell) can fall below the normal
        # threshold after downsampling. Retain their strongest ink, not blanks.
        threshold = max(1, min(100, cell.getextrema()[1] * 3 // 4))
        return (
            cell.point(lambda value: 255 if value >= threshold else 0)
            .convert("1")
            .tobytes()
        )

    objects = [("_SIGNATURE", b"DATA", b"Fonts.Dat v2.53 Build 30\r\n\0")]
    for slot, name in sorted(names.items()):
        spec = metrics[str(slot)]
        assert spec["name"] == name
        widths = bytes.fromhex(spec["widths"])
        assert len(widths) == 224 and min(widths) > 0
        height = spec["height"]
        # All Latin byte slots plus the extended Unicode range from FONT_ALLEGRO.
        ranges = [(32, 255)]
        if name == "FONT_ALLEGRO":
            ranges += [(256, 383), (8364, 8364)]
        body = struct.pack(">HH", 0, len(ranges))
        for start, end in ranges:
            body += struct.pack(">BII", 1, start, end)
            for code in range(start, end + 1):
                width = widths[code - 32] if code <= 255 else 8
                # These two non-Unicode byte assignments are explicit in title.cpp.
                rendered = (
                    {132: 0x2190, 133: 0x2192}.get(code, code)
                    if name == "FONT_NES"
                    else code
                )
                # C1 controls have no printable meaning. Use a visible replacement
                # rather than invent proprietary pictograph/script mappings.
                if 127 <= rendered < 160:
                    rendered = 0xFFFD
                pixels = (
                    bitmap_glyph(tiny5[rendered], width, height)
                    if rendered in tiny5
                    else glyph(rendered, width, height)
                )
                body += struct.pack(">HH", width, height) + pixels
        objects.append((name, b"FONT", body))
    # ZQuest's load_datafile_count (src/core/zdefs.cpp) subtracts one callback
    # for the grabber metadata object, not for the DAT_END array terminator.
    # Preserve this final physical slot: signature + 101 fonts + info = 103.
    objects.append(
        ("GrabberInfo", b"info", b"Generated compatibility font metadata.\0")
    )
    return packfile(objects, b"longtan")


def write_bitmaps(output):
    # Original generic palette: grayscale body and two conventional RGB-cube
    # UI rows. BLACK/WHITE are engine ABI indices 253/254, not RGB black/white.
    palette = [(i, i, i) for i in range(256)]
    palette[0] = (255, 0, 255)
    for row, low, high in ((224, 0, 255), (240, 0, 170)):
        for i in range(16):
            lift = 85 if i & 8 else 0
            palette[row + i] = tuple(
                min(255, (high if i & bit else low) + lift) for bit in (4, 2, 1)
            )
    palette[253], palette[254] = (0, 0, 0), (255, 255, 255)
    flat = [channel for rgb in palette for channel in rgb]
    image = Image.new("P", (16, 16))
    image.putpalette(flat)
    image.putdata(list(range(256)))
    image.save(output / "assets/gui_pal.bmp")
    # Player copies the 16x16 cell starting at (1,1). 0 is transparent;
    # dvc(2)=242 is outline, dvc(3)=243 is light fill for recolor_mouse().
    cursor = Image.new("P", (18, 18), 0)
    cursor.putpalette(flat)
    draw = ImageDraw.Draw(cursor)
    draw.polygon(
        [(2, 2), (2, 14), (5, 11), (8, 16), (10, 15), (7, 10), (12, 10)],
        fill=243,
        outline=242,
    )
    cursor.save(output / "assets/cursor.bmp")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="new or empty resource directory"
    )
    parser.add_argument(
        "--source", type=Path, required=True, help="pinned engine source (headers only)"
    )
    parser.add_argument(
        "--font",
        type=Path,
        required=True,
        help="pinned licensed ProggyVector-Regular.ttf",
    )
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error(
            "output directory must be empty; never mix generated and original resources"
        )
    font_data = args.font.read_bytes()
    if digest(font_data) != FONT_SHA256:
        parser.error("font input is not the audited ProggyVector TTF")
    tiny5_glyphs()  # Fail before creating any output if either pinned input changed.
    font_license = (
        "Tiny5 bitmap fonts\n\n"
        + (HERE / "tiny5-OFL.txt").read_text()
        + "\nProggyVector: uncovered Unicode/symbol glyphs and debugger TTF\n\n"
        + font_notices(font_data)
    )
    sound_names = slots(args.source, "sfx.h", "SAMP")
    font_names = slots(args.source, "fontsdat.h", "FONT")
    if list(sorted(sound_names)) != list(range(1, 62)) or list(
        sorted(font_names)
    ) != list(range(1, 102)):
        parser.error("unexpected source slot IDs/counts")
    definitions = (args.source / "src/core/zdefs.h").read_text()
    for name, value in {
        "SFXDAT_VERSION": "0x0211",
        "SFXDAT_BUILD": "15",
        "FONTSDAT_VERSION": "0x0253",
        "FONTSDAT_BUILD": "30",
    }.items():
        if not re.search(r"#define\s+" + name + r"\s+" + value + r"\b", definitions):
            parser.error("source signature changed: " + name)
    metrics_data = (HERE / "public-assets-metrics.json").read_bytes()
    metrics = json.loads(metrics_data)
    assert len(metrics) == 101 and len(CUES) == 61
    (args.output / "assets").mkdir(parents=True)
    (args.output / "modules/classic").mkdir(parents=True)
    sounds = [("_SIGNATURE", b"DATA", b"SFX.Dat v2.11 Build 15\r\n\0")]
    sounds += [
        (sound_names[slot], b"SAMP", sample(slot, CUES[slot - 1]))
        for slot in range(1, 62)
    ]
    (args.output / "sfx.dat").write_bytes(packfile(sounds))
    (args.output / "modules/classic/classic_fonts.dat").write_bytes(
        make_fonts(args.font, metrics, font_names)
    )
    # Preserve the default tune table's beat-based loop points (ending 129..225,
    # overworld 17..EOF). EOF before a positive loop start hangs the legacy
    # sequencer in midi_player -> midi_seek. Keep a 256-beat timeline with an
    # event each beat so seeking/looping always makes progress. At 120 BPM this
    # is 128 seconds. Tempo, all-notes-off and markers emit no audible notes.
    # No global mute or program changes; quest-provided music is untouched.
    track = b"\x00\xff\x51\x03\x07\xa1\x20\x00\xb0\x7b\x00"
    track += b"\x60\xff\x06\x00" * 255  # quarter-note-spaced empty markers
    track += b"\x60\xff\x2f\x00"  # end after beat 256
    midi = (
        b"MThd"
        + struct.pack(">IHHH", 6, 0, 1, 96)
        + b"MTrk"
        + struct.pack(">I", len(track))
        + track
    )
    for name in MIDIS:
        (args.output / "assets" / (name + ".mid")).write_bytes(midi)
    write_bitmaps(args.output)
    (args.output / "ASSET-LICENSES.md").write_bytes(
        (HERE / "ASSET-LICENSES.md").read_bytes()
    )
    (args.output / "public-assets-font-license.txt").write_text(font_license)
    provenance = {
        "format_version": 1,
        "compatibility_source_revision": REVISION,
        "font": {
            "source": "tiny5.glyphs.txt",
            "sha256": TINY5_SHA256,
            "output_family": "Tiny5 compatibility raster",
            "license_source": "tiny5-OFL.txt",
            "license_sha256": TINY5_LICENSE_SHA256,
            "fitting": "Exact pixels with a common seven-row baseline; ink projection only in undersized legacy cells; unchanged advances and heights.",
            "fallback": {
                "source": "ProggyVector-Regular.ttf",
                "sha256": FONT_SHA256,
                "usage": "Only Unicode/symbol glyphs absent from Tiny5; unmodified TTF retained for the debugger.",
            },
        },
        "generator_sha256": digest(Path(__file__).read_bytes()),
        "metrics_sha256": digest(metrics_data),
        "pillow_version": pillow_version,
        "freetype_version": features.version("freetype2"),
        "source_headers": {
            name: digest((args.source / "src" / name).read_bytes())
            for name in ("sfx.h", "fontsdat.h", "core/zdefs.h")
        },
        "sounds": [
            {
                "slot": slot,
                "compatibility_name": sound_names[slot],
                "cue": CUES[slot - 1][4],
            }
            for slot in range(1, 62)
        ],
        "fonts": [
            {
                "slot": slot,
                "compatibility_name": name,
                "height": metrics[str(slot)]["height"],
            }
            for slot, name in sorted(font_names.items())
        ],
        "files": {
            str(path.relative_to(args.output)): digest(path.read_bytes())
            for path in sorted(args.output.rglob("*"))
            if path.is_file()
        },
    }
    (args.output / "public-assets-provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    main()

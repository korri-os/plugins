#!/usr/bin/env python3
"""Check generated resources, optionally with the actual Allegro Legacy reader.

The optional reader uses SYSTEM_NONE: no window, input device or audio driver.
--midi-playback additionally uses the native timer and MIDI_NONE sequencer to
check default loop boundaries, without installing audio or opening a window.
Supply a native library, not the library from a cross-architecture output.
"""

import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
MIDIS = ("dungeon", "ending", "gameover", "level9", "overworld", "title", "triforce")
# Exact 8x8 cells derived from Pico's pinned Tiny5 table, not the generator.
# Capitals, a descender and the dotted i expose stretching/baseline regressions.
TINY5_NES_PIXELS = {
    ord("A"): bytes.fromhex("0018243c24240000"),
    ord("g"): bytes.fromhex("0000182828183000"),
    ord("i"): bytes.fromhex("1000101010100000"),
}


def read_objects(path, password=b""):
    data = path.read_bytes()
    if password:
        data = bytes(b ^ password[i % len(password)] for i, b in enumerate(data))
        # encrypt_id(F_NOPACK_MAGIC, TRUE) for the fixed loader password.
        assert data[:4] == bytes.fromhex("7803087b"), data[:4].hex()
    else:
        assert data[:4] == b"slh."
    assert data[4:8] == b"ALL."
    count = struct.unpack_from(">I", data, 8)[0]
    pos = 12
    objects = []
    for _ in range(count):
        assert data[pos : pos + 8] == b"propNAME"
        size = struct.unpack_from(">I", data, pos + 8)[0]
        name = data[pos + 12 : pos + 12 + size].decode("ascii")
        pos += 12 + size
        kind = data[pos : pos + 4]
        stored, unpacked = struct.unpack_from(">II", data, pos + 4)
        assert stored == unpacked
        pos += 12
        body = data[pos : pos + stored]
        assert len(body) == stored
        objects.append((name, kind, body))
        pos += stored
    assert pos == len(data), "unexpected trailing data"
    return objects


def structural(root, metrics):
    provenance = json.loads((root / "public-assets-provenance.json").read_text())
    assert (
        provenance["metrics_sha256"]
        == hashlib.sha256(
            (HERE / "public-assets-metrics.json").read_bytes()
        ).hexdigest()
    )
    assert provenance["font"]["source"] == "tiny5.glyphs.txt"
    assert (
        provenance["font"]["sha256"]
        == "38d7d58a644a3cc03d49e1c59ffab3be8eb0ea91c7e4a256983d8b487f849e6d"
    )
    assert provenance["font"]["license_source"] == "tiny5-OFL.txt"
    assert (
        provenance["font"]["license_sha256"]
        == "6fe7d64407c69d187748206265977654747d3e2fe9e38e45a62cd03ec4770df6"
    )
    assert provenance["font"]["fallback"] == {
        "source": "ProggyVector-Regular.ttf",
        "sha256": "dae80a9b9bb23a37f60465dd93de9365a8ddd43300adc304d96f91ce54c28dd5",
        "usage": "Only Unicode/symbol glyphs absent from Tiny5; unmodified TTF retained for the debugger.",
    }
    font_license = (root / "public-assets-font-license.txt").read_text()
    tiny5_license = font_license.split("Tiny5 bitmap fonts\n\n", 1)[1].split(
        "\nProggyVector: uncovered Unicode/symbol glyphs and debugger TTF\n\n", 1
    )[0]
    assert (
        hashlib.sha256(tiny5_license.encode()).hexdigest()
        == provenance["font"]["license_sha256"]
    )
    assert "BITSTREAM VERA LICENSE" in font_license and "MIT LICENSE" in font_license
    actual_files = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    assert actual_files == set(provenance["files"]) | {"public-assets-provenance.json"}
    for name, expected in provenance["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
    sounds = read_objects(root / "sfx.dat")
    assert len(sounds) == 62
    assert sounds[0] == ("_SIGNATURE", b"DATA", b"SFX.Dat v2.11 Build 15\r\n\0")
    for slot, (name, kind, body) in enumerate(sounds[1:], 1):
        assert name == provenance["sounds"][slot - 1]["compatibility_name"]
        assert kind == b"SAMP"
        bits, rate, size = struct.unpack_from(">HHI", body)
        assert (bits, rate) == (16, 22050) and len(body) == 8 + 2 * size
        values = struct.unpack("<" + "H" * size, body[8:])
        assert values[0] == values[-1] == 32768
        assert min(values) < 32000 and max(values) > 33536, (
            slot,
            "silent or inaudible sample",
        )
        assert 21000 < min(values) < max(values) < 44500, (slot, "clipping")
    fonts = read_objects(root / "modules/classic/classic_fonts.dat", b"longtan")
    # load_datafile_count in src/core/zdefs.cpp returns callback_count - 1:
    # the final grabber info object is counted by Allegro; DAT_END is not.
    assert len(fonts) == 103 and len(fonts) - 1 == 102
    assert fonts[0] == ("_SIGNATURE", b"DATA", b"Fonts.Dat v2.53 Build 30\r\n\0")
    assert fonts[102] == (
        "GrabberInfo",
        b"info",
        b"Generated compatibility font metadata.\0",
    )
    for slot, (name, kind, body) in enumerate(fonts[1:102], 1):
        assert kind == b"FONT" and name == metrics[str(slot)]["name"]
        widths = bytes.fromhex(metrics[str(slot)]["widths"])
        height, ranges = struct.unpack_from(">HH", body)
        assert height == 0 and ranges == (3 if name == "FONT_ALLEGRO" else 1)
        pos = 4
        for r in range(ranges):
            depth, first, last = struct.unpack_from(">BII", body, pos)
            assert depth == 1
            assert (first, last) == [(32, 255), (256, 383), (8364, 8364)][r]
            pos += 9
            for code in range(first, last + 1):
                width, height = struct.unpack_from(">HH", body, pos)
                assert width == (widths[code - 32] if code <= 255 else 8)
                assert height == metrics[str(slot)]["height"]
                pos += 4
                size = ((width + 7) // 8) * height
                pixels = body[pos : pos + size]
                assert len(pixels) == size
                if 33 <= code <= 126:
                    assert any(pixels), (slot, code, "blank printable ASCII")
                if name == "FONT_NES" and code in TINY5_NES_PIXELS:
                    assert (width, height) == (8, 8)
                    assert pixels == TINY5_NES_PIXELS[code], (
                        slot,
                        code,
                        "not exact Tiny5 pixels",
                    )
                pos += size
        assert pos == len(body)
    for name in MIDIS:
        data = (root / "assets" / (name + ".mid")).read_bytes()
        assert data[:18] == b"MThd\0\0\0\x06\0\0\0\x01\0\x60MTrk"
        track = data[22:]
        assert struct.unpack_from(">I", data, 18)[0] == len(track)
        # An explicit event whitelist proves silence without a synthesizer:
        # tempo + all-notes-off at zero; 255 timed markers; timed EOT. The
        # 256-beat duration exceeds the default ending's loop end (225).
        assert track[:11] == b"\x00\xff\x51\x03\x07\xa1\x20\x00\xb0\x7b\x00"
        assert track[11:-4] == b"\x60\xff\x06\x00" * 255
        assert track[-4:] == b"\x60\xff\x2f\x00"
    for name, size in (("cursor", (18, 18)), ("gui_pal", (16, 16))):
        data = (root / "assets" / (name + ".bmp")).read_bytes()
        assert data[:2] == b"BM"
        assert struct.unpack_from("<ii", data, 18) == size
        assert struct.unpack_from("<H", data, 28)[0] == 8
    print(
        "Verified hashes, Tiny5 license/provenance/exact pixels, 61 audible PCM slots, 101 font slots/metrics, seven silent MIDI files and two indexed BMPs."
    )


def upstream(root, library, metrics, playback=False):
    class Data(C.Structure):
        _fields_ = [
            ("dat", C.c_void_p),
            ("type", C.c_int),
            ("size", C.c_long),
            ("prop", C.c_void_p),
        ]

    class Font(C.Structure):
        _fields_ = [("data", C.c_void_p), ("height", C.c_int), ("vtable", C.c_void_p)]

    class Sample(C.Structure):
        _fields_ = [
            ("bits", C.c_int),
            ("stereo", C.c_int),
            ("freq", C.c_int),
            ("priority", C.c_int),
            ("len", C.c_ulong),
            ("loop_start", C.c_ulong),
            ("loop_end", C.c_ulong),
            ("param", C.c_ulong),
            ("data", C.c_void_p),
        ]

    allegro = C.CDLL(str(library))

    def function(name, result, *arguments):
        fn = getattr(allegro, name)
        fn.restype, fn.argtypes = result, list(arguments)
        return fn

    init = function(
        "_install_allegro_version_check",
        C.c_int,
        C.c_int,
        C.POINTER(C.c_int),
        C.c_void_p,
        C.c_int,
    )
    error = C.c_int()
    # SYSTEM_NONE cannot install timers. SYSTEM_AUTODETECT initializes A5 but
    # opens no window and installs no keyboard, mouse, joystick or audio driver.
    assert init(0 if playback else 0x4E4F4E45, C.byref(error), None, 0x040402) == 0
    if playback:
        assert function("install_timer", C.c_int)() == 0
        assert C.c_void_p.in_dll(allegro, "midi_driver").value == C.addressof(
            C.c_char.in_dll(allegro, "_midi_none")
        )
    password = function("packfile_password", None, C.c_char_p)
    load = function("load_datafile", C.POINTER(Data), C.c_char_p)
    unload = function("unload_datafile", None, C.POINTER(Data))
    text_length = function("text_length", C.c_int, C.c_void_p, C.c_char_p)
    function("set_uformat", None, C.c_int)(
        0x41534338
    )  # U_ASCII, raw byte character IDs
    function("set_color_depth", None, C.c_int)(8)
    password(None)
    sounds = load(str(root / "sfx.dat").encode())
    assert sounds and sounds[62].type == -1
    assert C.string_at(sounds[0].dat).startswith(b"SFX.Dat v2.11 Build 15")
    for slot in range(1, 62):
        assert sounds[slot].type == int.from_bytes(b"SAMP", "big")
        sample = C.cast(sounds[slot].dat, C.POINTER(Sample)).contents
        assert (sample.bits, sample.stereo, sample.freq) == (16, 0, 22050)
        assert sample.len > 0 and sample.loop_end == sample.len and sample.data
        values = C.cast(sample.data, C.POINTER(C.c_ushort))
        assert values[0] == values[sample.len - 1] == 32768
    unload(sounds)
    password(b"longtan")
    callback_type = C.CFUNCTYPE(None, C.POINTER(Data))
    callback_types = []

    @callback_type
    def dat_callback(obj):
        callback_types.append(obj.contents.type)

    load_callback = function(
        "load_datafile_callback", C.POINTER(Data), C.c_char_p, callback_type
    )
    fonts = load_callback(
        str(root / "modules/classic/classic_fonts.dat").encode(), dat_callback
    )
    assert fonts
    # Match ZQuest's actual load_datafile_count wrapper, not just load_datafile.
    engine_count = len(callback_types) - 1
    assert engine_count == 102, ("load_datafile_count", engine_count, "expected", 102)
    assert callback_types == [int.from_bytes(b"DATA", "big")] + [
        int.from_bytes(b"FONT", "big")
    ] * 101 + [int.from_bytes(b"info", "big")]
    assert fonts[102].type == int.from_bytes(b"info", "big") and fonts[103].type == -1
    assert C.string_at(fonts[102].dat) == b"Generated compatibility font metadata."
    assert C.string_at(fonts[0].dat).startswith(b"Fonts.Dat v2.53 Build 30")
    for slot in range(1, 102):
        assert fonts[slot].type == int.from_bytes(b"FONT", "big")
        face = C.cast(fonts[slot].dat, C.POINTER(Font)).contents
        assert face.height == metrics[str(slot)]["height"]
        for code, width in enumerate(bytes.fromhex(metrics[str(slot)]["widths"]), 32):
            assert text_length(fonts[slot].dat, bytes([code])) == width, (slot, code)
    unload(fonts)
    password(None)
    load_midi = function("load_midi", C.c_void_p, C.c_char_p)
    destroy_midi = function("destroy_midi", None, C.c_void_p)
    for name in MIDIS:
        midi = load_midi(str(root / "assets" / (name + ".mid")).encode())
        assert midi, name
        if playback:
            play = function("play_midi", C.c_int, C.c_void_p, C.c_int)
            play_looped = function(
                "play_looped_midi", C.c_int, C.c_void_p, C.c_int, C.c_int
            )
            seek = function("midi_seek", C.c_int, C.c_int)
            position = C.c_long.in_dll(allegro, "midi_pos")
            loop_start, loop_end = {"ending": (129, 225), "overworld": (17, -1)}.get(
                name, (-1, -1)
            )
            loop = name not in ("title", "triforce")
            if loop:
                assert play_looped(midi, loop_start, loop_end) == 0
            else:
                assert play(midi, 0) == 0
            deadline = time.monotonic() + 3
            while position.value < 1 and time.monotonic() < deadline:
                time.sleep(0.01)
            assert position.value >= 1, (name, "timer did not start")
            # Seek near the actual boundary to exercise it without waiting 128
            # seconds per track. Repeat loops to catch a stalled timer after seek.
            for _ in range(2 if loop else 1):
                target = 223 if name == "ending" else 255
                assert seek(target) == 0, (name, "seek failed")
                assert position.value >= target - 1, (name, "short timeline")
                deadline = time.monotonic() + 3
                while position.value >= target - 1 and time.monotonic() < deadline:
                    time.sleep(0.01)
                if loop:
                    assert max(1, loop_start) <= position.value < target - 1, (
                        name,
                        "loop did not progress",
                        position.value,
                    )
                else:
                    assert position.value < 0, (name, "track did not stop")
            assert play(None, 0) == 0
            print(
                f"Verified native silent MIDI timer: {name}, loop={loop}, bounds={loop_start}/{loop_end}",
                flush=True,
            )
        destroy_midi(midi)
    # The app registers an A5 bridge for .bmp; SYSTEM_NONE has no such app
    # registry. Use the bundled reader directly to validate BMP encoding.
    load_bitmap = function("load_bmp", C.c_void_p, C.c_char_p, C.c_void_p)
    destroy_bitmap = function("destroy_bitmap", None, C.c_void_p)
    palette = C.create_string_buffer(1024)
    for name, size in (("cursor", (18, 18)), ("gui_pal", (16, 16))):
        bitmap = load_bitmap(str(root / "assets" / (name + ".bmp")).encode(), palette)
        assert bitmap, name
        dimensions = C.cast(bitmap, C.POINTER(C.c_int))
        assert (dimensions[0], dimensions[1]) == size
        destroy_bitmap(bitmap)
    function("allegro_exit", None)()
    print(
        "Verified actual Allegro loader: font callback count 103 / ZQuest count 102, every sample/font slot, all MIDI and BMP files."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--allegro-library", type=Path)
    parser.add_argument(
        "--midi-playback",
        action="store_true",
        help="test native MIDI_NONE playback and default loop boundaries",
    )
    parser.add_argument(
        "--midi-playback-child", action="store_true", help=argparse.SUPPRESS
    )
    args = parser.parse_args()
    if args.midi_playback and not args.allegro_library:
        parser.error("--midi-playback requires --allegro-library")
    if args.midi_playback and not args.midi_playback_child:
        # A native sequencer regression can hang inside C, so bound the entire
        # child process rather than relying only on Python polling deadlines.
        subprocess.run(
            [sys.executable, __file__, *sys.argv[1:], "--midi-playback-child"],
            check=True,
            timeout=60,
        )
        return
    metrics = json.loads((HERE / "public-assets-metrics.json").read_text())
    structural(args.resources, metrics)
    if args.allegro_library:
        upstream(args.resources, args.allegro_library, metrics, args.midi_playback)


if __name__ == "__main__":
    main()

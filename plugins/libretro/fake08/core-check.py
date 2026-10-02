"""Exercise the real libretro ABI without a display, audio device or network.

Fixtures are authored here, not upstream sample art or starter-pack games.
Test memory-backed .p8 and .p8.png loads, then local extensionless load()
with a second PNG cartridge and retained upper memory (Into Ruins' pattern).
"""

import ctypes as c
from pathlib import Path
import struct
import sys
import tempfile
import zlib


class SystemInfo(c.Structure):
    _fields_ = [("name", c.c_char_p), ("version", c.c_char_p),
                ("extensions", c.c_char_p), ("fullpath", c.c_bool),
                ("block_extract", c.c_bool)]


class GameInfo(c.Structure):
    _fields_ = [("path", c.c_char_p), ("data", c.c_void_p),
                ("size", c.c_size_t), ("meta", c.c_char_p)]


def png_cart(lua):
    payload = bytearray(160 * 205)
    code = lua.encode("ascii")
    payload[0x4300:0x4300 + len(code)] = code
    payload[0x8000] = 42
    rgba = b"".join(bytes(((v >> 4) & 3, (v >> 2) & 3, v & 3,
                           252 | (v >> 6))) for v in payload)
    rows = b"".join(b"\0" + rgba[y * 640:(y + 1) * 640] for y in range(205))

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 160, 205, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def main():
    core = c.CDLL(sys.argv[1])
    core.retro_api_version.restype = c.c_uint
    core.retro_get_system_info.argtypes = [c.POINTER(SystemInfo)]
    core.retro_load_game.argtypes = [c.POINTER(GameInfo)]
    core.retro_load_game.restype = c.c_bool
    assert core.retro_api_version() == 1
    info = SystemInfo()
    core.retro_get_system_info(c.byref(info))
    assert info.name == b"fake-08"
    assert info.extensions == b"p8|png"  # Korri's narrower discovery is separate.
    assert not info.fullpath

    frames = []
    errors = []
    env_t = c.CFUNCTYPE(c.c_bool, c.c_uint, c.c_void_p)
    video_t = c.CFUNCTYPE(None, c.c_void_p, c.c_uint, c.c_uint, c.c_size_t)
    audio_t = c.CFUNCTYPE(None, c.c_int16, c.c_int16)
    batch_t = c.CFUNCTYPE(c.c_size_t, c.c_void_p, c.c_size_t)
    poll_t = c.CFUNCTYPE(None)
    input_t = c.CFUNCTYPE(c.c_int16, c.c_uint, c.c_uint, c.c_uint, c.c_uint)

    with tempfile.TemporaryDirectory() as tmp:
        directory = tmp.encode()

        @env_t
        def environment(command, data):
            if command in (9, 31):  # system/save directories
                c.cast(data, c.POINTER(c.c_char_p))[0] = directory
                return True
            if command == 10:  # RGB565
                return c.cast(data, c.POINTER(c.c_int))[0] == 2
            if command == 3:  # can dupe
                c.cast(data, c.POINTER(c.c_bool))[0] = False
                return True
            return False

        @video_t
        def video(data, width, height, pitch):
            if (width, height, pitch) != (128, 128, 256) or not data:
                errors.append("invalid frame")
                return
            frames.append(c.cast(data, c.POINTER(c.c_uint16))[0])

        callbacks = {
            "environment": environment,
            "video_refresh": video,
            "audio_sample": audio_t(lambda left, right: None),
            "audio_sample_batch": batch_t(lambda data, count: count),
            "input_poll": poll_t(lambda: None),
            "input_state": input_t(lambda port, device, index, button: 0),
        }
        for name, callback in callbacks.items():
            setter = getattr(core, "retro_set_" + name)
            setter.argtypes = [type(callback)]
            setter(callback)
        core.retro_init()

        def load(filename, data, expected):
            frames.clear()
            path = Path(tmp) / filename
            path.write_bytes(data)
            buffer = c.create_string_buffer(data)
            game = GameInfo(str(path).encode(), c.cast(buffer, c.c_void_p), len(data), None)
            assert core.retro_load_game(c.byref(game))
            for _ in range(8):
                core.retro_run()
            assert not errors, errors
            assert frames and frames[-1] == expected, (filename, frames)
            core.retro_unload_game()

        # This core's color 8 -> RGB565 0xf809; color 11 -> 0x0726.
        load("plain.p8", b"pico-8 cartridge // test\nversion 42\n__lua__\n"
             b"function _draw() cls(8) end\n", 0xf809)
        load("single.p8.png", png_cart("function _draw() cls(11) end\n"), 0x0726)
        # No cwd reliance: the initial path establishes the cartridge directory.
        # This uses the exact sibling filenames from Into Ruins, but not its code.
        (Path(tmp) / "intoruins_main.p8.png").write_bytes(png_cart(
            "function _draw() if peek(0x8000)==42 then cls(11) else cls(8) end end\n"))
        load("intoruins.p8.png", png_cart(
            "function _init() poke(0x8000,42) load('intoruins_main','new game') end\n"),
             0x0726)
        core.retro_deinit()
    print("FAKE-08 real ABI: .p8, .p8.png, local PNG multicart and upper memory passed")


if __name__ == "__main__":
    main()

"""Run the actual selected native libretro core, without a window-system double.

Usage: core-probe.py CORE_FILE CONTENT_FILE [FRAME_COUNT]
This checks callbacks and nonuniform content frames, not hardware presentation.
"""

import ctypes as c
import hashlib
import sys
import tempfile
import time


class SystemInfo(c.Structure):
    _fields_ = [
        ("name", c.c_char_p),
        ("version", c.c_char_p),
        ("extensions", c.c_char_p),
        ("need_fullpath", c.c_bool),
        ("block_extract", c.c_bool),
    ]


class GameInfo(c.Structure):
    _fields_ = [
        ("path", c.c_char_p),
        ("data", c.c_void_p),
        ("size", c.c_size_t),
        ("meta", c.c_char_p),
    ]


class Variable(c.Structure):
    _fields_ = [("key", c.c_char_p), ("value", c.c_char_p)]


ENV = c.CFUNCTYPE(c.c_bool, c.c_uint, c.c_void_p)
VIDEO = c.CFUNCTYPE(None, c.c_void_p, c.c_uint, c.c_uint, c.c_size_t)
AUDIO = c.CFUNCTYPE(None, c.c_int16, c.c_int16)
BATCH = c.CFUNCTYPE(c.c_size_t, c.c_void_p, c.c_size_t)
POLL = c.CFUNCTYPE(None)
INPUT = c.CFUNCTYPE(c.c_int16, c.c_uint, c.c_uint, c.c_uint, c.c_uint)


def probe(core_file, content, frames=180):
    from pathlib import Path

    core = c.CDLL(core_file)
    frame = 0
    videos = []
    input_ids = set()
    shutdown = []
    polls = []
    audio = []
    with tempfile.TemporaryDirectory(prefix="libretro-probe-") as temporary:
        directory = temporary.encode()

        @ENV
        def environment(command, data):
            if command in (9, 30, 31):
                c.cast(data, c.POINTER(c.c_char_p))[0] = directory
                return True
            if command == 3:
                c.cast(data, c.POINTER(c.c_bool))[0] = True
                return True
            if command == 17:
                c.cast(data, c.POINTER(c.c_bool))[0] = False
                return True
            if command == 15:
                variable = c.cast(data, c.POINTER(Variable)).contents
                if variable.key == b"wasm4_audio_type":
                    variable.value = b"normal"  # Synchronous audio frontend.
                    return True
                variable.value = None  # Let other options use native defaults.
                return False
            if command == 7:
                shutdown.append(frame)
                return True
            return command in (10, 11, 16, 18, 35, 37, 42)

        @VIDEO
        def video(data, width, height, pitch):
            if data and data != c.c_void_p(-1).value:
                pixels = c.string_at(data, height * pitch)
                videos.append(
                    (
                        width,
                        height,
                        hashlib.sha256(pixels).hexdigest(),
                        len(set(pixels)),
                    )
                )

        @AUDIO
        def sample(left, right):
            audio.append(1)

        @BATCH
        def batch(data, count):
            audio.append(count)
            return count

        @POLL
        def poll():
            polls.append(frame)

        @INPUT
        def state(port, device, index, button):
            if device == 1:
                input_ids.add(button)
                # A dismisses PuzzleScript title; Start is core input, not exit.
                return int(
                    port == 0
                    and (
                        (button == 8 and 20 <= frame < 25)
                        or (button == 3 and 60 <= frame < 65)
                        or (button == 7 and 90 <= frame < 95)
                    )
                )
            return 0

        for name, callback in [
            ("environment", environment),
            ("video_refresh", video),
            ("audio_sample", sample),
            ("audio_sample_batch", batch),
            ("input_poll", poll),
            ("input_state", state),
        ]:
            getattr(core, f"retro_set_{name}")(callback)
        core.retro_get_system_info.argtypes = [c.POINTER(SystemInfo)]
        core.retro_load_game.argtypes = [c.POINTER(GameInfo)]
        core.retro_load_game.restype = c.c_bool
        core.retro_get_memory_size.restype = c.c_size_t
        core.retro_get_memory_data.restype = c.c_void_p
        core.retro_serialize_size.restype = c.c_size_t
        core.retro_serialize.argtypes = [c.c_void_p, c.c_size_t]
        core.retro_serialize.restype = c.c_bool
        core.retro_unserialize.argtypes = [c.c_void_p, c.c_size_t]
        core.retro_unserialize.restype = c.c_bool
        core.retro_init()
        info = SystemInfo()
        core.retro_get_system_info(c.byref(info))
        payload = Path(content).read_bytes()
        buffer = c.create_string_buffer(payload)
        game = GameInfo(
            str(Path(content).resolve()).encode(),
            c.cast(buffer, c.c_void_p),
            len(payload),
            None,
        )
        assert core.retro_load_game(c.byref(game)), (
            "Native core refused selected content"
        )
        try:
            for frame in range(frames):
                core.retro_run()
                # pzretro executes on its own thread; do not starve that thread.
                time.sleep(0.002)
            assert len(videos) > 10, "No native content frames"
            assert any(v[3] > 1 for v in videos), "Only blank/uniform frames"
            assert polls, "Core did not poll input"
            assert not shutdown, f"Start requested native exit: {shutdown}"
            assert audio, "Core did not deliver audio callbacks"
            size = core.retro_serialize_size()
            if size:
                saved = c.create_string_buffer(size)
                assert core.retro_serialize(saved, size), "Core could not serialize"
                assert core.retro_unserialize(saved, size), (
                    "Core could not restore its own state"
                )
            print(
                f"{info.name.decode()}: {len(videos)} nonblank-capable frames, "
                f"{len(polls)} input polls, {sum(audio)} audio samples, Start did not exit"
            )
        finally:
            core.retro_unload_game()
            core.retro_deinit()


if __name__ == "__main__":
    probe(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 180)

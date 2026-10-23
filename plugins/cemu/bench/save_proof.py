"""Bounded BotW System > Save route. A failed route is not storage proof."""

import ctypes
import hashlib
import json
import os
import select
import struct
import time
from collections.abc import Callable
from pathlib import Path

from gamepad import Gamepad
from gameplay_gate import FrameCapture

Record = dict[str, object]


def game_data(root: Path) -> dict[str, Record]:
    result = {}
    for path in sorted(root.rglob("game_data.sav")):
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root.resolve())
        ):
            raise RuntimeError("Unsafe game_data.sav under saveRoot")
        with path.open("rb") as source:
            sha = hashlib.file_digest(source, "sha256").hexdigest()
        result[str(path.relative_to(root))] = {
            "sha256": sha,
            "mtimeNs": path.stat().st_mtime_ns,
        }
    if not result:
        raise RuntimeError("No game_data.sav under declared saveRoot")
    return result


def press(
    pad: Gamepad,
    code: int,
    gap: float = 0.5,
    wait: Callable[[float], None] = time.sleep,
) -> None:
    pad.send((0, 1, code, 1))
    wait(0.15)
    pad.send((0, 1, code, 0))
    wait(gap)


class SaveProof:
    def __init__(
        self,
        root: Path,
        folder: Path,
        wait: Callable[[float], None] = time.sleep,
        timeout_s: float = 30,
    ):
        self.root = root
        self.wait = wait
        self.timeout_s = timeout_s
        self.folder = folder
        self.changed: dict[str, Record] = {}
        self.watch: SaveReadWatch | None = None

    def verify_declaration(self, tree: dict[int, Record]) -> None:
        for process in tree.values():
            argv = process.get("argv", [])
            if not isinstance(argv, list):
                continue
            for arg in argv:
                if not isinstance(arg, str) or not arg.startswith("{"):
                    continue
                try:
                    data = json.loads(arg)
                except ValueError:
                    continue
                if isinstance(data, dict) and data.get("saveRoot") == str(self.root):
                    return
        raise RuntimeError("--save-root does not match this launch's declared saveRoot")

    def save(
        self, pad: Gamepad | None, capture: FrameCapture, tree: dict[int, Record]
    ) -> None:
        self.verify_declaration(tree)
        if pad is None:
            raise RuntimeError("Save proof requires an input script and bench pad")
        before = game_data(self.root)
        (self.folder / "game-data-before.json").write_text(
            json.dumps(before, indent=2) + "\n"
        )
        press(pad, 0x13B, wait=self.wait)  # Plus / BTN_START
        for _ in range(10):
            press(
                pad, 0x137, wait=self.wait
            )  # R: 0.5 second gaps between releases and next presses
        press(pad, 0x131, wait=self.wait)  # Wii U A / BTN_EAST: Save
        press(pad, 0x131, wait=self.wait)  # Confirm
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            after = game_data(self.root)
            self.changed = {
                key: value
                for key, value in after.items()
                if key not in before
                or (
                    value["sha256"] != before[key]["sha256"]
                    and value["mtimeNs"] != before[key]["mtimeNs"]
                )
            }
            if self.changed:
                self.wait(2)
                stable = game_data(self.root)
                if all(stable.get(key) == value for key, value in self.changed.items()):
                    break
            self.wait(0.5)
        else:
            raise RuntimeError(
                "Save route unproven: no changed game_data.sav hash and mtime within 30 seconds"
            )
        (self.folder / "game-data-written.json").write_text(
            json.dumps(self.changed, indent=2) + "\n"
        )
        press(pad, 0x13B, wait=self.wait)
        # A menu is never a gameplay sample, even after a successful file write.
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            if capture.reference.classify(capture.capture()) == "gameplay":
                return
            self.wait(1)
        raise RuntimeError("Save was written but gameplay did not return after menu")

    def watch_reads(self, tree: dict[int, Record]) -> None:
        self.verify_declaration(tree)
        self.watch = SaveReadWatch(
            self.root,
            {
                pid
                for pid, process in tree.items()
                if Path(str(process.get("exe"))).name == "Cemu"
            },
        )

    def verify_loaded(
        self, pad: Gamepad | None, capture: FrameCapture, tree: dict[int, Record]
    ) -> None:
        self.verify_declaration(tree)
        after = game_data(self.root)
        if not self.changed or any(
            after.get(key, {}).get("sha256") != value["sha256"]
            for key, value in self.changed.items()
        ):
            raise RuntimeError("New game_data.sav did not survive stop/relaunch")
        reads = self.watch.collect() if self.watch else {}
        (self.folder / "game-data-reads.json").write_text(
            json.dumps(reads, indent=2) + "\n"
        )
        if not any(
            reads.get(key) == value["sha256"] for key, value in self.changed.items()
        ):
            raise RuntimeError(
                "No actual Cemu read of newly written game_data.sav observed after relaunch"
            )
        (self.folder / "game-data-reloaded.json").write_text(
            json.dumps(after, indent=2) + "\n"
        )


class SaveReadWatch:
    """Linux fanotify OPEN notifications, installed after launch materialization."""

    def __init__(self, root: Path, renderers: set[int]):
        self.root = root.resolve(strict=True)
        self.renderers = renderers
        libc = ctypes.CDLL(None, use_errno=True)
        libc.fanotify_init.argtypes = [ctypes.c_uint, ctypes.c_uint]
        libc.fanotify_mark.argtypes = [
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_uint64,
            ctypes.c_int,
            ctypes.c_char_p,
        ]
        self.fd = libc.fanotify_init(1 | 2, os.O_RDONLY | os.O_CLOEXEC)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), "fanotify_init failed")
        try:
            for directory in [
                self.root,
                *(path for path in self.root.rglob("*") if path.is_dir()),
            ]:
                if directory.is_symlink():
                    raise RuntimeError("Symlink under saveRoot")
                if (
                    libc.fanotify_mark(
                        self.fd, 1, 0x20 | 0x08000000, -100, os.fsencode(directory)
                    )
                    < 0
                ):
                    raise OSError(ctypes.get_errno(), "fanotify_mark failed")
        except BaseException:
            self.close()
            raise

    def collect(self) -> dict[str, str]:
        reads = {}
        while select.select([self.fd], [], [], 0)[0]:
            data = os.read(self.fd, 65536)
            offset = 0
            while offset < len(data):
                length, _version, _reserved, _metadata, _mask, event_fd, pid = (
                    struct.unpack_from("=IBBHQii", data, offset)
                )
                offset += length
                if event_fd < 0:
                    raise RuntimeError(
                        "Save-read notification overflow; load proof unavailable"
                    )
                try:
                    path = Path(os.readlink(f"/proc/self/fd/{event_fd}"))
                    if (
                        pid in self.renderers
                        and path.name == "game_data.sav"
                        and path.is_relative_to(self.root)
                    ):
                        with os.fdopen(os.dup(event_fd), "rb") as source:
                            reads[str(path.relative_to(self.root))] = (
                                hashlib.file_digest(source, "sha256").hexdigest()
                            )
                finally:
                    os.close(event_fd)
        return reads

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

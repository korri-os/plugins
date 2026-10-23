"""Observe ordinary InputPlumber admission; never change its management policy.

Only cleanup effect: stop this probe's newly created, now-source-less composite
through InputPlumber's existing CompositeDevice.Stop method. Its native Xbox
profile is persistent, so destroying the uinput source alone is insufficient.
"""

import fcntl
import json
import os
import struct
import subprocess
import time
from pathlib import Path
from typing import cast

from gamepad import NAME, PHYS

SERVICE = "org.shadowblip.InputPlumber"
MANAGER = "/org/shadowblip/InputPlumber/Manager"
COMPOSITE0 = "/org/shadowblip/InputPlumber/CompositeDevice0"
INTERFACE = "org.shadowblip.Input.CompositeDevice"


def output(*args: str) -> str:
    return subprocess.check_output(args, text=True, timeout=15).strip()


def property_value(path: str, interface: str, name: str) -> object:
    response = json.loads(
        output(
            "busctl",
            "--system",
            "--json=short",
            "get-property",
            SERVICE,
            path,
            interface,
            name,
        )
    )
    return response["data"]


def composites() -> set[str]:
    return {
        path
        for path in output("busctl", "--system", "--list", "tree", SERVICE).splitlines()
        if path.startswith("/org/shadowblip/InputPlumber/CompositeDevice")
    }


def attached_devices() -> list[dict[str, object]]:
    devices: list[dict[str, object]] = []
    for device in sorted(Path("/sys/class/input").glob("event*/device")):
        words = (device / "capabilities/key").read_text().split()
        mask = sum(
            int(word, 16) << (64 * index) for index, word in enumerate(reversed(words))
        )
        devices.append(
            {
                "event": device.parent.name,
                "name": (device / "name").read_text().strip(),
                "phys": (device / "phys").read_text().strip()
                if (device / "phys").exists()
                else "",
                "gamepad": bool(mask & ((1 << 0x130) | (1 << 0x120))),
                "sysfs": os.path.realpath(device),
            }
        )
    return devices


def external_gamepads(
    devices: list[dict[str, object]], builtin_paths: list[str]
) -> list[dict[str, object]]:
    builtin = {Path(path).name for path in builtin_paths}
    return [
        device
        for device in devices
        if device["gamepad"]
        and device["event"] not in builtin
        and not (
            str(device["name"]).startswith("Korri Seat P")
            and str(device["phys"]).startswith("korri/input-seat/")
        )
        and not (
            device["name"] == "Microsoft X-Box 360 pad"
            and not device["phys"]
            and "/devices/virtual/input/" in str(device["sysfs"])
        )
    ]


def seat_state(path: Path) -> dict[str, object]:
    with path.open("rb", buffering=0) as source:
        keys = bytearray(96)
        fcntl.ioctl(source, 0x80604518, keys)  # EVIOCGKEY(96)
        axes: dict[str, int] = {}
        for axis in (0, 1, 2, 3, 4, 5, 16, 17):
            info = bytearray(24)
            fcntl.ioctl(source, 0x80184540 + axis, info)  # EVIOCGABS
            axes[str(axis)] = struct.unpack("6i", info)[0]
        return {"deviceNumber": os.stat(path).st_rdev, "keys": keys.hex(), "axes": axes}


class InputObserver:
    def __init__(self, folder: Path):
        self.folder = folder
        self.previous: bool | None = None
        self.sources: list[str] = []
        self.readers: dict[int, str] = {}
        self.p1: Path | None = None
        self.p1_before: dict[str, object] = {}
        self.events: list[dict[str, object]] = []
        self.before_composites: set[str] = set()
        self.owned_composites: set[str] = set()
        self.state: dict[str, object] = {"managementPolicyWritten": False}

    def persist(self) -> None:
        (self.folder / "input-observer.json").write_text(
            json.dumps(self.state, indent=2) + "\n"
        )

    def begin(self) -> None:
        previous = property_value(
            MANAGER, "org.shadowblip.InputManager", "ManageAllDevices"
        )
        if not isinstance(previous, bool):
            raise TypeError("InputPlumber returned invalid ManageAllDevices")
        self.previous = previous
        sources = property_value(COMPOSITE0, INTERFACE, "SourceDevicePaths")
        if not isinstance(sources, list) or not all(
            isinstance(path, str) for path in sources
        ):
            raise RuntimeError("Invalid built-in source paths")
        self.sources = cast(list[str], sources)
        devices = attached_devices()
        self.before_composites = composites()
        self.state.update(
            {
                "before": previous,
                "devicesBefore": devices,
                "builtinSourcesBefore": self.sources,
                "compositesBefore": sorted(self.before_composites),
            }
        )
        self.persist()
        external = external_gamepads(devices, self.sources)
        if external or self.before_composites != {COMPOSITE0}:
            raise RuntimeError(
                f"External/unknown controller state; refusing probe: {external}"
            )
        for device in devices:
            if str(device["name"]).startswith("Korri Seat P"):
                path = Path("/dev/input") / str(device["event"])
                self.readers[os.open(path, os.O_RDONLY | os.O_NONBLOCK)] = str(
                    device["name"]
                )
                if device["name"] == "Korri Seat P1":
                    self.p1 = path
                    self.p1_before = seat_state(path)
        if self.p1 is None:
            raise RuntimeError("Korri Seat P1 is missing")
        self.state["seatP1Before"] = self.p1_before
        self.persist()

    def collect(self) -> None:
        if not self.owned_composites:
            bench_nodes = {
                str(device["event"])
                for device in attached_devices()
                if device["name"] == NAME and device["phys"] == PHYS
            }
            for path in composites() - self.before_composites:
                sources = property_value(path, INTERFACE, "SourceDevicePaths")
                if isinstance(sources, list) and any(
                    Path(str(node)).name in bench_nodes for node in sources
                ):
                    self.owned_composites.add(path)
            self.state["probeComposites"] = sorted(self.owned_composites)
        for fd, name in self.readers.items():
            while True:
                try:
                    data = os.read(fd, 24 * 256)
                except BlockingIOError:
                    break
                if not data:
                    break
                for seconds, micros, kind, code, value in struct.iter_unpack(
                    "llHHi", data
                ):
                    if kind:
                        self.events.append(
                            {
                                "seat": name,
                                "seconds": seconds,
                                "microseconds": micros,
                                "type": kind,
                                "code": code,
                                "value": value,
                            }
                        )
        (self.folder / "seat-events.json").write_text(
            json.dumps(self.events, indent=2) + "\n"
        )

    def close(self) -> None:
        try:
            self.collect()
            # The source has been destroyed. Never stop an unrelated, occupied
            # composite, even if its D-Bus object path was recycled meanwhile.
            for path in self.owned_composites:
                deadline = time.monotonic() + 3
                while path in composites():
                    sources = property_value(path, INTERFACE, "SourceDevicePaths")
                    if sources == []:
                        output(
                            "busctl",
                            "--system",
                            "call",
                            SERVICE,
                            path,
                            INTERFACE,
                            "Stop",
                        )
                        break
                    if time.monotonic() >= deadline:
                        raise RuntimeError(
                            "Probe composite still owns a source; refusing to stop it"
                        )
                    time.sleep(0.1)
            time.sleep(1)
            after = property_value(
                MANAGER, "org.shadowblip.InputManager", "ManageAllDevices"
            )
            self.state["after"] = after
            self.state["managementUnchanged"] = after == self.previous
            self.state["compositesAfter"] = sorted(composites())
            self.state["compositesRestored"] = composites() == self.before_composites
            if self.previous is not None and (
                after != self.previous or not self.state["compositesRestored"]
            ):
                raise RuntimeError(
                    "InputPlumber topology/policy changed during bench; review input-observer.json"
                )
            if self.p1 is not None:
                sources = property_value(COMPOSITE0, INTERFACE, "SourceDevicePaths")
                self.state["builtinSourcesAfter"] = sources
                self.state["seatP1After"] = seat_state(self.p1)
                self.state["builtinUnchanged"] = sorted(
                    cast(list[str], sources)
                ) == sorted(self.sources)
                self.state["seatP1Unchanged"] = (
                    self.state["seatP1After"] == self.p1_before
                )
                if (
                    not self.state["builtinUnchanged"]
                    or not self.state["seatP1Unchanged"]
                ):
                    raise RuntimeError(
                        "Built-in controller or seat P1 changed during bench"
                    )
        finally:
            for fd in self.readers:
                os.close(fd)
            self.readers.clear()
            self.persist()

"""Restricted native evemu-play event input; Linux uinput ABI, no Korri config."""

import fcntl
import math
import os
import struct
from pathlib import Path

# Linux input-event-codes.h, standard Xbox buttons and axes. No keyboard/Guide.
BUTTONS = set(range(0x130, 0x13F)) - {0x13C}
AXES = {
    0: (-32768, 32767),
    1: (-32768, 32767),
    2: (0, 255),
    3: (-32768, 32767),
    4: (-32768, 32767),
    5: (0, 255),
    16: (-1, 1),
    17: (-1, 1),
}
Event = tuple[float, int, int, int]
NAME = "Korri bench gamepad"
BUS = 5
VENDOR = 0x045E
PRODUCT = 0x02D1
VERSION = 0x0114
PHYS = "korri-cemu-bench/input0"


def gamepad_identity() -> dict[str, int | str]:
    return {
        "name": NAME,
        "bus": BUS,
        "vendor": VENDOR,
        "product": PRODUCT,
        "version": VERSION,
        "phys": PHYS,
    }


def read_script(path: Path) -> list[Event]:
    events: list[Event] = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 5 or fields[0] != "E:":
            raise ValueError(f"{path}:{number}: expected native evemu E: event")
        at, kind, code, value = (
            float(fields[1]),
            int(fields[2], 16),
            int(fields[3], 16),
            int(fields[4]),
        )
        valid = (
            (kind == 0 and code == 0 and value == 0)
            or (kind == 1 and code in BUTTONS and value in (0, 1))
            or (kind == 3 and code in AXES and AXES[code][0] <= value <= AXES[code][1])
        )
        if (
            not valid
            or not math.isfinite(at)
            or not 0 <= at <= 3600
            or (events and at < events[-1][0])
        ):
            raise ValueError(f"{path}:{number}: invalid or non-monotonic gamepad event")
        events.append((at, kind, code, value))
    if not events:
        raise ValueError("Input script has no events")
    return events


class Gamepad:
    def __init__(self) -> None:
        self.fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        try:
            for kind in (1, 3):
                fcntl.ioctl(self.fd, 0x40045564, kind)  # UI_SET_EVBIT
            for button in sorted(BUTTONS):
                fcntl.ioctl(self.fd, 0x40045565, button)
            for axis in AXES:
                fcntl.ioctl(self.fd, 0x40045567, axis)
            # uinput_user_dev, stable Linux ABI. Deliberately unique identity;
            # never impersonate Korri Seat P1 or an existing physical device.
            name = NAME.encode()
            # Bench-only synthetic controller. Native 60-xbox_one_gamepad.yaml
            # explicitly auto-manages 045e:02d1. InputPlumber 0.75.2 manager.rs
            # 1232-1267 accepts virtual Bluetooth (bus 5) devices. Distinct phys
            # satisfies inputd's ordinary reconnect identity; no seat spoofing.
            fcntl.ioctl(self.fd, 0x4008556C, PHYS.encode() + b"\0")  # UI_SET_PHYS
            header = struct.pack("80sHHHHI", name, BUS, VENDOR, PRODUCT, VERSION, 0)
            maximum = [AXES.get(i, (0, 0))[1] for i in range(64)]
            minimum = [AXES.get(i, (0, 0))[0] for i in range(64)]
            os.write(
                self.fd, header + struct.pack("256i", *(maximum + minimum + [0] * 128))
            )
            fcntl.ioctl(self.fd, 0x5501)  # UI_DEV_CREATE
        except BaseException:
            os.close(self.fd)
            raise

    def send(self, event: Event) -> None:
        _, kind, code, value = event
        os.write(self.fd, struct.pack("llHHi", 0, 0, kind, code, value))
        if kind:
            os.write(self.fd, struct.pack("llHHi", 0, 0, 0, 0, 0))

    def close(self) -> None:
        try:
            for code in BUTTONS:
                self.send((0, 1, code, 0))
            for code in AXES:
                self.send((0, 3, code, 0))
            fcntl.ioctl(self.fd, 0x5502)  # UI_DEV_DESTROY
        finally:
            os.close(self.fd)

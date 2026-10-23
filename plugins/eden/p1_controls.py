"""Seed only untouched Eden P1 bindings from its native Controls UI record."""

import configparser
import ctypes
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Device:
    name: str
    guid: str
    port: int


class Guid(ctypes.Structure):
    _fields_ = [("data", ctypes.c_ubyte * 16)]
    data: ctypes.Array[ctypes.c_ubyte]


def discover(sdl2: str, sdl3: str) -> list[Device]:
    # Eden's SDL2 compatibility library loads SDL3. Preload the same pinned
    # library in this helper process, without changing the game's environment.
    dependency = ctypes.CDLL(sdl3, mode=ctypes.RTLD_GLOBAL)
    sdl = ctypes.CDLL(sdl2)
    sdl.SDL_InitSubSystem.argtypes = [ctypes.c_uint32]
    sdl.SDL_InitSubSystem.restype = ctypes.c_int
    sdl.SDL_QuitSubSystem.argtypes = [ctypes.c_uint32]
    sdl.SDL_NumJoysticks.restype = ctypes.c_int
    sdl.SDL_JoystickNameForIndex.argtypes = [ctypes.c_int]
    sdl.SDL_JoystickNameForIndex.restype = ctypes.c_char_p
    sdl.SDL_JoystickPathForIndex.argtypes = [ctypes.c_int]
    sdl.SDL_JoystickPathForIndex.restype = ctypes.c_char_p
    sdl.SDL_JoystickGetDeviceGUID.argtypes = [ctypes.c_int]
    sdl.SDL_JoystickGetDeviceGUID.restype = Guid
    flags = 0x2200  # SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER
    if sdl.SDL_InitSubSystem(flags) != 0:
        raise ValueError("SDL controller discovery is unavailable")
    try:
        count: int = sdl.SDL_NumJoysticks()
        if count < 0:
            raise ValueError("SDL controller enumeration failed")
        ports: dict[str, int] = {}
        devices = []
        for index in range(count):
            raw = bytearray(sdl.SDL_JoystickGetDeviceGUID(index).data)
            # Eden sdl_driver.cpp:17–23 clears the controller-name CRC, then
            # assigns a port among devices with that normalized GUID.
            raw[2:4] = b"\0\0"
            guid = raw.hex()
            port = ports.get(guid, 0)
            ports[guid] = port + 1
            raw_name: bytes | None = sdl.SDL_JoystickNameForIndex(index)
            name = raw_name.decode(errors="replace") if raw_name else ""
            raw_path: bytes | None = sdl.SDL_JoystickPathForIndex(index)
            if raw_path:
                event = Path(raw_path.decode(errors="replace")).name
                if re.fullmatch(r"event[0-9]+", event):
                    try:
                        # SDL names all four observed seats "Xbox 360 Controller".
                        # Its native device path identifies InputPlumber's seat.
                        name = (
                            (Path("/sys/class/input") / event / "device/name")
                            .read_text()
                            .strip()
                        )
                    except OSError:
                        pass
            devices.append(Device(name, guid, port))
        return devices
    finally:
        sdl.SDL_QuitSubSystem(flags)
        # Keep SDL3 loaded until SDL2 has finished shutting down.
        del dependency


def find_seat(devices: list[Device]) -> Device | None:
    seats = [device for device in devices if device.name == "Korri Seat P1"]
    return seats[0] if len(seats) == 1 else None


def uses_defaults(config: Path) -> bool:
    native = configparser.ConfigParser(interpolation=None)
    try:
        if not native.read(config):
            raise ValueError("native Eden configuration is unreadable")
        if not native.has_section("Controls"):
            return True
        return all(
            native.getboolean("Controls", key)
            for key in native["Controls"]
            if key.startswith("player_0_") and key.endswith("\\default")
        )
    except (configparser.Error, ValueError) as error:
        # Native parser errors can contain arbitrary private configuration text.
        raise ValueError("native Eden P1 default flags could not be read") from error


def configure(
    config: Path, seat: Device | None, template: Path, crudini: str
) -> Literal["kept", "missing", "configured"]:
    if not uses_defaults(config):
        return "kept"
    if seat is None or seat.name != "Korri Seat P1":
        return "missing"
    if not re.fullmatch(r"[0-9a-f]{32}", seat.guid) or seat.port < 0:
        raise ValueError("invalid native SDL seat identity")
    text = template.read_text()
    guids = set(re.findall(r"\bguid:([0-9a-f]{32})", text))
    ports = set(re.findall(r"\bport:([0-9]+)", text))
    if len(guids) != 1 or len(ports) != 1:
        raise ValueError("native P1 mapping record has an ambiguous identity")
    text = text.replace("guid:" + guids.pop(), "guid:" + seat.guid)
    text = re.sub(r"\bport:[0-9]+", "port:" + str(seat.port), text)
    # One native INI merge; every other player and setting remains Eden-owned.
    subprocess.run(
        [crudini, "--merge", str(config)],
        input=text,
        text=True,
        check=True,
        timeout=10,
    )
    return "configured"


def main() -> None:
    config, template, sdl2, sdl3, crudini = sys.argv[1:]
    try:
        if not uses_defaults(Path(config)):
            return
        try:
            seat = find_seat(discover(sdl2, sdl3))
        except (OSError, ValueError, AttributeError):
            seat = None
        result = configure(Path(config), seat, Path(template), crudini)
        if result == "missing":
            print(
                "Eden P1: Korri Seat P1 unavailable; keeping Eden's native defaults",
                file=sys.stderr,
            )
        elif result == "configured":
            print("Eden P1: native defaults assigned to Korri Seat P1", file=sys.stderr)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("Eden P1: native controller configuration failed", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()

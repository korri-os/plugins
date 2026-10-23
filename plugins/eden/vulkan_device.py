"""Select Turnip using Eden 0.2.1's device order, not the loader's order."""

import configparser
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Device:
    name: str
    vendor: int
    kind: str
    driver: str

    def is_turnip(self) -> bool:
        return (
            "Adreno" in self.name
            and self.driver == "DRIVER_ID_MESA_TURNIP"
            and self.kind
            in (
                "PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU",
                "PHYSICAL_DEVICE_TYPE_DISCRETE_GPU",
            )
        )


def read_devices(summary: str) -> list[Device]:
    """Read the pinned vulkaninfo --summary's native device properties."""
    records: list[dict[str, str]] = []
    for line in summary.splitlines():
        if re.fullmatch(r"GPU[0-9]+:", line):
            records.append({})
        elif records and "=" in line:
            key, value = line.strip().split("=", 1)
            records[-1][key.strip()] = value.strip()
    devices = []
    for record in records:
        try:
            devices.append(
                Device(
                    record["deviceName"],
                    int(record["vendorID"], 0),
                    record["deviceType"],
                    record["driverID"],
                )
            )
        except (KeyError, ValueError) as error:
            raise ValueError("incomplete Vulkan device properties") from error
    if not devices:
        raise ValueError("vulkaninfo returned no device properties")
    return devices


def eden_order(devices: list[Device]) -> list[Device]:
    # Exact stable ordering: pinned vulkan_wrapper.cpp:23–69,470–475.
    # The package check pins that complete source file and the Eden version.
    ordered = sorted(
        devices, key=lambda device: device.name.encode("utf-8"), reverse=True
    )
    ordered.sort(key=lambda device: device.kind != "PHYSICAL_DEVICE_TYPE_DISCRETE_GPU")
    for vendor in reversed((0x10DE, 0x1002, 0x8086)):
        ordered.sort(key=lambda device: device.vendor != vendor)
    ordered.sort(key=lambda device: "Microsoft" in device.name)
    return ordered


def configure(config: Path, devices: list[Device], crudini: str) -> tuple[int, bool]:
    native = configparser.ConfigParser(interpolation=None)
    try:
        loaded = native.read(config)
    except configparser.Error as error:
        # Parser messages can contain arbitrary configuration lines or credentials.
        raise ValueError("native Eden configuration could not be parsed") from error
    if not loaded:
        raise ValueError("native Eden configuration is unreadable")
    try:
        use_default = native.getboolean(
            "Renderer", "vulkan_device\\default", fallback=True
        )
        configured_index = (
            0 if use_default else native.getint("Renderer", "vulkan_device", fallback=0)
        )
    except (configparser.Error, ValueError) as error:
        raise ValueError("native Vulkan device setting is invalid") from error
    ordered = eden_order(devices)
    if use_default:
        selected = next(
            (i for i, device in enumerate(ordered) if device.is_turnip()), None
        )
        if selected is None:
            raise ValueError(
                "no Adreno/Turnip Vulkan device is available; refusing software fallback"
            )
    else:
        selected = configured_index
    if not 0 <= selected < len(ordered):
        raise ValueError(f"native Vulkan device index {selected} is unavailable")
    if not ordered[selected].is_turnip():
        raise ValueError(
            f"native Vulkan device index {selected} is {ordered[selected].name}, not Adreno/Turnip; "
            "choose an Adreno device in Eden's native settings"
        )
    if use_default:
        # One atomic native INI merge. Do not write provenance or Korri settings.
        subprocess.run(
            [crudini, "--merge", str(config)],
            input=f"[Renderer]\nvulkan_device={selected}\nvulkan_device\\default=false\n",
            text=True,
            check=True,
            timeout=10,
        )
    return selected, use_default


def main() -> None:
    started = time.monotonic()
    try:
        config, vulkaninfo, crudini = sys.argv[1:]
        probe = subprocess.run(
            [vulkaninfo, "--summary"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        devices = read_devices(probe.stdout)
        selected, changed = configure(Path(config), devices, crudini)
        name = eden_order(devices)[selected].name
        print(
            f"Eden Vulkan: index {selected} ({name}); native choice "
            f"{'selected' if changed else 'kept'}; preflight {(time.monotonic() - started) * 1000:.0f} ms",
            file=sys.stderr,
        )
    except (
        ValueError,
        OSError,
        configparser.Error,
        subprocess.SubprocessError,
    ) as error:
        print(f"Eden Vulkan device selection failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()

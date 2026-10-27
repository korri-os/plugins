#!/usr/bin/env python3
"""Add netplay facts from pinned core info and the built core's libretro ABI.

Build-machine tool only. Installed plugins remain effect-free TypeScript source.
"""

import argparse
import ctypes
import json
import re
from pathlib import Path


# libretro.h: retro_system_info. No retro_init or content execution is needed.
class SystemInfo(ctypes.Structure):
    _fields_ = [
        ("library_name", ctypes.c_char_p),
        ("library_version", ctypes.c_char_p),
        ("valid_extensions", ctypes.c_char_p),
        ("need_fullpath", ctypes.c_bool),
        ("block_extract", ctypes.c_bool),
    ]


def deterministic(info_path: Path) -> bool:
    # Custom cores may have no upstream info yet. Absence grants no netplay.
    if not info_path.exists():
        return False
    values = re.findall(
        r'^\s*savestate_features\s*=\s*"([^"\n]*)"\s*(?:#.*)?$',
        info_path.read_text(),
        flags=re.MULTILINE,
    )
    if len(values) > 1:
        raise ValueError(f"Duplicate savestate_features in {info_path}")
    return values == ["deterministic"]


def system_info(core_path: Path) -> dict[str, str]:
    core = ctypes.CDLL(str(core_path))
    get_info = core.retro_get_system_info
    get_info.argtypes = [ctypes.POINTER(SystemInfo)]
    get_info.restype = None
    info = SystemInfo()
    get_info(ctypes.byref(info))
    if not info.library_name or not info.library_version:
        raise ValueError(f"Missing libretro library name or version in {core_path}")
    return {
        "library": info.library_name.decode("utf-8"),
        "version": info.library_version.decode("utf-8"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--core-info", type=Path, required=True)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.template.read_text()
    marker = "    // @netplay@\n"
    if source.count(marker) != 1:
        raise ValueError("Expected one netplay slot in the runner template")
    field = ""
    if deterministic(args.core_info):
        field = f"    netplay: {json.dumps(system_info(args.core))},\n"
    args.output.write_text(source.replace(marker, field))


if __name__ == "__main__":
    main()

#!/usr/bin/env nix
#! nix shell nixpkgs#python3 --command python3
"""Load the packaged controller database through SDL's production lookup path."""

import ctypes
from pathlib import Path
import sys

library, database = sys.argv[1:]
assert Path(database).is_file()
sdl = ctypes.CDLL(library)


class Guid(ctypes.Structure):
    _fields_ = [("data", ctypes.c_uint8 * 16)]


for name, arguments, result in [
    ("SDL_SetHint", [ctypes.c_char_p, ctypes.c_char_p], ctypes.c_int),
    ("SDL_Init", [ctypes.c_uint32], ctypes.c_int),
    ("SDL_GameControllerMappingForGUID", [Guid], ctypes.c_void_p),
    ("SDL_GetError", [], ctypes.c_char_p),
    ("SDL_free", [ctypes.c_void_p], None),
    ("SDL_Quit", [], None),
]:
    function = getattr(sdl, name)
    function.argtypes, function.restype = arguments, result

# Solarus System::initialize sets this hint before initializing controllers.
assert sdl.SDL_SetHint(b"SDL_GAMECONTROLLERCONFIG_FILE", database.encode())
assert sdl.SDL_Init(0x2000) == 0, sdl.SDL_GetError().decode()
try:
    # The generic Linux Xbox 360 GUID in Solarus's database and the four GUIDs
    # observed from real Korri player seats on the Mini V2. SDL adds their CRCs.
    for identifier in [
        "030000005e0400008e02000001000000",
        "030082db5e0400008e02000001000000",
        "0300c2da5e0400008e02000001000000",
        "0300031a5e0400008e02000001000000",
        "030042d85e0400008e02000001000000",
    ]:
        guid = Guid((ctypes.c_uint8 * 16).from_buffer_copy(bytes.fromhex(identifier)))
        pointer = sdl.SDL_GameControllerMappingForGUID(guid)
        assert pointer, f"No mapping for {identifier}: {sdl.SDL_GetError().decode()}"
        try:
            mapping = ctypes.string_at(pointer).decode()
        finally:
            sdl.SDL_free(pointer)
        fields = dict(
            part.split(":", 1) for part in mapping.split(",")[2:] if ":" in part
        )
        expected = {
            "dpup": "h0.1",
            "dpright": "h0.2",
            "dpdown": "h0.4",
            "dpleft": "h0.8",
            "a": "b0",
            "b": "b1",
            "x": "b2",
            "y": "b3",
            "back": "b6",
            "start": "b7",
            "leftshoulder": "b4",
            "rightshoulder": "b5",
            "leftstick": "b9",
            "rightstick": "b10",
            "leftx": "a0",
            "lefty": "a1",
            "lefttrigger": "a2",
            "rightx": "a3",
            "righty": "a4",
            "righttrigger": "a5",
        }
        for control, binding in expected.items():
            assert fields.get(control) == binding, (
                f"{identifier} {control}: expected {binding}, got {fields.get(control)}"
            )
        print(f"PASS {identifier}: four D-pad directions; sticks and buttons unchanged")
finally:
    sdl.SDL_Quit()

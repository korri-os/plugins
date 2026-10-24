"""Retain native libretro framebuffer pixels as a standard RGB PNG."""

import struct
import zlib
from pathlib import Path


def write_png(path, width, height, pitch, pixel_format, pixels):
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # PNG scanline: no filter.
        for x in range(width):
            if pixel_format == 1:  # Native little-endian XRGB8888.
                b, g, r = pixels[y * pitch + x * 4 : y * pitch + x * 4 + 3]
            else:
                value = struct.unpack_from("<H", pixels, y * pitch + x * 2)[0]
                if pixel_format == 2:  # RGB565.
                    r, g, b = (
                        (value >> 11) * 255 // 31,
                        ((value >> 5) & 63) * 255 // 63,
                        (value & 31) * 255 // 31,
                    )
                else:  # 0RGB1555 (libretro default).
                    r, g, b = (
                        ((value >> 10) & 31) * 255 // 31,
                        ((value >> 5) & 31) * 255 // 31,
                        (value & 31) * 255 // 31,
                    )
            rows.extend((r, g, b))

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    Path(path).write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )

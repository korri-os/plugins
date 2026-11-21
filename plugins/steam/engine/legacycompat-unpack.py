"""steam-legacycompat-unpack <work-dir> <bins_misc.zip.vz>

The unpack program of the artifact @korri:steam/legacycompat (ADR 0012,
korri#589). korrid downloads Valve's pinned `bins_misc_linuxarm64` package
from Valve's update servers and checks its sha256; this program then writes
Valve's `legacycompat/` folder from it into <work-dir>/legacycompat.

Proton copies `steamclient.dll`, `steamclient64.dll`, `Steam.dll`,
`SteamService.exe` (as steam.exe) and `GameOverlayRenderer64.dll` from
`$STEAM_COMPAT_CLIENT_INSTALL_PATH/legacycompat/` into every prefix. A
Steamworks game loads that steamclient(64).dll; Proton's ntdll then points its
exports at lsteamclient, which loads the engine's steamclient.so. An
engine-only Steam folder has no client, so this artifact supplies the folder.

In Valve's package, `legacycompat\\steamclient.dll`, `legacycompat\\
steamclient64.dll` and `legacycompat\\GameOverlayRenderer64.dll` are symbolic
links (with `\\` in their names) to files at the package root, the layout of
Valve's client. korrid's own archive reader refuses any link, so it cannot
open this package. This program writes each link as a regular copy of its
target and nothing outside `legacycompat/`.

VZ layout: b"VZa", a u32 timestamp, 5 bytes of LZMA1 properties, the LZMA1
stream, then the u32 CRC32 and u32 size of the decoded zip, then b"zv"
(reference: the spike's scripts/aka/vz-extract.py).

Exit status: 0 ready, 1 failed. Diagnostics go to stderr; stdout carries
nothing korrid reads. It writes only under <work-dir>.
"""
import io
import lzma
import os
import re
import struct
import sys
import zipfile
import zlib

# The files a Steamworks game under Proton needs; the package must hold them.
REQUIRED = ("steamclient.dll", "steamclient64.dll", "Steam.dll")
FOLDER = "legacycompat"
# The decoded zip of the pinned package is 29,388,966 bytes. Refuse a header
# that claims far more before decoding anything.
MAX_ZIP_BYTES = 256 * 1024 * 1024
MAX_FILE_BYTES = 128 * 1024 * 1024
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
S_IFMT, S_IFLNK, S_IFREG = 0o170000, 0o120000, 0o100000


class Refused(Exception):
    pass


def decode_vz(data):
    if len(data) < 12 + 10 or data[:3] != b"VZa" or data[-2:] != b"zv":
        raise Refused("not a VZa package")
    props = data[7:12]
    crc, size = struct.unpack("<II", data[-10:-2])
    if size > MAX_ZIP_BYTES:
        raise Refused(f"the package declares a {size}-byte zip")
    if props[0] >= 9 * 5 * 5:
        raise Refused("bad LZMA properties")
    lc, lp, pb = props[0] % 9, (props[0] // 9) % 5, props[0] // 45
    (dict_size,) = struct.unpack("<I", props[1:5])
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[
        {"id": lzma.FILTER_LZMA1, "dict_size": dict_size, "lc": lc, "lp": lp, "pb": pb}])
    try:
        raw = decoder.decompress(data[12:-10], max_length=size)
    except lzma.LZMAError as error:
        raise Refused(f"LZMA: {error}") from None
    if len(raw) != size or zlib.crc32(raw) & 0xFFFFFFFF != crc:
        raise Refused(f"decoded {len(raw)} of {size} bytes or the CRC32 does not match")
    return raw


def kind(info):
    mode = (info.external_attr >> 16) & S_IFMT
    if info.create_system == 3 and mode == S_IFLNK:
        return "link"
    if mode in (0, S_IFREG):
        return "dir" if info.filename.endswith(("/", "\\")) else "file"
    raise Refused(f"special file {info.filename!r}")


def plan(archive):
    """{name in legacycompat: zip entry to copy}, links resolved."""
    entries = {}
    for info in archive.infolist():
        if info.flag_bits & 0x1:
            raise Refused(f"encrypted entry {info.filename!r}")
        if info.filename in entries:
            raise Refused(f"repeated entry {info.filename!r}")
        entries[info.filename] = info
    wanted = {}
    for name, info in entries.items():
        parts = re.split(r"[/\\]", name)
        if parts[0] != FOLDER or len(parts) != 2 or parts[1] == "":
            continue
        base = parts[1]
        if not SAFE_NAME.match(base):
            raise Refused(f"unsafe name {name!r}")
        if base in wanted:
            raise Refused(f"repeated name {base!r}")
        what = kind(info)
        if what == "dir":
            raise Refused(f"folder inside {FOLDER}: {name!r}")
        if what == "link":
            if info.file_size > 256:
                raise Refused(f"link {name!r} is too long")
            target = archive.read(info).decode("utf-8", "strict")
            match = re.fullmatch(r"\.\./([^/\\]+)", target)
            if not match or not SAFE_NAME.match(match.group(1)):
                raise Refused(f"link {name!r} leads to {target!r}")
            info = entries.get(match.group(1))
            if info is None or kind(info) != "file":
                raise Refused(f"link {name!r} leads to no file in the package")
        if info.file_size > MAX_FILE_BYTES:
            raise Refused(f"{name!r} is {info.file_size} bytes")
        wanted[base] = info
    missing = [name for name in REQUIRED if name not in wanted]
    if missing:
        raise Refused(f"the package has no {FOLDER}/{', '.join(missing)}")
    return wanted


def write(work, archive, wanted):
    folder = os.path.join(work, FOLDER)
    os.mkdir(folder, 0o755)
    for name, info in sorted(wanted.items()):
        data = archive.read(info)
        if len(data) != info.file_size:
            raise Refused(f"{name}: read {len(data)} of {info.file_size} bytes")
        fd = os.open(os.path.join(folder, name),
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        with os.fdopen(fd, "wb") as out:
            out.write(data)


def main(argv):
    if len(argv) != 3:
        raise Refused("usage: steam-legacycompat-unpack <work-dir> <bins_misc.zip.vz>")
    work, package = argv[1], argv[2]
    if not os.path.isabs(work) or not os.path.isdir(work):
        raise Refused(f"work directory is not an absolute directory: {work}")
    if os.path.lexists(os.path.join(work, FOLDER)):
        raise Refused(f"{FOLDER} already exists in the work directory")
    with open(package, "rb") as source:
        data = source.read(MAX_ZIP_BYTES + 1)
    try:
        archive = zipfile.ZipFile(io.BytesIO(decode_vz(data)))
    except zipfile.BadZipFile as error:
        raise Refused(f"zip: {error}") from None
    with archive:
        wanted = plan(archive)
        write(work, archive, wanted)
    print(f"steam-legacycompat-unpack: wrote {FOLDER}/ with {', '.join(sorted(wanted))}",
          file=sys.stderr)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except (Refused, OSError, zipfile.BadZipFile, UnicodeDecodeError) as error:
        print(f"steam-legacycompat-unpack: {error}", file=sys.stderr)
        sys.exit(1)

"""Pick the launch entry Steam would use for an app, from Steam's own appinfo.vdf.

Ported from the spike's scripts/mini/steam-launch-entry.py (ADR 0083). The
engine runner maps every app to Proton (CompatToolMapping "0"), so Steam uses
the Windows entries; steam-engine-session asks for a Linux entry only when the
app has no Windows one. Selection mirrors Steam's: OS matches, no beta key, a 64-bit
entry before a 32-bit one, a "default" (or untyped) entry before others, then
appinfo order. No per-game rules.

Usage: launch-entry.py <appinfo.vdf> <appid> [--os windows|linux]
Prints shell-safe KEY=VALUE lines: EXE, ARGS, WORKDIR, INSTALLDIR, ENTRY, CANDIDATES.
"""
import shlex
import struct
import sys

STRINGS = []


def read_kv(buf, i):
    out = {}
    while True:
        t = buf[i]
        i += 1
        if t == 8:
            return out, i
        (k,) = struct.unpack_from("<I", buf, i)
        i += 4
        key = STRINGS[k]
        if t == 0:
            v, i = read_kv(buf, i)
        elif t == 1:
            e = buf.index(b"\0", i)
            v = buf[i:e].decode("utf-8", "replace")
            i = e + 1
        elif t in (2, 4, 6):
            (v,) = struct.unpack_from("<i", buf, i)
            i += 4
        elif t == 3:
            (v,) = struct.unpack_from("<f", buf, i)
            i += 4
        elif t in (7, 10):
            (v,) = struct.unpack_from("<Q", buf, i)
            i += 8
        else:
            raise ValueError(f"vdf type {t}")
        out[key] = v


def find_app(path, want):
    data = open(path, "rb").read()
    magic, _ = struct.unpack_from("<II", data, 0)
    if magic != 0x07564429:
        sys.exit(f"unsupported appinfo magic {magic:#x}")
    (table,) = struct.unpack_from("<q", data, 8)
    (n,) = struct.unpack_from("<I", data, table)
    p = table + 4
    for _ in range(n):
        e = data.index(b"\0", p)
        STRINGS.append(data[p:e].decode("utf-8", "replace"))
        p = e + 1
    pos = 16
    while pos < table:
        (appid,) = struct.unpack_from("<I", data, pos)
        if appid == 0:
            break
        (size,) = struct.unpack_from("<I", data, pos + 4)
        start = pos + 8
        if appid == want:
            kv, _ = read_kv(data, start + 4 + 4 + 8 + 20 + 4 + 20)
            return kv.get("appinfo", kv)
        pos = start + size
    return None


def main():
    if len(sys.argv) not in (3, 5):
        sys.exit(__doc__)
    path, appid = sys.argv[1], int(sys.argv[2])
    want_os = sys.argv[4] if len(sys.argv) == 5 else "windows"
    app = find_app(path, appid)
    if not app:
        sys.exit(f"app {appid} not in appinfo")
    config = app.get("config", {}) or {}
    launch = config.get("launch", {}) or {}
    cands = []
    for key in sorted(launch, key=lambda k: int(k) if str(k).isdigit() else 999):
        entry = launch[key]
        if not isinstance(entry, dict) or not entry.get("executable"):
            continue
        cfg = entry.get("config", {}) or {}
        oslist = [o for o in str(cfg.get("oslist", "")).split(",") if o]
        if oslist and want_os not in oslist:
            continue
        if cfg.get("betakey"):
            continue
        if str(cfg.get("ownsdlc", "")):
            continue
        arch = str(cfg.get("osarch", ""))
        etype = str(entry.get("type", "default") or "default")
        rank = (0 if etype in ("default", "") else 1, 0 if arch in ("64", "") else 1)
        cands.append((rank, key, entry))
    if not cands:
        sys.exit(f"app {appid}: no {want_os} launch entry")
    cands.sort(key=lambda c: c[0])
    _, key, entry = cands[0]
    exe = str(entry["executable"]).replace("\\", "/")
    work = str(entry.get("workingdir", "") or "").replace("\\", "/")
    fields = {
        "EXE": exe,
        "ARGS": str(entry.get("arguments", "") or ""),
        "WORKDIR": work,
        "INSTALLDIR": str(config.get("installdir", "")),
        "ENTRY": str(key),
        "CANDIDATES": str(len(cands)),
    }
    for k, v in fields.items():
        print(f"{k}={shlex.quote(v)}")
    try:
        words = shlex.split(fields["ARGS"])
    except ValueError:
        words = fields["ARGS"].split()
    print("ARGV=(" + " ".join(shlex.quote(w) for w in words) + ")")


if __name__ == "__main__":
    main()

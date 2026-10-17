#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3
"""Fail if a quest payload contains franchise or stock-template text.

Scans every printable run (>=3 chars) of the uncompressed quest bytes,
case-insensitively, for franchise terms. Prints all section IDs and every
printable string >= 4 chars so a human can review what the file says.
"""
import re
import sys
from pathlib import Path

def unlzss(src):
    """Allegro packfile LZSS (N=4096, F=18, THRESHOLD=2)."""
    N, F, TH = 4096, 18, 2
    ring = bytearray(N)
    r = N - F
    out = bytearray()
    i = 0
    flags = 0
    while i < len(src):
        flags >>= 1
        if not flags & 0x100:
            flags = src[i] | 0xFF00
            i += 1
            if i >= len(src):
                break
        if flags & 1:
            c = src[i]; i += 1
            out.append(c); ring[r] = c; r = (r + 1) & (N - 1)
        else:
            if i + 1 >= len(src):
                break
            a, b = src[i], src[i + 1]; i += 2
            a |= (b & 0xF0) << 4
            n = (b & 0x0F) + TH
            for k in range(n + 1):
                c = ring[(a + k) & (N - 1)]
                out.append(c); ring[r] = c; r = (r + 1) & (N - 1)
    return bytes(out)

data = Path(sys.argv[1]).read_bytes()
if data.startswith(b"slh!"):
    data = unlzss(data[4:])
head = data[:40]
print("header:", head[:31])
assert head.startswith(b"AG ZC Enhanced Quest File") or head.startswith(b"AG Zelda Classic"), \
    "not an uncompressed quest payload"
TERMS = [r"zelda", r"triforce", r"tri-force", r"ganon", r"hyrule", r"\blink\b", r"nintendo",
         r"din'?s", r"nayru", r"farore", r"octorok", r"moblin", r"lynel", r"darknut",
         r"stalfos", r"keese", r"gibdo", r"goriya", r"aquamentus", r"dodongo", r"manhandla",
         r"gleeok", r"digdogger", r"gohma", r"lanmola", r"patra", r"wizzrobe", r"pols voice",
         r"like like", r"vire", r"zol\b", r"\bgel\b", r"rope", r"tektite", r"leever", r"peahat",
         r"zora", r"ghini", r"armos", r"rupee", r"rupy", r"bs zelda", r"\bz1\b", r"\bz3\b",
         r"master sword", r"hookshot", r"ocarina", r"recorder", r"magical", r"lttp", r"mario",
         r"metroid", r"\bnes\b", r"abei", r"\bama\b", r"subrosia", r"hylian", r"fairy", r"potion",
         r"candle", r"boomerang", r"ladder", r"raft", r"bracelet", r"compass", r"whistle"]
runs = [m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{3,}", data)]
hits = []
# Native four-byte section IDs are format structure, not content.
SECTION_IDS = {"LINK"}
for r in runs:
    if r in SECTION_IDS:
        continue
    for t in TERMS:
        if re.search(t, r, re.I):
            hits.append((t, r[:120]))
sections = sorted(set(re.findall(rb"(?<=[\x00-\xff])(?:HDR |RULE|STR |DOOR|DMAP|MISC|MCLR|ICON|ITEM|WPN |MAP |CMBO|CMBA|CSET|TILE|MIDI|CHT |INIT|GUY |LINK|SUBS|FFSC|SFX |DROP|FAVS|ZINF|ADVM)", data)))
print("sections:", [s.decode() for s in sections])
readable = sorted({r for r in runs if len(r) >= 4 and re.search(r"[A-Za-z]{3}", r)})
print(f"readable strings ({len(readable)}):")
for r in readable:
    print("  ", r[:100])
if hits:
    print(f"FAIL: {len(hits)} franchise/stock hits")
    for t, r in hits[:80]:
        print(f"  [{t}] {r}")
    sys.exit(1)
print("PASS: no franchise terms")

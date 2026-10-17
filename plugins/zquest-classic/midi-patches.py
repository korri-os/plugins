#!/usr/bin/env python3
"""Convert FreePats' native bank map to Allegro DIGMID's native patch index."""

from pathlib import Path
import sys

source, destination = map(Path, sys.argv[1:])
banks = {"bank": {}, "drumset": {}}
current = None
for line in (source / "crude.cfg").read_text().splitlines():
    fields = line.split("#", 1)[0].split()
    if not fields:
        continue
    if fields[0] in banks:
        assert fields == [fields[0], "0"], fields
        current = banks[fields[0]]
        continue
    assert current is not None and len(fields) == 2, fields
    index = int(fields[0])
    assert 0 <= index < 128 and index not in current, fields
    patch = source / fields[1]
    assert patch.is_file(), patch
    current[index] = patch
# crude.cfg explicitly leaves some effects unmapped. Preserve those omissions
# instead of inventing instrument substitutions.
assert banks["bank"] and banks["drumset"]
# digmid.c: melodic entries are one-based; percussion entries retain MIDI note
# numbers, with begin_multipatch's one-based offset locating the percussion bank.
lines = [f"{index + 1} {path}" for index, path in sorted(banks["bank"].items())]
lines.append("129 begin_multipatch")
lines.extend(f"{index} {path}" for index, path in sorted(banks["drumset"].items()))
lines.append("end_multipatch")
destination.write_text("\n".join(lines) + "\n")

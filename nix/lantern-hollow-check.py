#!/usr/bin/env python3
"""Replay Lantern Hollow headless in the packaged public engine.

Arguments: ENGINE QUEST STAGE
The replay waits for the intro message, dismisses it, walks north into the
hill entrance and stops inside the dungeon. Snapshots must show the quest's
own village and dungeon palettes, not an error screen.
"""

import os
from pathlib import Path
import subprocess
import sys

from PIL import Image

engine, quest, stage = (Path(arg) for arg in sys.argv[1:])
stage.mkdir(parents=True)
for resource in (engine / "share/zquestclassic").iterdir():
    if resource.suffix != ".cfg":
        (stage / resource.name).symlink_to(resource, target_is_directory=resource.is_dir())
(stage / "zc.cfg").write_text(
    "[zeldadx]\nnosound = 1\nfullscreen = 0\nreplay_upload = 0\n"
    "replay_upload_prompt = 1\nclicktofreeze = 0\n"
)
frames = 900
lines = [
    "M version latest",
    f"M qst {quest}",
    f"M frames {frames}",
    "M test_mode false",
    "M sync_rng false",
    "K 0 84 85 82 83 26 24 67 17 23 75 1 19 4 3",
    "R 0 0 1 123",
    "R 0 2 257 456",
    # Dismiss the elder's intro message, then walk north into the hill.
    "D 400 A",
    "U 403 A",
    "D 420 Up",
    "U 820 Up",
    f"Q {frames} 3",
]
(stage / "run.zplay").write_text("\n".join(lines) + "\n")
log = stage / "native.log"
with log.open("w") as out:
    result = subprocess.run(
        [
            "xvfb-run", "-a", "-s", "-screen 0 1240x1080x24",
            str(engine / "bin/zplayer"), "-replay", str(stage / "run.zplay"),
            "-replay-exit-when-done", "-headless", "-snapshot", "300 880",
        ],
        cwd=stage,
        env=dict(os.environ, ZC_DISABLE_CHDIR="1"),
        stdout=out,
        stderr=subprocess.STDOUT,
        timeout=600,
    )
text = log.read_text()
assert result.returncode == 0, f"player exited {result.returncode}\n{text[-2000:]}"
assert "Time to load qst:" in text, "quest did not load"
assert "rng desync" not in text, "replay desynced"
fields = dict(
    line.split(": ", 1)
    for line in (stage / "run.zplay.result.txt").read_text().splitlines()
    if ": " in line
)
assert fields.get("success") == "true" and fields.get("stopped") == "true", fields
assert int(fields["frame"]) == frames, fields


def colours(frame):
    with Image.open(stage / f"run.zplay.{frame}.png") as image:
        return {c for _, c in image.convert("RGB").getcolors(1 << 20)}


village = colours(300)
dungeon = colours(880)
# Kenney Tiny Town grass and Tiny Dungeon wall colours from the quest palette.
assert (132, 198, 105) in village, "village grass colour missing"
assert (192, 203, 220) in dungeon or (139, 155, 180) in dungeon, "dungeon wall colour missing"
assert (132, 198, 105) not in dungeon, "still in the village; hill entrance not reached"
print("Lantern Hollow loaded, played 900 frames and reached the dungeon.")

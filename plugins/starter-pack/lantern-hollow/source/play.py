#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 xvfb-run util-linux
"""Run the PUBLIC player on a quest with a scripted input replay.

play.py <quest.qst> <run-name> <frames> "<snapshot frames>" [events...]
events: "<frame>:<D|U>:<Button>"  e.g. 60:D:Up 120:U:Up
Writes runs/<run-name>/ with PNG snapshots, native.log and result.txt.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
engine = Path((HERE / "player-path.txt").read_text().strip())
quest = Path(sys.argv[1]).resolve()
name, frames = sys.argv[2], int(sys.argv[3])
snaps = sys.argv[4]
events = []
for e in sys.argv[5:]:
    f, kind, btn = e.split(":")
    events.append((int(f), f"{kind} {f} {btn}"))
events.append((frames, f"Q {frames} 3"))

stage = HERE / "runs" / name
shutil.rmtree(stage, ignore_errors=True)
stage.mkdir(parents=True)
for res in (engine / "share/zquestclassic").iterdir():
    if res.suffix != ".cfg":
        (stage / res.name).symlink_to(res, target_is_directory=res.is_dir())
(stage / "zc.cfg").write_text(
    "[zeldadx]\nnosound = 1\nfullscreen = 0\nreplay_upload = 0\n"
    "replay_upload_prompt = 1\nclicktofreeze = 0\n")
start = os.environ.get("START")  # "dmap:screen:retsqr" -> native test mode
meta = ["M test_mode false"]
if start:
    d, s, r = (int(v, 0) for v in start.split(":"))
    meta = ["M test_mode true", f"M starting_dmap {d}", f"M starting_scr {s}",
            f"M starting_retsqr {r}"]
lines = ["M version latest", f"M qst {quest}", f"M frames {frames}"] + meta + [
         "M sync_rng false", "K 0 84 85 82 83 26 24 67 17 23 75 1 19 4 3",
         "R 0 0 1 123", "R 0 2 257 456"]
(stage / "run.zplay").write_text("\n".join(lines + [t for _, t in sorted(events)]) + "\n")
args = ["xvfb-run", "-a", "-s", "-screen 0 1240x1080x24", str(engine / "bin/zplayer"),
        "-replay", str(stage / "run.zplay"), "-replay-exit-when-done", "-headless",
        "-snapshot", snaps]
env = dict(os.environ, ZC_DISABLE_CHDIR="1", LIBGL_ALWAYS_SOFTWARE="1")
with (stage / "native.log").open("w") as log:
    try:
        rc = subprocess.run(args, cwd=stage, env=env, stdout=log, stderr=subprocess.STDOUT,
                            timeout=600, start_new_session=True).returncode
    except subprocess.TimeoutExpired:
        rc = "timeout"
print("exit", rc)
res = stage / "run.zplay.result.txt"
if res.exists():
    print(res.read_text().strip().replace("\n", " | "))
print("snapshots:", sorted(p.name for p in stage.glob("*.png")))

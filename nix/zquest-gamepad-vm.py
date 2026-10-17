#!/usr/bin/env python3
"""Drive the packaged player with virtual Korri seats inside a disposable VM."""

import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from evdev import AbsInfo, UInput, ecodes as e
from PIL import Image

launcher, quest_source = sys.argv[1:]
assert Path("/etc/zquest-gamepad-vm").read_text() == "disposable-vm-only\n"

# The identity and controls of a Korri input seat on the Mini V2:
# /sys/class/input/event8 reports abs=3003f and these eleven buttons.
BUTTONS = [
    e.BTN_A, e.BTN_B, e.BTN_X, e.BTN_Y, e.BTN_TL, e.BTN_TR,
    e.BTN_SELECT, e.BTN_START, e.BTN_MODE, e.BTN_THUMBL, e.BTN_THUMBR,
]
STICK = AbsInfo(0, -32768, 32767, 16, 128, 0)
TRIGGER = AbsInfo(0, 0, 255, 0, 0, 0)
HAT = AbsInfo(0, -1, 1, 0, 0, 0)
AXES = [
    (e.ABS_X, STICK), (e.ABS_Y, STICK), (e.ABS_Z, TRIGGER),
    (e.ABS_RX, STICK), (e.ABS_RY, STICK), (e.ABS_RZ, TRIGGER),
    (e.ABS_HAT0X, HAT), (e.ABS_HAT0Y, HAT),
]


def pad(name):
    return UInput(
        {e.EV_KEY: BUTTONS, e.EV_ABS: AXES},
        name=name, bustype=e.BUS_USB, vendor=0x045E, product=0x028E, version=0x0114,
    )


def allegro_order():
    """Gamepad names in Allegro's order: unsorted /dev/input, evdev nodes only."""
    names = []
    for entry in os.listdir("/dev/input"):
        if entry.startswith("event"):
            names.append(Path(f"/sys/class/input/{entry}/device/name").read_text().strip())
    return [name for name in names if name.startswith(("Korri Seat", "Extra Pad"))]


def settle():
    time.sleep(1.5)  # udev creates the nodes; Allegro rescans on inotify.


seats = {n: pad(f"Korri Seat P{n}") for n in (1, 2, 3, 4)}
settle()
# Reproduce the Mini V2 defect: P1 must not be Allegro's first gamepad. The
# directory order depends on the filesystem, so recreate P1 if it came first.
if allegro_order()[0] == "Korri Seat P1":
    seats[1].close()
    seats[1] = pad("Korri Seat P1")
    settle()
order = allegro_order()
print("Allegro gamepad order:", order, flush=True)
assert len(order) == 4 and order[0] != "Korri Seat P1", order
first = seats[int(order[0][-1])]

root = Path("/tmp/zquest-gamepad")
shutil.rmtree(root, ignore_errors=True)
directory = root / "account"
directory.mkdir(parents=True)
(directory / "zc.cfg").write_text("[zeldadx]\nnosound = 1\nreplay_upload = 0\n")
quest = root / "room.qst"
shutil.copyfile(quest_source, quest)
log = (root / "player.log").open("w")
player = subprocess.Popen([launcher, str(quest), str(directory)], stdout=log, stderr=subprocess.STDOUT)


def screen():
    png = subprocess.check_output(["import", "-window", "root", "png:-"], timeout=10)
    with Image.open(io.BytesIO(png)) as image:
        return image.convert("RGB").tobytes()


def wait_for(test, explanation, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        assert player.poll() is None, f"player exited {player.returncode}: {explanation}"
        if test():
            return
        time.sleep(0.5)
    raise AssertionError(f"timed out: {explanation}")


wait_for(lambda: any((directory / "saves").glob("*.sav")), "native save exists")
window = subprocess.check_output(["xdotool", "search", "--onlyvisible", "--name", "."], text=True).split()[-1]
subprocess.run(["xdotool", "windowfocus", "--sync", window], check=True)
previous = [None]


def stable():
    current = screen()
    same = current == previous[0]
    previous[0] = current
    return same


wait_for(stable, "the generated room is idle")


def press(device, code, value, seconds=0.6):
    device.write(e.EV_ABS, code, value)
    device.syn()
    time.sleep(seconds)
    device.write(e.EV_ABS, code, 0)
    device.syn()
    time.sleep(0.8)


def moves(device, code, value, explanation):
    before = screen()
    press(device, code, value)
    after = screen()
    assert after != before, f"hero did not move: {explanation}"
    print("moved:", explanation, flush=True)


def stays(device, code, value, explanation):
    before = screen()
    press(device, code, value)
    assert screen() == before, f"hero moved: {explanation}"
    print("ignored:", explanation, flush=True)


# Upstream reads gamepad 0, which is P4 here, through its configured stick.
stays(first, e.ABS_X, 32767, f"left stick on Allegro's first gamepad, {order[0]}")
stays(first, e.ABS_HAT0X, 1, f"D-pad on Allegro's first gamepad, {order[0]}")
moves(seats[1], e.ABS_HAT0X, 1, "D-pad right on P1")
moves(seats[1], e.ABS_X, -32768, "left stick left on P1")

# A gamepad added during play shifts Allegro's numbering. The name still wins.
extra = pad("Extra Pad")
settle()
print("Allegro gamepad order:", allegro_order(), flush=True)
stays(extra, e.ABS_HAT0Y, 1, "D-pad on a gamepad added during play")
moves(seats[1], e.ABS_HAT0Y, 1, "D-pad down on P1 after the new gamepad")

# Without P1 the player reads no gamepad, not whichever gamepad is first.
seats[1].close()
settle()
remaining = allegro_order()
print("Allegro gamepad order:", remaining, flush=True)
stays(seats[int(remaining[0][-1])] if remaining[0].startswith("Korri") else extra,
      e.ABS_HAT0Y, -1, f"D-pad on {remaining[0]} while P1 is absent")
seats[1] = pad("Korri Seat P1")
settle()
moves(seats[1], e.ABS_HAT0Y, -1, "D-pad up on P1 after it reconnects")

player.terminate()
player.wait(timeout=20)
print("ZQUEST_GAMEPAD_VM_OK", flush=True)

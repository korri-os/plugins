"""X11 regression client for nested Gamescope (Python stdlib + libX11).

Map a main window, a transient dialog and an override-redirect popup. Move
that popup offscreen, unmap/remap the main window, then destroy and recreate
the only focus window like a launcher handing off to its game. Vary the gap
across frame boundaries to race a new buffer against the host reconfigure.
Without the configure backport, Sway rejects the next buffer with
xdg_surface error 3 (issue #105).
Gamescope without the clipping backport aborts at MOVING_POPUP_OFFSCREEN.
XEVENT 4/5 records button press/release, including touch-to-pointer delivery.
Set X11_LIB to libX11.so.6. Run as the child of gamescope, not against Sway.
"""

import ctypes as C
import os
import time

x = C.CDLL(os.environ["X11_LIB"])
x.XOpenDisplay.restype = C.c_void_p
x.XOpenDisplay.argtypes = [C.c_char_p]
d = x.XOpenDisplay(None)
if not d:
    raise SystemExit("No X display")
# Every Xlib call takes the display pointer first.
for name in [
    "XDefaultRootWindow",
    "XCreateSimpleWindow",
    "XStoreName",
    "XSelectInput",
    "XMapWindow",
    "XFlush",
    "XDestroyWindow",
    "XSetTransientForHint",
    "XChangeWindowAttributes",
    "XPending",
    "XNextEvent",
    "XMoveWindow",
    "XUnmapWindow",
]:
    getattr(x, name).argtypes = [C.c_void_p] + {
        "XDefaultRootWindow": [],
        "XCreateSimpleWindow": [
            C.c_ulong,
            C.c_int,
            C.c_int,
            C.c_uint,
            C.c_uint,
            C.c_uint,
            C.c_ulong,
            C.c_ulong,
        ],
        "XStoreName": [C.c_ulong, C.c_char_p],
        "XSelectInput": [C.c_ulong, C.c_long],
        "XMapWindow": [C.c_ulong],
        "XFlush": [],
        "XDestroyWindow": [C.c_ulong],
        "XSetTransientForHint": [C.c_ulong, C.c_ulong],
        "XChangeWindowAttributes": [C.c_ulong, C.c_ulong, C.c_void_p],
        "XPending": [],
        "XNextEvent": [C.c_void_p],
        "XMoveWindow": [C.c_ulong, C.c_int, C.c_int],
        "XUnmapWindow": [C.c_ulong],
    }[name]
x.XDefaultRootWindow.restype = C.c_ulong
x.XCreateSimpleWindow.restype = C.c_ulong
root = x.XDefaultRootWindow(d)


def window(name, w, h, color):
    win = x.XCreateSimpleWindow(d, root, 30, 30, w, h, 0, 0, color)
    x.XStoreName(d, win, name.encode())
    x.XSelectInput(d, win, (1 << 2) | (1 << 3) | (1 << 6) | (1 << 17))
    return win


main = window("Gamescope multi-window repro", 640, 480, 0x225577)
x.XMapWindow(d, main)
x.XFlush(d)
time.sleep(3)
dialog = window("Transient dialog", 320, 180, 0x447722)
x.XSetTransientForHint(d, dialog, main)
x.XMapWindow(d, dialog)
x.XFlush(d)
time.sleep(3)


# XSetWindowAttributes from Xlib.h; ctypes preserves the native ABI alignment.
class Attributes(C.Structure):
    _fields_ = [
        ("background_pixmap", C.c_ulong),
        ("background_pixel", C.c_ulong),
        ("border_pixmap", C.c_ulong),
        ("border_pixel", C.c_ulong),
        ("bit_gravity", C.c_int),
        ("win_gravity", C.c_int),
        ("backing_store", C.c_int),
        ("backing_planes", C.c_ulong),
        ("backing_pixel", C.c_ulong),
        ("save_under", C.c_int),
        ("event_mask", C.c_long),
        ("do_not_propagate_mask", C.c_long),
        ("override_redirect", C.c_int),
        ("colormap", C.c_ulong),
        ("cursor", C.c_ulong),
    ]


popup = window("Override redirect popup", 160, 90, 0x884422)
a = Attributes()
a.override_redirect = 1
x.XChangeWindowAttributes(d, popup, 1 << 9, C.byref(a))
x.XMapWindow(d, popup)
x.XFlush(d)
print("ALL_WINDOWS_MAPPED", flush=True)
event = (C.c_long * 24)()
for i in range(100):
    while x.XPending(d):
        x.XNextEvent(d, C.byref(event))
        print("XEVENT", C.cast(event, C.POINTER(C.c_int))[0], flush=True)
    if i == 30:
        print("MOVING_POPUP_OFFSCREEN", flush=True)
        x.XMoveWindow(d, popup, 2000, 2000)
        x.XFlush(d)
    if i == 60:
        x.XDestroyWindow(d, dialog)
        x.XDestroyWindow(d, popup)
        x.XFlush(d)
    time.sleep(0.1)
for cycle in range(20):
    print("UNMAP_REMAP_MAIN", cycle + 1, flush=True)
    x.XUnmapWindow(d, main)
    x.XFlush(d)
    time.sleep(0.05)
    x.XMapWindow(d, main)
    x.XFlush(d)
    time.sleep(0.1)
for cycle in range(25):
    print("DESTROY_MAIN", cycle + 1, flush=True)
    x.XDestroyWindow(d, main)
    x.XFlush(d)
    # Destroy the focus window like a launcher handing off to its game.
    # Unmapping alone can leave the old focus/held commit alive in Gamescope.
    time.sleep((0.02, 0.04, 0.08, 0.16, 0.32)[cycle % 5])
    main = window("Gamescope recreated game window", 640, 480, 0x225577)
    x.XMapWindow(d, main)
    x.XFlush(d)
    time.sleep(1)
    print("RECREATE_COMPLETE", cycle + 1, flush=True)
print("REPRO_COMPLETE", flush=True)

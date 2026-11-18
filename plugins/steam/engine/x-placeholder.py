# Keep one 1x1 black X window mapped on gamescope's Xwayland for the whole
# engine session (spike FINDINGS.md section 9; steam-engine-session runs it in
# the Steam FHS, which has libX11).
#
# Why: gamescope's Wayland backend unmaps its sway toplevel (attaches a NULL
# buffer) whenever it has no focus window, and maps it again when one appears.
# wlroots drops every pending xdg_surface configure on that unmap. If sway's
# configure for the fresh map is still unread when gamescope unmaps, gamescope
# later acks a serial wlroots no longer has: "wrong configure serial", posted
# as xdg_wm_base error 4, and gamescope 3.16.31 aborts in its input thread.
# Without Valve's client, the first X windows in gamescope are Proton's and the
# game's start-up windows, which can map and vanish within milliseconds. A
# permanent window keeps the toplevel mapped, so it never unmaps mid-configure.
#
# gamescope ranks a 1x1 window below every other window (win_is_useless), so
# it never takes focus from a game window. Uses only libX11 through ctypes.
# It ends with the session program (PR_SET_PDEATHSIG) or with Xwayland.
import ctypes
import os
import signal
import sys

PR_SET_PDEATHSIG = 1


def main() -> int:
    if not os.environ.get("DISPLAY"):
        print("x-placeholder: DISPLAY is not set", file=sys.stderr)
        return 0
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)
    x = ctypes.CDLL("libX11.so.6")
    x.XOpenDisplay.restype = ctypes.c_void_p
    x.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x.XDefaultScreen.argtypes = [ctypes.c_void_p]
    x.XRootWindow.restype = ctypes.c_ulong
    x.XRootWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    x.XBlackPixel.restype = ctypes.c_ulong
    x.XBlackPixel.argtypes = [ctypes.c_void_p, ctypes.c_int]
    x.XCreateSimpleWindow.restype = ctypes.c_ulong
    x.XCreateSimpleWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong, ctypes.c_ulong]
    x.XStoreName.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_char_p]
    x.XMapWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x.XFlush.argtypes = [ctypes.c_void_p]
    x.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    dpy = x.XOpenDisplay(None)
    if not dpy:
        print("x-placeholder: cannot open DISPLAY", file=sys.stderr)
        return 1
    screen = x.XDefaultScreen(dpy)
    black = x.XBlackPixel(dpy, screen)
    win = x.XCreateSimpleWindow(dpy, x.XRootWindow(dpy, screen), 0, 0, 1, 1, 0, black, black)
    x.XStoreName(dpy, win, b"korri-steam-placeholder")
    x.XMapWindow(dpy, win)
    x.XFlush(dpy)
    print(f"x-placeholder: mapped window 0x{win:x} on {os.environ['DISPLAY']}", file=sys.stderr, flush=True)
    # No event mask is selected; this only blocks. Xlib exits the process when
    # gamescope's X server goes away, and SIGTERM ends it with the shim.
    event = ctypes.create_string_buffer(256)
    while True:
        x.XNextEvent(dpy, event)


if __name__ == "__main__":
    sys.exit(main())

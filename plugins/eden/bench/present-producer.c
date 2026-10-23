/* Native integration producer; deliberately has no _NET_WM_PID property. */
#include <X11/Xlib.h>
#include <X11/extensions/Xpresent.h>
#include <signal.h>
#include <stdio.h>
#include <time.h>

static volatile sig_atomic_t stop;
static void interrupted(int number) { (void)number; stop = 1; }
int main(void) {
    Display *display = XOpenDisplay(NULL);
    if (!display) return 1;
    int screen = DefaultScreen(display);
    Window window = XCreateSimpleWindow(display, RootWindow(display, screen),
        0, 0, 320, 240, 0, 0, WhitePixel(display, screen));
    Pixmap pixels = XCreatePixmap(display, window, 320, 240, DefaultDepth(display, screen));
    GC brush = XCreateGC(display, pixels, 0, NULL);
    XSetForeground(display, brush, WhitePixel(display, screen));
    XFillRectangle(display, pixels, brush, 0, 0, 320, 240);
    XMapWindow(display, window);
    XSync(display, False);
    printf("%lu\n", window); fflush(stdout);
    signal(SIGINT, interrupted); signal(SIGTERM, interrupted);
    unsigned serial = 0;
    const struct timespec delay = {0, 16666667};
    while (!stop) {
        XPresentPixmap(display, window, pixels, ++serial, 0, 0, 0, 0, 0,
                       0, 0, 0, 0, 0, 0, NULL, 0);
        XFlush(display);
        nanosleep(&delay, NULL);
    }
    XDestroyWindow(display, window);
    XCloseDisplay(display);
    return 0;
}

/* Read-only Xlib observer. Server-owned XRes PID selects renderer windows.
 * It counts Pixmap CompleteNotify, not display refresh or Present NotifyMSC.
 */
#include <sys/types.h>
#include <X11/Xlib.h>
#include <X11/extensions/XRes.h>
#include <X11/extensions/Xpresent.h>
#include <errno.h>
#include <inttypes.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t done;
static int xerror;
static void interrupted(int number) { (void)number; done = 1; }
static int record_error(Display *display, XErrorEvent *error) {
    (void)display; xerror = error->error_code; return 0;
}
static uint64_t monotonic_us(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (uint64_t)now.tv_sec * 1000000 + (uint64_t)now.tv_nsec / 1000;
}

struct watch { Window window; XID subscription; };
static struct watch watches[4096];
static size_t used;

static int renderer_owns(Display *display, Window window, pid_t renderer) {
    XResClientIdSpec request = {window, XRES_CLIENT_ID_PID_MASK};
    XResClientIdValue *identities = NULL;
    long count = 0;
    int match = 0;
    /* This XRes function returns X11 Success (zero), unlike QueryVersion. */
    if (XResQueryClientIds(display, 1, &request, &count, &identities) == Success) {
        for (long i = 0; i < count; i++)
            if (XResGetClientPid(&identities[i]) == renderer) match = 1;
        XResClientIdsDestroy(count, identities);
    }
    return match;
}

static void inspect_tree(Display *display, Window window, pid_t renderer, unsigned depth) {
    if (depth > 24 || used == 4096) return;
    size_t i;
    for (i = 0; i < used && watches[i].window != window; i++) {}
    if (i == used && renderer_owns(display, window, renderer)) {
        xerror = 0;
        XID subscription = XPresentSelectInput(display, window, PresentCompleteNotifyMask);
        XSelectInput(display, window, StructureNotifyMask);
        XSync(display, False);
        if (!xerror) {
            watches[used++] = (struct watch){window, subscription};
            fprintf(stderr, "XRes renderer=%ld window=%lu\n", (long)renderer, window);
        }
    }
    Window root, parent, *children = NULL;
    unsigned count = 0;
    if (XQueryTree(display, window, &root, &parent, &children, &count))
        for (unsigned child = 0; child < count; child++)
            inspect_tree(display, children[child], renderer, depth + 1);
    if (children) XFree(children);
}

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: present-observer RENDERER_NAMESPACE_PID\n"); return 2; }
    char *tail;
    long parsed = strtol(argv[1], &tail, 10);
    if (!argv[1][0] || *tail || parsed <= 0 || parsed > 2147483647) return 2;
    Display *display = XOpenDisplay(NULL);
    if (!display) { fprintf(stderr, "Cannot connect to renderer Xwayland\n"); return 1; }
    XSetErrorHandler(record_error);
    int opcode, event_base, error_base, major = 1, minor = 2;
    if (!XPresentQueryExtension(display, &opcode, &event_base, &error_base) ||
        !XPresentQueryVersion(display, &major, &minor)) return 1;
    int res_major, res_minor;
    if (!XResQueryVersion(display, &res_major, &res_minor) ||
        res_major < 1 || (res_major == 1 && res_minor < 2)) {
        fprintf(stderr, "XRes 1.2 PID authority unavailable\n"); return 1;
    }
    fprintf(stderr, "Present %d.%d; XRes %d.%d\n", major, minor, res_major, res_minor);
    signal(SIGTERM, interrupted); signal(SIGINT, interrupted);
    setvbuf(stdout, NULL, _IOLBF, 0);
    puts("event,ust_us,window,mode");
    uint64_t next_scan = 0;
    while (!done) {
        uint64_t now = monotonic_us();
        if (now >= next_scan) {
            for (int screen = 0; screen < ScreenCount(display); screen++)
                inspect_tree(display, RootWindow(display, screen), (pid_t)parsed, 0);
            XFlush(display);
            next_scan = now + 500000;
        }
        while (XPending(display)) {
            XEvent event;
            XNextEvent(display, &event);
            if (event.type == DestroyNotify) {
                Window window = event.xdestroywindow.window;
                for (size_t i = 0; i < used; i++) {
                    if (watches[i].window == window) {
                        printf("destroy,%" PRIu64 ",%lu,0\n", monotonic_us(), window);
                        watches[i] = watches[--used];
                        break;
                    }
                }
            } else if (event.type == GenericEvent && event.xcookie.extension == opcode &&
                       XGetEventData(display, &event.xcookie)) {
                if (event.xcookie.evtype == PresentCompleteNotify) {
                    XPresentCompleteNotifyEvent *frame = event.xcookie.data;
                    if (frame->kind == PresentCompleteKindPixmap)
                        printf("frame,%" PRIu64 ",%lu,%u\n", frame->ust, frame->window, frame->mode);
                }
                XFreeEventData(display, &event.xcookie);
            }
        }
        struct pollfd fd = {ConnectionNumber(display), POLLIN, 0};
        if (poll(&fd, 1, 50) < 0 && errno != EINTR) return 1;
        if (fd.revents & (POLLERR | POLLHUP | POLLNVAL)) return 1;
    }
    XCloseDisplay(display);
    return 0;
}

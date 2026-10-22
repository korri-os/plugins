/* Observe X Present CompleteNotify on one game's Xwayland windows.
 * No injection, grabs, graphics layer, polling of image pixels, or frame repeats.
 */
#include <xcb/xcb.h>
#include <xcb/present.h>
#include <errno.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static volatile sig_atomic_t running = 1;
static void stop(int sig) { (void)sig; running = 0; }
static xcb_connection_t *connection;
static xcb_atom_t pid_atom;
static uint32_t pid;
static xcb_window_t selected[8192];
static size_t count;

static bool owned(xcb_window_t window, bool inherited) {
    xcb_get_property_reply_t *reply = xcb_get_property_reply(connection,
        xcb_get_property(connection, 0, window, pid_atom, XCB_ATOM_CARDINAL, 0, 1), NULL);
    bool result = inherited;
    if (reply && xcb_get_property_value_length(reply) == 4)
        result = *(uint32_t *)xcb_get_property_value(reply) == pid;
    free(reply);
    return result;
}

static void discover(xcb_window_t window, bool inherited, unsigned depth) {
    if (depth > 12 || count == 8192) return;
    bool matches = owned(window, inherited);
    if (matches) {
        bool seen = false;
        for (size_t i = 0; i < count; ++i) if (selected[i] == window) seen = true;
        if (!seen) {
            xcb_generic_error_t *error = xcb_request_check(connection,
                xcb_present_select_input_checked(connection, xcb_generate_id(connection),
                    window, XCB_PRESENT_EVENT_MASK_COMPLETE_NOTIFY));
            if (!error) {
                selected[count++] = window;
                fprintf(stderr, "watch window=%u pid=%u\n", window, pid);
            }
            free(error);
        }
    }
    xcb_query_tree_reply_t *tree = xcb_query_tree_reply(connection, xcb_query_tree(connection, window), NULL);
    if (!tree) return;
    xcb_window_t *children = xcb_query_tree_children(tree);
    for (int i = 0; i < xcb_query_tree_children_length(tree); ++i)
        discover(children[i], matches, depth + 1);
    free(tree);
}

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: present-watch GAME_PID (uses DISPLAY)\n"); return 2; }
    char *end;
    unsigned long parsed = strtoul(argv[1], &end, 10);
    if (*end || !parsed || parsed > UINT32_MAX) return 2;
    pid = (uint32_t)parsed;
    signal(SIGINT, stop); signal(SIGTERM, stop);
    connection = xcb_connect(NULL, NULL);
    if (xcb_connection_has_error(connection)) { fprintf(stderr, "Cannot open DISPLAY\n"); return 1; }
    const xcb_query_extension_reply_t *extension = xcb_get_extension_data(connection, &xcb_present_id);
    if (!extension || !extension->present) { fprintf(stderr, "X Present unavailable\n"); return 1; }
    xcb_present_query_version_reply_t *version = xcb_present_query_version_reply(connection,
        xcb_present_query_version(connection, 1, 2), NULL);
    if (!version) return 1;
    fprintf(stderr, "X Present %u.%u\n", version->major_version, version->minor_version);
    free(version);
    xcb_intern_atom_reply_t *atom = xcb_intern_atom_reply(connection,
        xcb_intern_atom(connection, 0, 11, "_NET_WM_PID"), NULL);
    if (!atom) return 1;
    pid_atom = atom->atom; free(atom);
    puts("monotonic_s,window,ust_us,msc,mode"); fflush(stdout);
    time_t last = 0;
    while (running && !xcb_connection_has_error(connection)) {
        time_t now = time(NULL);
        if (now != last) {
            xcb_screen_iterator_t screens = xcb_setup_roots_iterator(xcb_get_setup(connection));
            while (screens.rem) { discover(screens.data->root, false, 0); xcb_screen_next(&screens); }
            xcb_flush(connection); last = now;
        }
        xcb_generic_event_t *event;
        while ((event = xcb_poll_for_event(connection))) {
            if ((event->response_type & 0x7f) == XCB_GE_GENERIC) {
                xcb_present_complete_notify_event_t *complete = (void *)event;
                if (complete->extension == extension->major_opcode &&
                    complete->event_type == XCB_PRESENT_COMPLETE_NOTIFY &&
                    complete->kind == XCB_PRESENT_COMPLETE_KIND_PIXMAP) {
                    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
                    printf("%.9f,%u,%llu,%llu,%u\n", ts.tv_sec + ts.tv_nsec / 1e9,
                        complete->window, (unsigned long long)complete->ust,
                        (unsigned long long)complete->msc, complete->mode);
                    fflush(stdout);
                }
            }
            free(event);
        }
        struct pollfd fd = { .fd = xcb_get_file_descriptor(connection), .events = POLLIN };
        if (poll(&fd, 1, 100) < 0 && errno != EINTR) break;
    }
    bool failed = xcb_connection_has_error(connection);
    xcb_disconnect(connection);
    return failed ? 1 : 0;
}

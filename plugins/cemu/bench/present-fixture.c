/* A real Present producer for the observer's integration check. Intentionally
 * omits _NET_WM_PID, so the check exercises XRes server-owned PID resolution. */
#include <xcb/xcb.h>
#include <xcb/present.h>
#include <signal.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

static volatile sig_atomic_t running = 1;
static void stop(int sig) { (void)sig; running = 0; }
int main(void) {
    signal(SIGTERM, stop);
    xcb_connection_t *c = xcb_connect(NULL, NULL);
    if (xcb_connection_has_error(c)) return 1;
    xcb_screen_t *screen = xcb_setup_roots_iterator(xcb_get_setup(c)).data;
    xcb_window_t win = xcb_generate_id(c);
    xcb_create_window(c, screen->root_depth, win, screen->root, 0, 0, 300, 150, 0,
        XCB_WINDOW_CLASS_INPUT_OUTPUT, screen->root_visual, 0, NULL);
    xcb_map_window(c, win);
    xcb_present_query_version_reply_t *version = xcb_present_query_version_reply(c,
        xcb_present_query_version(c, 1, 2), NULL);
    if (!version) return 1;
    free(version);
    xcb_pixmap_t pixmaps[2] = { xcb_generate_id(c), xcb_generate_id(c) };
    xcb_gcontext_t gc = xcb_generate_id(c);
    xcb_create_gc(c, gc, win, 0, NULL);
    for (uint32_t i = 0; i < 2; ++i) {
        xcb_create_pixmap(c, screen->root_depth, pixmaps[i], win, 300, 150);
        uint32_t color = i ? 0x00ffffff : 0;
        xcb_change_gc(c, gc, XCB_GC_FOREGROUND, &color);
        xcb_rectangle_t rect = {0, 0, 300, 150};
        xcb_poly_fill_rectangle(c, pixmaps[i], gc, 1, &rect);
    }
    struct timespec interval = { .tv_nsec = 33333333 };
    for (uint32_t serial = 0; running; ++serial) {
        xcb_present_pixmap(c, win, pixmaps[serial % 2], serial, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, NULL);
        xcb_flush(c);
        nanosleep(&interval, NULL);
    }
    xcb_disconnect(c);
    return 0;
}

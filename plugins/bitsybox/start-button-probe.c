/* Test-only SDL event producer. Never included in shipping outputs. */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <SDL.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

static void *send_start(void *unused) {
    (void)unused;
    /* Core's launcher also inherits LD_PRELOAD. Only its native SDL child
     * creates a window, so never inject into the launcher itself. */
    Uint32 (*was_init)(Uint32) = dlsym(RTLD_DEFAULT, "SDL_WasInit");
    void (*delay)(Uint32) = dlsym(RTLD_DEFAULT, "SDL_Delay");
    int (*push_event)(SDL_Event *) = dlsym(RTLD_DEFAULT, "SDL_PushEvent");
    if (!was_init || !delay || !push_event) return NULL;
    const char *trigger = getenv("KORRI_TEST_START_TRIGGER");
    if (!trigger) return NULL;
    for (int attempt = 0; attempt < 1500; attempt++) {
        if (access(trigger, F_OK) == 0 && was_init(SDL_INIT_VIDEO)) {
            for (int pressed = 1; pressed >= 0; pressed--) {
                SDL_Event event;
                memset(&event, 0, sizeof(event));
                event.type = pressed ? SDL_CONTROLLERBUTTONDOWN : SDL_CONTROLLERBUTTONUP;
                event.cbutton.button = SDL_CONTROLLER_BUTTON_START;
                event.cbutton.state = pressed ? SDL_PRESSED : SDL_RELEASED;
                if (push_event(&event) != 1) return NULL;
                fprintf(stderr, "BITSY_TEST_START_%s\n", pressed ? "DOWN" : "UP");
                fflush(stderr);
                delay(250);
            }
            return NULL;
        }
        delay(10);
    }
    return NULL;
}

__attribute__((constructor)) static void start_probe(void) {
    pthread_t thread;
    if (pthread_create(&thread, NULL, send_start, NULL) == 0) pthread_detach(thread);
}

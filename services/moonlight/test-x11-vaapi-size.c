// Exercise the real X11 presentation handler against a real, resizable window.
// The VA-API sink records its destination rectangle; no GPU is required in CI.
#include "video/x11.c"
#include <assert.h>

static int presented_width;
static int presented_height;
static int presentations;
enum decoders ffmpeg_decoder = VAAPI;

void vaapi_queue(AVFrame* frame, Window target, int width, int height) {
  assert(frame);
  assert(target == window);
  presented_width = width;
  presented_height = height;
  presentations++;
}

static void present_at(AVFrame* frame, int width, int height) {
  XResizeWindow(display, window, width, height);
  XSync(display, False);
  int before = presentations;
  assert(write(pipefd[1], &frame, sizeof(frame)) == sizeof(frame));
  assert(frame_handle(pipefd[0]) == LOOP_OK);
  assert(presentations == before + 1);
  assert(presented_width == width);
  assert(presented_height == height);
}

int main(void) {
  display = XOpenDisplay(NULL);
  assert(display);
  window = XCreateSimpleWindow(display, DefaultRootWindow(display),
                               0, 0, 1920, 1080, 0, 0, 0);
  XMapWindow(display, window);
  XSync(display, False);
  assert(pipe(pipefd) == 0);
  assert(fcntl(pipefd[0], F_SETFL, O_NONBLOCK) == 0);

  AVFrame frame = {.width = 1920, .height = 1080};
  // The windowed setup starts with stream dimensions. Korri's compositor then
  // expands that same window to the output, without changing decoded frames.
  display_width = frame.width;
  display_height = frame.height;
  present_at(&frame, 3840, 2160);
  assert(frame.width == 1920 && frame.height == 1080);
  present_at(&frame, 1537, 865);

  // A stream larger than the output must scale down, not be clipped.
  frame.width = display_width = 3840;
  frame.height = display_height = 2160;
  present_at(&frame, 1280, 720);
  present_at(&frame, 1920, 1080);

  close(pipefd[0]);
  close(pipefd[1]);
  XDestroyWindow(display, window);
  XCloseDisplay(display);
  puts("VA-API presentation follows actual X11 window geometry across resizes");
}

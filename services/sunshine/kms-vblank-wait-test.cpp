#include "kms_vblank_wait.h"

#include <cassert>
#include <cstdio>
#include <fcntl.h>
#include <signal.h>
#include <sys/time.h>

int main() {
  using namespace platf::kms;
  int fds[2];
  assert(pipe2(fds, O_NONBLOCK | O_CLOEXEC) == 0);
  // Real poll/read timeout: no vblanks arrive, as when a panel turns off.
  struct sigaction action {};
  action.sa_handler = [](int) {
  };
  assert(sigaction(SIGALRM, &action, nullptr) == 0);
  itimerval timer {{0, 1000}, {0, 1000}};
  assert(setitimer(ITIMER_REAL, &timer, nullptr) == 0);
  auto start = std::chrono::steady_clock::now();
  assert(!wait_vblank_event(fds[0], 1, start + vblank_wait_timeout));
  assert(errno == ETIMEDOUT);
  auto elapsed = std::chrono::steady_clock::now() - start;
  assert(elapsed >= vblank_wait_timeout && elapsed < std::chrono::seconds(2));
  timer = {};
  assert(setitimer(ITIMER_REAL, &timer, nullptr) == 0);
  drm_event_vblank events[2] {};
  for (auto &event : events) {
    event.base.type = DRM_EVENT_VBLANK;
    event.base.length = sizeof(event);
    event.tv_sec = 17;
    event.tv_usec = 42;
    event.sequence = 99;
  }
  events[0].user_data = 1;  // A stale completion cannot satisfy a new request.
  events[1].user_data = 2;
  assert(write(fds[1], events, sizeof(events)) == sizeof(events));
  auto event = wait_vblank_event(fds[0], 2, std::chrono::steady_clock::now() + vblank_wait_timeout);
  assert(event && event->sequence == 99 && event->tv_usec == 42);
  assert(!wait_vblank_event(fds[0], 3, std::chrono::steady_clock::now() + std::chrono::milliseconds(2)));
  assert(errno == ETIMEDOUT);
  close(fds[0]);
  close(fds[1]);
  std::puts("PASS bounded vblank poll timeout under signals, missing event, stale cookie, event timestamp and sequence");
}

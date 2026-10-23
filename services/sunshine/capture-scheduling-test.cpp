#include "capture_scheduling.h"

#include <cassert>
#include <cstdio>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

int main() {
  for (auto value : {"", "-1", "+15", "21", "99", "15:15", "infinity", "15ms", "1.5", " 15", "15 ", "999999999999999999999"}) {
    assert(!video::parse_capture_rt_priority(value));
  }
  assert(video::parse_capture_rt_priority("0") == 0);
  assert(video::parse_capture_rt_priority("1") == 1);
  assert(video::parse_capture_rt_priority("15") == 15);
  assert(video::parse_capture_rt_priority("20") == 20);
  auto policy = sched_getscheduler(0);
  using video::capture_backend;
  // Positive config does not authorize any non-RAM backend, even with no
  // pacing sleeps (100 slow VRAM snapshots at 60Hz).
  for (int snapshot = 0; snapshot < 100; ++snapshot) {
    for (int priority = 1; priority <= 20; ++priority) {
      assert(video::request_capture_scheduling(priority, capture_backend::other, true) == 0);
    }
    assert(sched_getscheduler(0) == policy);
  }
  assert(video::request_capture_scheduling(5, capture_backend::guarded_ram_kms, false) == 0);

  assert(video::request_capture_scheduling(5) == 0);
  assert(video::request_capture_scheduling(0) == 0);
  assert(sched_getscheduler(0) == policy);
  assert(video::request_capture_scheduling(-1, capture_backend::guarded_ram_kms, true) == EINVAL);
  assert(video::request_capture_scheduling(21, capture_backend::guarded_ram_kms, true) == EINVAL);
  auto child = fork();
  assert(child >= 0);
  if (!child) {
    rlimit limit {0, 0};
    assert(setrlimit(RLIMIT_RTPRIO, &limit) == 0);
    assert(video::request_capture_scheduling(15, capture_backend::guarded_ram_kms, true) == EPERM);
    assert(sched_getscheduler(0) == policy);
    _exit(0);
  }
  int status;
  assert(waitpid(child, &status, 0) == child);
  assert(WIFEXITED(status) && WEXITSTATUS(status) == 0);
  assert(sched_getscheduler(0) == policy);
  std::puts("PASS FIFO scope excludes other and unlocked backends, parsing, invalid bounds, EPERM continuation, caller policy unchanged");
}

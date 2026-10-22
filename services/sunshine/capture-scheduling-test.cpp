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
  assert(video::request_capture_scheduling(0) == 0);
  assert(sched_getscheduler(0) == policy);
  assert(video::request_capture_scheduling(-1) == EINVAL);
  assert(video::request_capture_scheduling(21) == EINVAL);
  auto child = fork();
  assert(child >= 0);
  if (!child) {
    rlimit limit {0, 0};
    assert(setrlimit(RLIMIT_RTPRIO, &limit) == 0);
    assert(video::request_capture_scheduling(15) == EPERM);
    assert(sched_getscheduler(0) == policy);
    _exit(0);
  }
  int status;
  assert(waitpid(child, &status, 0) == child);
  assert(WIFEXITED(status) && WEXITSTATUS(status) == 0);
  assert(sched_getscheduler(0) == policy);
  std::puts("PASS capture FIFO parsing, default off, invalid bounds, EPERM continuation, caller policy unchanged");
}

#include "kms_capture_rt_guard.h"

#include <cassert>
#include <chrono>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <limits>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

namespace {
  std::int64_t clock_ns(clockid_t clock) {
    timespec value {};
    assert(clock_gettime(clock, &value) == 0);
    return std::int64_t(value.tv_sec) * 1000000000 + value.tv_nsec;
  }

  void busy_for(std::chrono::nanoseconds duration) {
    auto began = clock_ns(CLOCK_THREAD_CPUTIME_ID);
    while (clock_ns(CLOCK_THREAD_CPUTIME_ID) - began < duration.count()) {}
  }
}  // namespace

int main(int argc, char **argv) {
  using namespace platf::kms;
  using namespace std::chrono_literals;
  capture_pacing_history_t normal, slow, spin, repeated, backwards, wrap, fallback;
  for (std::uint32_t sequence = 1; sequence < 100; ++sequence) {
    assert(normal.observe(1, sequence) == capture_rt_guard_reason::none);
    assert(slow.observe(1, sequence + sequence / 4) == capture_rt_guard_reason::none);
    assert(fallback.observe(1, {}) == capture_rt_guard_reason::none);
  }
  assert(spin.observe(0, 1) == capture_rt_guard_reason::none);
  assert(spin.observe(0, 2) == capture_rt_guard_reason::none);
  assert(spin.observe(0, 3) == capture_rt_guard_reason::no_pacing_calls);
  assert(repeated.observe(1, 7) == capture_rt_guard_reason::none);
  assert(repeated.observe(1, 7) == capture_rt_guard_reason::none);
  assert(repeated.observe(1, 7) == capture_rt_guard_reason::repeated_sequence);
  assert(backwards.observe(1, 100) == capture_rt_guard_reason::none);
  assert(backwards.observe(1, 99) == capture_rt_guard_reason::backwards_sequence);
  assert(wrap.observe(1, std::numeric_limits<std::uint32_t>::max()) == capture_rt_guard_reason::none);
  assert(wrap.observe(1, 0) == capture_rt_guard_reason::none);
  auto initial = sched_getscheduler(0) & ~SCHED_RESET_ON_FORK;
  assert(initial == SCHED_OTHER || initial == SCHED_BATCH || initial == SCHED_IDLE);
  capture_rt_guard_t ordinary;
  ordinary.begin_pacing();
  assert(ordinary.before_acquisition(1ms, 0, {}) == capture_rt_guard_result::ready);
  if (argc == 2 && std::strcmp(argv[1], "--require-rt") == 0) {
    sched_param fifo {.sched_priority = 5};
    sched_param other {};
    assert(sched_setscheduler(0, SCHED_FIFO | SCHED_RESET_ON_FORK, &fifo) == 0);
    capture_rt_guard_t unpaced;
    for (unsigned frame = 0; frame < 3; ++frame) {
      unpaced.begin_pacing();
      auto result = unpaced.before_acquisition(1ms, 0, frame);
      assert(result == (frame == 2 ? capture_rt_guard_result::degraded : capture_rt_guard_result::ready));
      unpaced.acquisition_complete();
    }
    assert(unpaced.reason_code() == capture_rt_guard_reason::no_pacing_calls);
    assert((sched_getscheduler(0) & ~SCHED_RESET_ON_FORK) == SCHED_OTHER);
    assert(sched_getscheduler(0) & SCHED_RESET_ON_FORK);
    assert(sched_setscheduler(0, SCHED_FIFO | SCHED_RESET_ON_FORK, &fifo) == 0);
    capture_rt_guard_t paced;
    auto normal_wall = clock_ns(CLOCK_MONOTONIC), normal_cpu = clock_ns(CLOCK_THREAD_CPUTIME_ID);
    for (unsigned frame = 0; frame < 20; ++frame) {
      busy_for(10ms);
      paced.begin_pacing();
      // A real pacing sleep call whose deadline already passed returns at once.
      timespec passed {};
      assert(clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &passed, nullptr) == 0);
      assert(paced.before_acquisition(1ms, 1, frame + frame / 4) == capture_rt_guard_result::ready);
      paced.acquisition_complete();
      assert((sched_getscheduler(0) & ~SCHED_RESET_ON_FORK) == SCHED_FIFO);
    }
    normal_wall = clock_ns(CLOCK_MONOTONIC) - normal_wall;
    normal_cpu = clock_ns(CLOCK_THREAD_CPUTIME_ID) - normal_cpu;
    std::printf("NORMAL_PACED cpu_ns=%lld wall_ns=%lld share=%.3f policy=FIFO5\n", static_cast<long long>(normal_cpu), static_cast<long long>(normal_wall), double(normal_cpu) / normal_wall);
    assert(sched_setscheduler(0, SCHED_OTHER | SCHED_RESET_ON_FORK, &other) == 0);
    pid_t child = fork();
    assert(child >= 0);
    if (child == 0) {
      assert(sched_setscheduler(0, SCHED_FIFO | SCHED_RESET_ON_FORK, &fifo) == 0);
      sock_filter filters[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(seccomp_data, nr)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, SYS_sched_setscheduler, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)
      };
      sock_fprog program {static_cast<unsigned short>(sizeof(filters) / sizeof(filters[0])), filters};
      assert(prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) == 0);
      assert(prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program) == 0);
      capture_rt_guard_t denied;
      for (unsigned frame = 0; frame < 3; ++frame) {
        denied.begin_pacing();
        auto result = denied.before_acquisition(1ms, 0, frame);
        assert(result == (frame == 2 ? capture_rt_guard_result::sleep_only : capture_rt_guard_result::ready));
        denied.acquisition_complete();
      }
      assert(denied.error() == EPERM);
      for (int attempt = 0; attempt < 3; ++attempt) {
        rusage before {}, after {};
        assert(getrusage(RUSAGE_THREAD, &before) == 0);
        auto started = std::chrono::steady_clock::now();
        assert(denied.before_acquisition(1ms, 0, {}) == capture_rt_guard_result::sleep_only);
        assert(std::chrono::steady_clock::now() - started >= 1ms);
        assert(getrusage(RUSAGE_THREAD, &after) == 0);
        assert(after.ru_nvcsw > before.ru_nvcsw);
      }
      _exit(0);
    }
    int status = 0;
    assert(waitpid(child, &status, 0) == child);
    assert(WIFEXITED(status) && WEXITSTATUS(status) == 0);
  }
  std::puts("PASS actual call/sequence guard: normal, passed deadline, slow, fallback, spin, re-read, backwards, wrap; unprivileged demotion and denied sleep-only fallback");
}

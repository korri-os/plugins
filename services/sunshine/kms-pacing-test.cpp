#include "kms_capture_pacing.h"

#include <cassert>
#include <cstdio>
#include <limits>

int main() {
  using namespace platf::kms;
  assert(default_vblank_offset_ms == 0);
  for (auto value : {"", "-1", "+12", "12ms", "12.0", " 12", "12 ", "1001", "999999999999999999999"}) {
    assert(!parse_vblank_offset_ms(value));
  }
  assert(parse_vblank_offset_ms("0") == 0);
  assert(parse_vblank_offset_ms("12") == 12);
  assert(parse_vblank_offset_ms("1000") == 1000);
  assert(mode_period_ns(24000, 800, 500, false, false, 0) == 16666666);
  assert(mode_period_ns(24000, 800, 500, true, false, 0) == 8333333);
  assert(mode_period_ns(24000, 800, 500, false, true, 0) == 33333333);
  assert(mode_period_ns(24000, 800, 500, false, false, 2) == 33333333);
  assert(!mode_period_ns(0, 800, 500, false, false, 0));
  assert(!mode_period_ns(24000, 0, 500, false, false, 0));
  assert(!mode_period_ns(24000, 800, 0, false, false, 0));
  assert(!mode_period_ns(1, 65535, 65535, false, true, 65535));
  assert(compatible_vblank_period(16666035, 16666666, 12000000));
  assert(compatible_vblank_period(16668000, 16666666, 12000000));
  assert(!compatible_vblank_period(16700000, 16666666, 12000000));
  assert(!compatible_vblank_period(16666666, 16666, 12000000));
  assert(!compatible_vblank_period(16666035, 33333333, 12000000));
  assert(!compatible_vblank_period(6944444, 6944444, 12000000));
  assert(!compatible_vblank_period(0, 16666666, 12000000));
  assert(!compatible_vblank_period(16666666, 0, 12000000));
  assert(!compatible_vblank_period(16666666, 16666666, -1));
  // A query or wake may overshoot a deadline that we started waiting for.
  assert(usable_vblank(11, 10, 100000000, 113100000, 16666666, 112900000, 13000000));
  // Entering pacing after that phase must wait, not keep FIFO capture busy.
  assert(!usable_vblank(11, 10, 100000000, 113100000, 16666666, 113050000, 13000000));
  assert(usable_vblank(11, 10, 100000000, 100200000, 16666666, 99900000, 0));
  assert(!usable_vblank(11, 10, 100000000, 100200000, 16666666, 100100000, 0));
  assert(!usable_vblank(10, 10, 100000000, 110000000, 16666666, 109000000, 12000000));
  assert(!usable_vblank(11, 10, 100000000, 116666666, 16666666, 109000000, 12000000));
  assert(usable_vblank(0, std::numeric_limits<std::uint32_t>::max(), 100000000, 110000000, 16666666, 109000000, 12000000));
  assert(!usable_vblank(11, 10, 0, 110000000, 16666666, 109000000, 12000000));
  assert(!usable_vblank(11, 10, 120000000, 110000000, 16666666, 109000000, 12000000));
  assert(future_nominal_deadline_ns(100, 90, 16) == 100);
  assert(future_nominal_deadline_ns(100, 100, 16) == 116);
  assert(future_nominal_deadline_ns(100, 151, 16) == 164);
  assert(!future_nominal_deadline_ns(100, 151, 0));
  assert(!future_nominal_deadline_ns(100, std::numeric_limits<std::int64_t>::max(), 16));
  std::puts("PASS strict offset parsing, refresh compatibility, late entry versus query overshoot, future-only nominal fallback, no sequence reuse, sequence wrap");
}

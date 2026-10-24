#!/usr/bin/env python3
"""Execute the patched encoder pacing blocks with a deterministic clock."""

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


def block(source, marker):
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def main():
    source = Path(sys.argv[1]).read_text()
    # Both execution paths must use the session's negotiated FPS, not the
    # capture backend's rate or a fixed 60 FPS deadline.
    assert "const std::uint32_t rkmpp_fps = config.framerate;" in source
    assert "const std::uint32_t rkmpp_fps = ctx->config.framerate;" in source
    interval = block(
        source, "  std::chrono::steady_clock::duration rkmpp_fps_interval("
    )
    encode = block(
        source, "      if (!requested_idr_frame && pace_rkmpp && rkmpp_fps > 0)"
    )
    capture = block(
        source, "          if (frame_captured && pace_rkmpp && rkmpp_fps > 0)"
    )
    # Only substitute time effects. Conditions and deadline arithmetic come
    # directly from the source that the release package compiles.
    encode = encode.replace("std::chrono::steady_clock::now()", "clock_now()")
    encode = encode.replace("std::this_thread::sleep_until", "sleep_until")
    capture = capture.replace("std::chrono::steady_clock::now()", "clock_now()")
    harness = (
        r"""
#include <cassert>
#include <chrono>
#include <cstdint>
#include <iostream>
using clock_type = std::chrono::steady_clock;
using duration = clock_type::duration;
using time_point = clock_type::time_point;
static time_point current;
static duration overshoot;
static int sleeps;
time_point clock_now() { return current; }
void sleep_until(time_point deadline) {
  assert(deadline > current);
  current = deadline + overshoot;
  ++sleeps;
}
"""
        + interval
        + r"""
void encode_step(bool requested_idr_frame, bool pace_rkmpp,
                 std::uint32_t rkmpp_fps, time_point &next_rkmpp_frame) {
"""
        + encode
        + r"""
}
struct context { time_point next_rkmpp_frame; };
bool capture_step(bool frame_captured, bool pace_rkmpp,
                  std::uint32_t rkmpp_fps, context *ctx) {
  int pos = 0;
  // The source's continue skips conversion and encode for this session.
  do {
"""
        + capture
        + r"""
  } while (false);
  return pos == 0;
}
int main() {
  const auto epoch = time_point {std::chrono::seconds {10}};
  for (const std::uint32_t fps : {1u, 30u, 59u, 60u, 61u, 90u, 120u, 144u}) {
    const auto interval = rkmpp_fps_interval(fps);
    assert(interval == std::chrono::duration_cast<duration>(
      std::chrono::duration<double> {1.0 / fps}));
    current = epoch;
    overshoot = interval / 20;
    sleeps = 0;
    time_point next {};
    encode_step(false, true, fps, next);
    assert(next == epoch + interval && sleeps == 0);
    next = epoch;
    encode_step(false, true, fps, next);
    assert(next == epoch + interval && sleeps == 0);
    // Sleep overshoot must not accumulate in the schedule.
    for (int i = 2; i <= 1000; ++i) {
      encode_step(false, true, fps, next);
      assert(next == epoch + interval * i);
    }
    assert(sleeps == 999);
    // The stall threshold is strictly more than one interval after the
    // advanced deadline. Equality does not resynchronise.
    current = next + interval * 2;
    auto expected = next + interval;
    encode_step(false, true, fps, next);
    assert(next == expected);
    current = next + interval * 2 + duration {1};
    expected = current + interval;
    encode_step(false, true, fps, next);
    assert(next == expected);
    // IDR, other encoders, and zero FPS bypass the encode pacer.
    for (int bypass = 0; bypass < 3; ++bypass) {
      const auto before = next;
      const auto sleep_count = sleeps;
      encode_step(bypass == 0, bypass != 1, bypass == 2 ? 0 : fps, next);
      assert(next == before && sleeps == sleep_count);
    }
    context ctx {};
    current = epoch;
    assert(capture_step(true, true, fps, &ctx));
    assert(ctx.next_rkmpp_frame == epoch + interval);
    // Early Wayland captures skip conversion and encode without sleeping.
    const auto sleep_count = sleeps;
    current = epoch + interval - duration {1};
    assert(!capture_step(true, true, fps, &ctx));
    assert(ctx.next_rkmpp_frame == epoch + interval && sleeps == sleep_count);
    current = epoch + interval;
    assert(capture_step(true, true, fps, &ctx));
    assert(ctx.next_rkmpp_frame == epoch + interval * 2);
    // A stalled capture skips all elapsed absolute deadlines.
    current = epoch + interval * 20 + interval / 2;
    assert(capture_step(true, true, fps, &ctx));
    assert(ctx.next_rkmpp_frame == epoch + interval * 21);
    for (int bypass = 0; bypass < 3; ++bypass) {
      const auto before = ctx.next_rkmpp_frame;
      assert(capture_step(bypass != 0, bypass != 1, bypass == 2 ? 0 : fps, &ctx));
      assert(ctx.next_rkmpp_frame == before && sleeps == sleep_count);
    }
  }
  std::cout << "RKMPP encode and Wayland capture pacing passed\n";
}
"""
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        (path / "pacing.cpp").write_text(harness)
        subprocess.run(
            shlex.split(os.environ.get("CXX", "c++"))
            + [
                "-std=c++17",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(path / "pacing.cpp"),
                "-o",
                str(path / "pacing"),
            ],
            check=True,
        )
        subprocess.run([str(path / "pacing")], check=True)


if __name__ == "__main__":
    main()

#include "runtime-resolution-channel.h"
#include <cassert>
#include <iostream>

int main() {
  using namespace korri::runtime_resolution;
  channel state({1920, 1080}, 20000, 60);
  request capability {1, query, {0,0}, reason::none};
  assert(state.submit(capability, channel::clock::now()).empty());
  assert(!state.reply());
  state.supported(true);
  auto ready = state.reply();
  assert(ready && read32(*ready,12) == resolution_bit);
  state.suspend();
  capability.id = 2;
  assert(state.submit(capability, channel::clock::now()).empty());
  state.supported(true);
  assert(state.reply());
  state.supported(false);
  request resize{2, resolution, {2448, 1848}, reason::none};
  auto refused = state.submit(resize, channel::clock::now());
  assert(read16(refused, 16) == static_cast<unsigned>(reason::unsupported_encoder));
  assert(!state.take());
  state.supported(true);
  assert(state.submit(resize, channel::clock::now()).empty());
  auto work = state.take();
  assert(work && !state.take());
  auto concurrent = resize;
  concurrent.id = 3;
  assert(!state.submit(concurrent, channel::clock::now()).empty());
  bool applied = false;
  assert(state.finish(*work, true, [&] { applied = true; }));
  assert(applied);
  auto reply = state.reply();
  assert(reply && read32(*reply, 8) == 2448 && read32(*reply, 12) == 1848);
  assert(!state.reply());
  assert(!state.submit(resize, channel::clock::now()).empty());

  resize.id = 4;
  resize.target = {1600, 1200};
  assert(state.submit(resize, channel::clock::now()).empty());
  work = state.take();
  assert(work);
  assert(!state.finish(*work, false, [] { assert(false); }));
  reply = state.reply();
  assert(reply && read32(*reply, 8) == 2448);
  assert(read16(*reply, 16) == static_cast<unsigned>(reason::apply_failed));

  resize.id = 5;
  assert(state.submit(resize, channel::clock::now() - std::chrono::seconds(3)).empty());
  work = state.take();
  assert(work);
  assert(!state.finish(*work, true, [] { assert(false); }));
  assert(state.reply());

  // A render-mode change can suspend capture before its resize request arrives.
  resize.id = 6;
  state.suspend();
  assert(state.submit(resize, channel::clock::now()).empty());
  assert(!state.take());
  state.supported(true);
  work = state.take();
  assert(work);
  auto deadline = work->deadline;
  assert(state.defer(*work));
  assert(!state.take());
  state.supported(true);
  work = state.take();
  assert(work && work->deadline == deadline);
  assert(state.finish(*work, true, [] {}));
  assert(state.reply());
  resize.id = 7;
  state.suspend();
  assert(state.submit(resize, channel::clock::now()).empty());
  state.supported(false);
  assert(!state.take());
  reply = state.reply();
  assert(reply && read16(*reply, 16) == static_cast<unsigned>(reason::unsupported_encoder));
  state.supported(true);
  resize.id = 8;
  assert(state.submit(resize, channel::clock::now()).empty());
  work = state.take();
  assert(work);
  state.close();
  assert(!state.finish(*work, true, [] { assert(false); }));
  assert(!state.reply());
  assert(!state.take());
  state.supported(true);
  assert(state.submit(resize, channel::clock::now()).empty());
  assert(!state.take());
  std::cout << "runtime-resolution admission, commit, refusal, deadline and teardown passed\n";
}

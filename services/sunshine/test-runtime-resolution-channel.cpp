#include "runtime-resolution-channel.h"
#include <cassert>
#include <future>
#include <iostream>
#include <thread>

namespace {
using namespace korri::runtime_resolution;

// The encoder thread's side: wait until the channel offers work.
std::optional<channel::work> await_work(channel &state) {
  for (int tries = 0; tries < 2000; ++tries) {
    if (auto work = state.take()) return work;
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
  return std::nullopt;
}

std::future<local_result> ask(channel &state, size target, std::chrono::milliseconds wait) {
  return std::async(std::launch::async, [&state, target, wait] { return state.resize(target, wait); });
}

// Patch 0046: a resize that korrid asks for. Its answer goes to korrid only.
void local_resize() {
  const auto long_wait = std::chrono::milliseconds(3000);
  channel state({1280, 720}, 20000, 60);
  state.supported(true);

  // Applied: the encoder takes the request as it takes a client's.
  auto applied = ask(state, {720, 1280}, long_wait);
  auto work = await_work(state);
  assert(work && work->local && work->request.target == (size {720, 1280}));
  bool committed = false;
  assert(state.finish(*work, true, [&] { committed = true; }));
  auto result = applied.get();
  assert(committed && result.outcome == status::applied && result.why == reason::none);
  assert(result.current == (size {720, 1280}));
  assert(!state.reply());  // nothing goes to the stream's client

  // Refused before the encoder: bounds, then a pending client request.
  for (size bad : {size {0, 720}, size {721, 1280}, size {4098, 720}}) {
    result = state.resize(bad, long_wait);
    assert(result.outcome == status::failed && result.why == reason::invalid_bounds);
    assert(result.current == (size {720, 1280}));
  }
  request client {9, resolution, {1280, 720}, reason::none};
  assert(state.submit(client, channel::clock::now()).empty());
  result = state.resize({1280, 720}, long_wait);
  assert(result.why == reason::conflict);
  work = state.take();
  assert(work && !work->local);
  assert(state.finish(*work, true, [] {}));
  assert(state.reply());  // the client's own answer still goes to the client

  // A client request while korrid's is pending is a conflict for the client.
  auto pending = ask(state, {720, 1280}, long_wait);
  work = await_work(state);
  assert(work && work->local);
  client.id = 10;
  auto refused = state.submit(client, channel::clock::now());
  assert(!refused.empty() && read16(refused, 16) == static_cast<unsigned>(reason::conflict));
  assert(!state.finish(*work, false, [] { assert(false); }));
  result = pending.get();
  assert(result.why == reason::apply_failed && result.current == (size {1280, 720}));

  // Unanswered: the request is withdrawn and its encoder can no longer commit.
  auto slow = ask(state, {720, 1280}, std::chrono::milliseconds(300));
  auto stale = await_work(state);
  assert(stale);
  result = slow.get();
  assert(result.why == reason::apply_failed);
  auto next = ask(state, {960, 540}, long_wait);
  work = await_work(state);
  assert(work && work->sequence != stale->sequence);
  assert(!state.finish(*stale, true, [] { assert(false); }));
  assert(!state.defer(*stale));
  assert(state.finish(*work, true, [] {}));
  result = next.get();
  assert(result.outcome == status::applied && result.current == (size {960, 540}));

  // A capture restart defers it; the next encoder finishes it.
  state.suspend();
  auto deferred = ask(state, {1280, 720}, long_wait);
  std::this_thread::sleep_for(std::chrono::milliseconds(20));
  assert(!state.take());
  state.supported(true);
  work = await_work(state);
  assert(work && state.defer(*work));
  state.supported(true);
  work = await_work(state);
  assert(work && state.finish(*work, true, [] {}));
  assert(deferred.get().outcome == status::applied);

  // An encoder without live resolution, before and while the request waits.
  state.suspend();
  auto unsupported = ask(state, {720, 1280}, long_wait);
  std::this_thread::sleep_for(std::chrono::milliseconds(20));
  state.supported(false);
  assert(unsupported.get().why == reason::unsupported_encoder);
  assert(state.resize({720, 1280}, long_wait).why == reason::unsupported_encoder);
  assert(!state.reply());

  // The stream ends while the request waits, and after.
  state.supported(true);
  auto ending = ask(state, {720, 1280}, long_wait);
  work = await_work(state);
  assert(work);
  state.close();
  assert(ending.get().why == reason::stream_ended);
  assert(!state.finish(*work, true, [] { assert(false); }));
  assert(state.resize({720, 1280}, long_wait).why == reason::stream_ended);
}
}  // namespace

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
  local_resize();
  std::cout << "runtime-resolution admission, commit, refusal, deadline and teardown passed\n";
  std::cout << "korrid's local resize: answer, refusal, withdrawal, deferral and teardown passed\n";
}

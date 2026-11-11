#include "runtime-resolution-wire.h"
extern "C" {
#include "SunshineRuntimeSettings.h"
}
#include <cassert>
#include <iostream>

int main() {
  using namespace korri::runtime_resolution;
  SS_RUNTIME_SETTINGS_STATE client;
  SsRuntimeSettingsInitialize(&client);
  SsRuntimeSettingsBeginSession(&client, 7);
  SsRuntimeSettingsSetSessionActive(&client, true);
  std::array<std::uint8_t, 16> buffer {};
  std::size_t length = 0;
  assert(SsRuntimeSettingsPrepareRequest(&client, 7, 0, 1, query, 0, 0,
                                        buffer.data(), &length) == 0);
  auto request = decode(std::span(buffer).first(length));
  assert(request && request->id == 1 && request->refusal == reason::none);
  auto facts = capabilities(1, true, 20000, 60, {1920, 1080}, {1920, 1080});
  assert(SsRuntimeSettingsProcessAck(&client, facts.data(), facts.size()) == 0);
  assert(client.snapshot.supportedOperations == resolution_bit);
  assert(SsRuntimeSettingsPrepareRequest(&client, 7, 1, 2, resolution, 2448, 1848,
                                        buffer.data(), &length) == 0);
  request = decode(std::span(buffer).first(length));
  const size unfolded {2448, 1848};
  assert(request && request->target == unfolded && request->refusal == reason::none);
  auto ack = resolution_ack(request->id, status::applied, reason::none, request->target);
  assert(SsRuntimeSettingsProcessAck(&client, ack.data(), ack.size()) == 0);
  assert(client.snapshot.currentWidth == 2448 && client.snapshot.currentHeight == 1848);
  assert(client.snapshot.sessionEpoch == 7);
  // Old ACKs cannot apply a second time, even when dimensions still match.
  assert(SsRuntimeSettingsProcessAck(&client, ack.data(), ack.size()) ==
         LI_RUNTIME_SETTINGS_ERROR_STALE_ACK);
  for (unsigned n = 0; n < 8; ++n) assert(!decode(std::span(buffer).first(n)));
  for (unsigned n = 8; n < 16; ++n)
    assert(decode(std::span(buffer).first(n))->refusal == reason::invalid_payload);
  write16(buffer, 6, 1);
  assert(decode(buffer)->refusal == reason::invalid_payload);
  write16(buffer, 6, 0);
  write32(buffer, 8, 4098);
  assert(decode(buffer)->refusal == reason::invalid_bounds);
  write16(buffer, 4, SS_RUNTIME_SETTINGS_OPERATION_SET_FPS);
  assert(decode(buffer)->refusal == reason::unsupported_operation);
  write32(buffer, 0, 0);
  assert(decode(buffer)->refusal == reason::invalid_payload);
  std::cout << "runtime-resolution host/client wire checks passed\n";
}

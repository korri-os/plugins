// Patch 0046: korrid's resize request on the certificate-control socket.
#include "korri_certificate_control.h"
#include "crypto.h"

#include <nlohmann/json.hpp>

#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>
#include <optional>
#include <string>
#include <vector>

namespace kc = korri_certificate_control;
namespace rr = korri::runtime_resolution;

static std::string read_all(const char *path) {
  std::ifstream input(path, std::ios::binary);
  assert(input.good());
  return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

static std::string resize_frame(const std::string &host, const std::string &certificate, const std::string &display) {
  return "{\"operation\":\"resize\",\"hostUuid\":" + kc::json_quote(host) + ",\"certificate\":" +
         kc::json_quote(certificate) + ",\"display\":" + display + "}";
}

static std::string refusal(const std::string &frame) {
  try {
    (void) kc::parse_resize_request(frame, "sunshine-host");
  } catch (const kc::protocol_error &error) {
    return error.code();
  }
  return {};
}

int main(int argc, char **argv) {
  assert(argc == 3);
  const auto client_one = read_all(argv[1]);
  const auto client_two = read_all(argv[2]);
  const auto one = kc::validate_single_certificate(client_one).fingerprint;
  const auto two = kc::validate_single_certificate(client_two).fingerprint;
  assert(one.size() == 64 && one != two);

  // A session holds the TLS peer's certificate as crypto::pem made it. The
  // fingerprint matches whatever PEM text korrid stored for the same key.
  auto x509 = crypto::x509(client_one);
  assert(x509);
  assert(kc::validate_single_certificate(crypto::pem(x509)).fingerprint == one);
  assert(kc::validate_single_certificate("\n" + client_one + " \n").fingerprint == one);

  const auto frame = resize_frame("sunshine-host", client_one, R"({"width":720,"height":1280})");
  const auto parsed = kc::parse_resize_request(frame, "sunshine-host");
  assert(parsed && parsed->fingerprint == one);
  assert(parsed->display == (rr::size {720, 1280}));

  // Other operations stay with patch 0020's handler, unchanged.
  for (const auto &other : std::vector<std::string> {
           "",
           "not json",
           "[]",
           R"({"operation":"attest","hostUuid":"sunshine-host"})",
           R"({"operation":"provision","hostUuid":"sunshine-host","certificate":"x"})",
           R"({"operation":7,"hostUuid":"sunshine-host"})",
           R"({"hostUuid":"sunshine-host"})",
       }) {
    assert(!kc::parse_resize_request(other, "sunshine-host"));
  }

  for (const auto &display : std::vector<std::string> {
           R"({"width":720})",
           R"({"width":720,"height":1280,"depth":1})",
           R"({"width":-720,"height":1280})",
           R"({"width":720.5,"height":1280})",
           R"({"width":"720","height":1280})",
           R"({"width":4294967296,"height":1280})",
           R"([720,1280])",
       }) {
    assert(refusal(resize_frame("sunshine-host", client_one, display)) == "InvalidFrame");
  }
  assert(refusal(R"({"operation":"resize","hostUuid":"sunshine-host","display":{"width":2,"height":2}})") ==
         "InvalidFrame");
  assert(refusal(resize_frame("sunshine-host", client_one, R"({"width":720,"height":1280})").insert(1, "\"extra\":1,")) ==
         "InvalidFrame");
  assert(refusal(resize_frame("another-host", client_one, R"({"width":720,"height":1280})")) == "HostMismatch");
  assert(refusal(resize_frame("sunshine-host", "not a certificate", R"({"width":720,"height":1280})")) ==
         "InvalidCertificate");
  assert(refusal(resize_frame("sunshine-host", client_one + client_two, R"({"width":720,"height":1280})")) ==
         "InvalidCertificate");

  // The encoder's answer, as korrid reads it.
  const auto applied = nlohmann::json::parse(
      kc::resize_response({rr::status::applied, rr::reason::none, {720, 1280}}));
  assert(applied == nlohmann::json({{"status", "ok"}, {"display", {{"width", 720}, {"height", 1280}}}}));
  for (const auto &[why, code] : std::vector<std::pair<rr::reason, std::string>> {
           {rr::reason::invalid_bounds, "InvalidBounds"},
           {rr::reason::unsupported_encoder, "UnsupportedEncoder"},
           {rr::reason::apply_failed, "ApplyFailed"},
           {rr::reason::conflict, "Conflict"},
           {rr::reason::stream_ended, "StreamEnded"},
           {rr::reason::invalid_payload, "InternalError"},
       }) {
    const auto failed = nlohmann::json::parse(kc::resize_response({rr::status::failed, why, {1280, 720}}));
    assert(failed == nlohmann::json({{"status", "error"}, {"code", code}}));
  }

  // The handler calls the stream's resize once, with the fingerprint, and
  // never for a refused frame or another operation.
  std::vector<std::pair<std::string, rr::size>> calls;
  auto resize = [&](const std::string &fingerprint, rr::size display) {
    calls.emplace_back(fingerprint, display);
    return rr::local_result {rr::status::failed, rr::reason::stream_ended, {0, 0}};
  };
  const auto answer = kc::handle_resize_request(frame, "sunshine-host", resize);
  assert(answer && nlohmann::json::parse(*answer) == nlohmann::json({{"status", "error"}, {"code", "StreamEnded"}}));
  assert(calls.size() == 1 && calls[0].first == one && calls[0].second == (rr::size {720, 1280}));
  const auto mismatch = kc::handle_resize_request(
      resize_frame("another-host", client_one, R"({"width":720,"height":1280})"), "sunshine-host", resize);
  assert(mismatch && nlohmann::json::parse(*mismatch)["code"] == "HostMismatch");
  assert(!kc::handle_resize_request(R"({"operation":"attest","hostUuid":"sunshine-host"})", "sunshine-host", resize));
  assert(calls.size() == 1);
  // No certificate text in any answer.
  assert(answer->find("CERTIFICATE") == std::string::npos);

  std::cout << "korrid's resize request: parsing, refusals and answers passed\n";
}

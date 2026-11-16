{
  pkgs,
  sunshinePackage,
  approvedPatchesPath,
  patchPath,
  testPath,
}:

# Patch 0046: korrid's resize request on the certificate-control socket.
# The channel's side (korrid's request, its answer and its withdrawal) is
# tested by the runtime-resolution check.
let
  lib = pkgs.lib;
  approved = import approvedPatchesPath;
  contains = needle: haystack: lib.hasInfix needle haystack;
  check = message: assertion: { inherit message assertion; };
  patch = builtins.readFile patchPath;
  patchName = builtins.baseNameOf patchPath;
  approvedPatch = lib.findFirst (record: record.name == patchName) null approved.patches;
  patchedSource = pkgs.applyPatches {
    name = "sunshine-korri-stream-resize-source";
    src = pkgs.sunshine.src;
    patches = map (record: record.path) approved.patches;
    patchFlags = [
      "-p1"
      "--fuzz=0"
    ];
  };
  checks = [
    (check "the resize patch is exact, approved and in the package" (
      approvedPatch != null
      && builtins.hashFile "sha256" patchPath == approvedPatch.sha256
      && builtins.elem patchName sunshinePackage.korriPatchNames
    ))
    (check "the request is served by patch 0020's socket and matched by fingerprint" (
      contains "handle_resize_request(frame, http::unique_id, resize_korri_stream)" patch
      && contains "validate_single_certificate(certificate).fingerprint == fingerprint" patch
      && contains "rtsp_stream::runtime_resolution_channels" patch
      && contains "stream::session::state_e::RUNNING" patch
      && !(contains "AF_INET" patch)
    ))
    (check "the answer goes to korrid, never to the stream's client" (
      contains "if (local) {" patch
      && contains "local_done_.notify_all();" patch
      && contains "pending_->sequence != work.sequence" patch
    ))
    (check "no certificate body is logged" (
      !(contains "<< certificate" patch) && !(contains "<< fingerprint" patch)
    ))
  ];
  failures = builtins.filter (candidate: !candidate.assertion) checks;
in
if failures != [ ] then
  throw "Korri Sunshine stream-resize patch check failed:\n${
    lib.concatMapStringsSep "\n" (failure: "- ${failure.message}") failures
  }"
else
  pkgs.runCommand "sunshine-korri-stream-resize-check"
    {
      nativeBuildInputs = [
        pkgs.stdenv.cc
        pkgs.openssl
      ];
      buildInputs = [
        pkgs.boost
        pkgs.openssl
        pkgs.nlohmann_json
      ];
    }
    ''
      work="$TMPDIR/certs"
      mkdir -p "$work"
      for name in client-one client-two; do
        ${pkgs.openssl}/bin/openssl req -x509 -newkey rsa:2048 -nodes \
          -subj "/CN=$name" -keyout "$work/$name.key" -out "$work/$name.crt" \
          -days 1 >/dev/null 2>&1
      done
      c++ -std=c++20 -O2 -Wall -Wextra -Werror -pedantic -pthread \
        -I${patchedSource}/src \
        ${testPath} ${patchedSource}/src/korri_certificate_control.cpp \
        ${patchedSource}/src/crypto.cpp \
        -lcrypto -o "$work/test-stream-resize"
      "$work/test-stream-resize" "$work/client-one.crt" "$work/client-two.crt"
      mkdir -p "$out"
      printf '%s\n' '${approvedPatch.sha256}' > "$out/stream-resize-patch-sha256"
    ''

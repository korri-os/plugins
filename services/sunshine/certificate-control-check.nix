{
  pkgs,
  sunshinePackage,
  approvedPatchesPath,
  patchPath,
  packagePath,
  testPath,
}:

let
  lib = pkgs.lib;
  approved = import approvedPatchesPath;
  contains = needle: haystack: lib.hasInfix needle haystack;
  check = message: assertion: { inherit message assertion; };
  patch = builtins.readFile patchPath;
  packageSource = builtins.readFile packagePath;
  patchName = builtins.baseNameOf patchPath;
  approvedPatch = lib.findFirst (record: record.name == patchName) null approved.patches;
  patchSha256 = builtins.hashFile "sha256" patchPath;
  expectedPatchSetSha256 =
    if sunshinePackage.korriRkmppEnabled or false then
      approved.rkmppPatchSetSha256
    else
      approved.patchSetSha256;
  patchedSource = pkgs.applyPatches {
    name = "sunshine-korri-certificate-control-source";
    src = pkgs.sunshine.src;
    patches = map (record: record.path) approved.patches;
    patchFlags = [
      "-p1"
      "--fuzz=0"
    ];
  };
  identityPatch = builtins.readFile ./patches/0039-bind-paired-client-input-identity.patch;
  checks = [
    (check "paired UUID is authenticated, propagated and unbound input fails closed" (
      contains "X509_cmp(paired.get(), x509.get()) == 0" identityPatch
      && contains "return client.uuid" identityPatch
      && contains "client.enabled && paired" identityPatch
      && contains "request->verified_client_uuid()" identityPatch
      && contains "session->client_uuid = launch_session.client_uuid" identityPatch
      && contains "input::alloc(session.mail, session.input_session_id, session.client_uuid)" identityPatch
      && contains "other->client_id == client_id" identityPatch
      && contains "clientId" identityPatch
      && contains "refused stream without authenticated paired-client UUID" identityPatch
    ))
    (check "the certificate-control patch is exact and approved" (
      approvedPatch != null
      && patchSha256 == approvedPatch.sha256
      && contains "approved-patches.nix" packageSource
      && builtins.elem patchName sunshinePackage.korriPatchNames
      && sunshinePackage.korriPatchSetSha256 == expectedPatchSetSha256
    ))
    (check "the private adapter consumes one root-owned systemd seqpacket socket" (
      contains "LISTEN_FDS" patch
      && contains "LISTEN_PID" patch
      && contains "LISTEN_FDNAMES" patch
      && contains "SOCK_SEQPACKET" patch
      && contains "SO_PEERCRED" patch
      && contains "accept4" patch
      && contains "KORRI_CERTIFICATE_CONTROL_UID" patch
      && contains "KORRI_CERTIFICATE_CONTROL_GID" patch
      && contains "KORRI_CERTIFICATE_CONTROL_OWNER_GID" patch
      && contains "KORRI_CERTIFICATE_CONTROL_PATH" patch
      && contains "KORRI_CERTIFICATE_CONTROL_MODE" patch
      && contains "select_systemd_descriptor" patch
      && contains "socket_state.st_gid != expected_owner_gid" patch
      && contains "expected_path," patch
      && contains "static_cast<gid_t>(*expected_owner_gid)" patch
      && !(contains "AF_INET" patch)
      && !(contains "AF_INET6" patch)
    ))
    (check "frames, certificates, and peer handling are bounded" (
      contains "max_frame_bytes = 16384" patch
      && contains "MSG_TRUNC" patch
      && contains "MSG_DONTWAIT" patch
      && contains "SOCK_CLOEXEC" patch
      && contains "SOCK_NONBLOCK" patch
      && contains "hostUuid" patch
      && contains "operation::attest" patch
      && contains "attest_response" patch
      && contains "http::unique_id" patch
    ))
    (check "state mutation is serialized, candidate-based, and atomic" (
      contains "client_auth_mutex()" patch
      && contains "entry.enabled" patch
      && contains "validated.canonical_pem" patch
      && contains "candidate" patch
      && contains "mkostemp" patch
      && contains "fsync" patch
      && contains "rename" patch
      && contains "replace_state_and_activate" patch
      && contains "replace_bytes_after_restore(target, previous, faults)" patch
      && !(contains "O_TRUNC" patch)
      && contains "activate_verified_state" patch
      && contains "accept_transaction_result" patch
      && contains "std::abort()" patch
      && contains "client_state_integrity_failed" patch
      && contains "apply_provision" patch
      && contains "apply_revoke" patch
    ))
    (check "no certificate body or private key is logged" (
      !(contains "BOOST_LOG(debug) << request" patch)
      && !(contains "BOOST_LOG(info) << request" patch)
      && !(contains "BOOST_LOG(warning) << request" patch)
      && !(contains "BOOST_LOG(error) << request" patch)
      && !(contains "BOOST_LOG(debug) << certificate" patch)
      && !(contains "BOOST_LOG(info) << certificate" patch)
    ))
  ];
  failures = builtins.filter (candidate: !candidate.assertion) checks;
in
if failures != [ ] then
  throw "Korri Sunshine certificate-control patch check failed:\n${
    lib.concatMapStringsSep "\n" (failure: "- ${failure.message}") failures
  }"
else
  pkgs.runCommand "sunshine-korri-certificate-control-check"
    {
      nativeBuildInputs = [
        pkgs.stdenv.cc
        pkgs.openssl
        pkgs.python3
      ];
      buildInputs = [
        pkgs.boost
        pkgs.openssl
        pkgs.nlohmann_json
      ];
    }
    ''
            test -x ${sunshinePackage}/bin/sunshine
            grep -F 'bool erase_all_clients();' ${patchedSource}/src/nvhttp.h >/dev/null
            grep -F 'bool erase_all_clients() {' ${patchedSource}/src/nvhttp.cpp >/dev/null
            grep -F 'if (!nvhttp::erase_all_clients()) {' ${patchedSource}/src/confighttp.cpp >/dev/null
            python3 - ${patchedSource}/src/confighttp.cpp <<'PY'
      import pathlib
      import sys

      source = pathlib.Path(sys.argv[1]).read_text()
      start = source.index("void unpairAll(")
      end = source.index("/**", start + 1)
      body = source[start:end]
      failure = body.index('if (!nvhttp::erase_all_clients()) {')
      failure_status = body.index('output_tree["status"] = false;', failure)
      failure_return = body.index('return;', failure_status)
      success_status = body.index('output_tree["status"] = true;', failure_return)
      terminate = body.index('proc::proc.terminate();', success_status)
      assert failure < failure_status < failure_return < success_status < terminate
      PY
            # These upstream security boundaries are not Korri extension points.
            python3 - ${pkgs.sunshine.src} ${patchedSource} <<'PY'
      import pathlib
      import sys

      base, patched = map(pathlib.Path, sys.argv[1:])
      for name in ("crypto.cpp", "crypto.h"):
          assert (base / "src" / name).read_bytes() == (patched / "src" / name).read_bytes()

      def function(root, name, marker):
          text = (root / "src" / name).read_text()
          start = text.index(marker)
          return text[start:text.index("\n  }\n", start) + 5]

      for name, marker in (
          ("input.cpp", "  bool validate_input_packet("),
          ("stream.cpp", "  std::optional<std::pair<std::uint16_t, std::string_view>> parse_control_packet("),
          ("nvhttp.cpp", "  bool start_pairing_session("),
          ("nvhttp.cpp", "  bool pin("),
          ("nvhttp.cpp", "  const char *verify_client_certificate("),
      ):
          assert function(base, name, marker) == function(patched, name, marker), marker
      text = (patched / "src/nvhttp.cpp").read_text()
      verification = text[text.index("    https_server.verify = "):text.index("    https_server.on_verify_failed = ")]
      assert verification.index("verify_client_certificate(x509.get())") < verification.index("return client.uuid;")
      assert "client.enabled && paired && X509_cmp(paired.get(), x509.get()) == 0" in verification
      PY
            work="$TMPDIR/certs"
            mkdir -p "$work"
            ${pkgs.openssl}/bin/openssl req -x509 -newkey rsa:2048 -nodes \
              -subj /CN=client-one -keyout "$work/client-one.key" -out "$work/client-one.crt" \
              -days 1 >/dev/null 2>&1
            ${pkgs.openssl}/bin/openssl req -x509 -newkey rsa:2048 -nodes \
              -subj /CN=client-two -keyout "$work/client-two.key" -out "$work/client-two.crt" \
              -days 1 >/dev/null 2>&1
            ${pkgs.openssl}/bin/openssl req -x509 -newkey rsa:2048 -nodes \
              -subj /CN=server -keyout "$work/server.key" -out "$work/server.crt" \
              -days 1 >/dev/null 2>&1
            c++ -std=c++20 -O2 -Wall -Wextra -Werror -pedantic -pthread \
              -I${patchedSource}/src \
              ${testPath} ${patchedSource}/src/korri_certificate_control.cpp \
              ${patchedSource}/src/crypto.cpp \
              -lcrypto -o "$work/test-certificate-control"
            "$work/test-certificate-control" \
              "$work/client-one.crt" "$work/client-two.crt" "$work/server.crt"
            mkdir -p "$out"
            printf '%s\n' '${approvedPatch.sha256}' > "$out/certificate-control-patch-sha256"
    ''

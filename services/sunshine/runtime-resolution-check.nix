{ pkgs, korri }:
let
  approved = import ./approved-patches.nix;
  client = "${korri}/clients/android/app/src/main/jni/moonlight-core/moonlight-common-c/src";
  source = pkgs.applyPatches {
    name = "sunshine-runtime-resolution-check-source";
    src = pkgs.sunshine.src;
    patchFlags = [ "-p1" "--fuzz=0" "--no-backup-if-mismatch" ];
    patches = map (record: record.path) approved.patches;
  };
in
pkgs.stdenv.mkDerivation {
  name = "sunshine-runtime-resolution-check";
  dontUnpack = true;
  buildPhase = ''
    $CXX -std=c++23 -O2 -Wall -Wextra -Werror -pthread -I${source}/src \
      ${./test-runtime-resolution-channel.cpp} -o channel-check
    $CC -std=c11 -O2 -Wall -Wextra -Werror -I${client} \
      -c ${client}/SunshineRuntimeSettings.c -o client.o
    $CXX -std=c++23 -O2 -Wall -Wextra -Werror -I${source}/src -I${client} \
      ${./test-runtime-resolution-wire.cpp} client.o -o wire-check
  '';
  doCheck = true;
  checkPhase = ''
    ./channel-check
    ./wire-check
  '';
  installPhase = "touch $out";
}

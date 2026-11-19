{ pkgs }:
let
  approved = import ./approved-patches.nix;
  source = pkgs.applyPatches {
    name = "sunshine-runtime-resolution-check-source";
    src = pkgs.sunshine.src;
    patchFlags = [ "-p1" "--fuzz=0" "--no-backup-if-mismatch" ];
    patches = map (record: record.path) approved.patches;
  };
in
# The channel half of patch 0044 (and 0046's local resize): admission,
# deferred capture, deadlines and shutdown, against the patched source. Its
# wire half linked Korri's Artemis client (`SunshineRuntimeSettings.c`),
# which Korri removed with Artemis (README.md, "Live resolution control").
pkgs.stdenv.mkDerivation {
  name = "sunshine-runtime-resolution-check";
  dontUnpack = true;
  buildPhase = ''
    $CXX -std=c++23 -O2 -Wall -Wextra -Werror -pthread -I${source}/src \
      ${./test-runtime-resolution-channel.cpp} -o channel-check
  '';
  doCheck = true;
  checkPhase = ''
    ./channel-check
  '';
  installPhase = "touch $out";
}

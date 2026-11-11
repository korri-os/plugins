{ pkgs, moonlightPackage }:
let
  source = pkgs.applyPatches {
    name = "moonlight-viewer-presence-source";
    inherit (moonlightPackage) src patches;
    patchFlags = [ "-p1" "--fuzz=0" ];
  };
in pkgs.stdenv.mkDerivation {
  name = "moonlight-viewer-presence-check";
  dontUnpack = true;
  buildPhase = ''
    $CC -std=gnu11 -Wall -Wextra -Werror -pthread \
      -I${source}/src -I${source}/third_party/moonlight-common-c/src \
      ${source}/src/connection.c ${./test-viewer-presence.c} -o presence-check
  '';
  doCheck = true;
  checkPhase = "./presence-check";
  installPhase = "touch $out";
}

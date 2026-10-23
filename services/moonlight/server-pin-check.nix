{ pkgs, moonlightPackage }:
let
  source = pkgs.applyPatches {
    name = "moonlight-server-pin-source";
    src = moonlightPackage.src;
    patches = moonlightPackage.patches;
  };
in
pkgs.runCommand "moonlight-server-pin-check"
  {
    nativeBuildInputs = [
      pkgs.stdenv.cc
      pkgs.pkg-config
      pkgs.python3
      pkgs.openssl
    ];
    buildInputs = [
      pkgs.curl
      pkgs.openssl
    ];
  }
  ''
    cc -Wall -Wextra -Werror -I${source} ${./test-server-pin.c} \
      ${source}/libgamestream/http.c $(pkg-config --cflags --libs libcurl openssl) -o check-pin
    python3 ${./test-server-pin.py} "$PWD/check-pin"
    touch "$out"
  ''

# Runs the exact frontend and its native client/server protocol. No game ROMs.
{ pkgs, program }:
pkgs.runCommand "retroarch-netplay-config-password-check"
  {
    nativeBuildInputs = [ pkgs.stdenv.cc pkgs.python3 pkgs.xvfb-run ];
  }
  ''
    $CC -std=c99 -shared -fPIC -Wall -Wextra -Werror \
      -I${program.src}/libretro-common/include \
      ${./retroarch-netplay-test-core.c} -o "$PWD/core.so"
    export SDL_VIDEODRIVER=x11 SDL_RENDER_DRIVER=software
    export XDG_RUNTIME_DIR="$TMPDIR/runtime"
    mkdir -m 700 "$XDG_RUNTIME_DIR"
    xvfb-run -a python3 ${./retroarch-netplay-config-password-check.py} \
      ${program}/bin/retroarch "$PWD/core.so"
    mkdir -p "$out"
    cp -r accepted refused "$out/"
  ''

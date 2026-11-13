{ pkgs, moonlightPackage }:
let
  source = pkgs.applyPatches {
    name = "moonlight-vaapi-source";
    inherit (moonlightPackage) src patches;
    patchFlags = [
      "-p1"
      "--fuzz=0"
    ];
  };
in
pkgs.runCommand "moonlight-vaapi-check"
  {
    nativeBuildInputs = [
      pkgs.stdenv.cc
      pkgs.pkg-config
      pkgs.xvfb-run
    ];
    # The V4L2 Request extension does not change the VA-API interface. Use
    # the unmodified FFmpeg at the same pin to keep this check small.
    buildInputs = [
      pkgs.ffmpeg
      pkgs.libva
      pkgs.libX11
    ];
  }
  ''
    cc -Wall -Wextra -Werror -Wno-unused-parameter -I${source}/src \
      ${source}/src/video/ffmpeg_vaapi.c ${./test-vaapi.c} \
      $(pkg-config --cflags --libs libavcodec libavutil libva-x11 x11) -o check-vaapi
    export HOME="$TMPDIR" LIBVA_DRIVER_NAME=korri_missing_driver
    xvfb-run -a -s '-screen 0 640x480x24 -nolisten tcp' ./check-vaapi
    touch "$out"
  ''

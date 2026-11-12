{ pkgs, moonlightPackage }:
let
  source = pkgs.applyPatches {
    name = "moonlight-x11-vaapi-size-source";
    inherit (moonlightPackage) src patches;
    patchFlags = [ "-p1" "--fuzz=0" ];
  };
in
pkgs.stdenv.mkDerivation {
  name = "moonlight-x11-vaapi-size-check";
  dontUnpack = true;
  nativeBuildInputs = [ pkgs.pkg-config pkgs.xvfb-run ];
  buildInputs = [ pkgs.ffmpeg pkgs.libva pkgs.libX11 pkgs.libglvnd ];
  buildPhase = ''
    $CC -std=gnu11 -DHAVE_X11 -DHAVE_VAAPI \
      -ffunction-sections -fdata-sections -Wl,--gc-sections \
      -I${source}/src -I${source}/third_party/moonlight-common-c/src \
      ${./test-x11-vaapi-size.c} ${source}/src/video/egl.c \
      $(pkg-config --cflags --libs libavcodec libavutil libva-x11 x11 egl glesv2) \
      -o check-size
  '';
  doCheck = true;
  checkPhase = ''
    xvfb-run -a -s '-screen 0 4096x2304x24 -nolisten tcp' ./check-size
  '';
  installPhase = "touch $out";
}

{
  lib,
  stdenv,
  fetchFromGitHub,
}:
stdenv.mkDerivation {
  pname = "libretro-lowresnx";
  version = "0-unstable-2026-09-30";
  src = fetchFromGitHub {
    owner = "timoinutilis";
    repo = "lowres-nx";
    rev = "63d5988f74e1eea2ecd6ea0445a8ce260b0a9822";
    hash = "sha256-Z2JclvJrj8pzH3pDDxprWOh8TtonPdtWMlkqQrCmBlY=";
  };
  dontConfigure = true;
  buildPhase = ''
    runHook preBuild
    make -C platform/LibRetro -j"$NIX_BUILD_CORES" platform=unix
    runHook postBuild
  '';
  installPhase = ''
    runHook preInstall
    install -Dm755 platform/LibRetro/lowresnx_libretro.so \
      "$out/lib/retroarch/cores/lowresnx_libretro.so"
    install -Dm644 LICENSE "$out/share/doc/libretro-lowresnx/LICENSE"
    install -Dm644 libretro/libretro.h "$out/share/doc/libretro-lowresnx/libretro.h"
    runHook postInstall
  '';
  meta = {
    description = "LowRes NX native libretro runtime (no virtual disk)";
    homepage = "https://lowresnx.inutilis.com";
    license = lib.licenses.zlib;
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
  };
}

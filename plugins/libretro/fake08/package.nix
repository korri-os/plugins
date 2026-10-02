# Only the unix libretro target. Never build or install upstream's players,
# platform assets, sample cartridges, or an official PICO-8 runtime.
{
  lib,
  stdenv,
  fetchgit,
}:
let
  rev = "814991a2571ad3970e386cef48f3b148aa1c27b9";
  z8luaRev = "e6928578d46b61fd5ea30cfcf547e855a30a0553";
in
stdenv.mkDerivation {
  pname = "libretro-fake08";
  version = "0-unstable-2026-06-13";
  src = fetchgit {
    url = "https://github.com/jtothebell/fake-08.git";
    inherit rev;
    fetchSubmodules = true;
    hash = "sha256-+2jhG4hMc5P1it1/ksTlWDRKAvRZUpkq2CZ2NxcEITg=";
  };
  strictDeps = true;
  dontConfigure = true;
  buildPhase = ''
    runHook preBuild
    make -C platform/libretro -j"$NIX_BUILD_CORES" platform=unix
    runHook postBuild
  '';
  installPhase = ''
    runHook preInstall
    install -Dm755 platform/libretro/fake08_libretro.so \
      "$out/lib/retroarch/cores/fake08_libretro.so"
    install -Dm644 platform/libretro/fake08_libretro.info \
      "$out/lib/retroarch/cores/fake08_libretro.info"

    doc="$out/share/doc/libretro-fake08"
    install -Dm644 LICENSE.MD "$doc/LICENSE.MD"
    install -Dm644 ${./THIRD-PARTY.md} "$doc/THIRD-PARTY.md"
    # Preserve complete original files containing transitive notices, not a
    # rewritten list of license names. Read from pristine src, before patching.
    for file in libs/z8lua/lua.h libs/z8lua/eris.c libs/z8lua/fix32.h \
      libs/z8lua/lpico8lib.c libs/lodepng/LICENSE libs/miniz/LICENSE \
      libs/simpleini/SimpleIni.h libs/simpleini/ConvertUTF.h \
      libs/simpleini/ConvertUTF.c source/emojiconversion.cpp \
      source/filter.cpp source/synth.cpp source/graphics.cpp \
      platform/libretro/libretro.h; do
      install -Dm644 "$src/$file" "$doc/original-notices/$file"
    done
    mkdir -p "$out/nix-support/libretro-fake08"
    cat > "$out/nix-support/libretro-fake08/manifest.txt" <<EOF
    upstream=https://github.com/jtothebell/fake-08
    upstream-rev=${rev}
    upstream-source=https://github.com/jtothebell/fake-08/tree/${rev}
    z8lua-source=https://github.com/jtothebell/z8lua/tree/${z8luaRev}
    target=platform/libretro platform=unix
    core=/lib/retroarch/cores/fake08_libretro.so
    notices=/share/doc/libretro-fake08
    EOF
    runHook postInstall
  '';
  passthru = {
    libretroCore = "/lib/retroarch/cores";
    core = "fake08";
  };
  meta = {
    description = "FAKE-08 PICO-8 reimplementation, unix libretro core only";
    homepage = "https://github.com/jtothebell/fake-08";
    # The upstream code is MIT, but linked code also carries these notices.
    # Unicode's original ConvertUTF notice is preserved in original-notices.
    license = with lib.licenses; [
      mit
      wtfpl
      zlib
      cc-by-sa-30
    ];
    platforms = lib.platforms.linux;
  };
}

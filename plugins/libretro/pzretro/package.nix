{
  lib,
  stdenv,
  fetchgit,
  python3,
}:
stdenv.mkDerivation {
  pname = "libretro-pzretro";
  version = "0-unstable-2026-03-01";
  src = fetchgit {
    url = "https://github.com/amberwhitehead/pzretro.git";
    rev = "6d859b47092f585a7ec05804c1d51a1676a06531";
    hash = "sha256-mskesRrXp/j/L3QaZbLNIQXHcHt1slpr65Ie79upAOU=";
    fetchSubmodules = true;
  };
  nativeBuildInputs = [ python3 ];
  dontConfigure = true;
  makeFlags = [ "platform=unix" ];
  installPhase = ''
    runHook preInstall
    install -Dm755 puzzlescript_libretro.so "$out/lib/retroarch/cores/puzzlescript_libretro.so"
    # Preserve native and embedded interpreter/engine notices from pinned source.
    find . -type f \( -iname '*license*' -o -iname 'copying*' -o -iname 'copyright*' \) \
      -not -path './.git/*' -print0 | while IFS= read -r -d $'\0' file; do
      install -Dm644 "$file" "$out/share/doc/libretro-pzretro/notices/$file"
    done
    install -Dm644 src/libretro/include/libretro.h "$out/share/doc/libretro-pzretro/libretro.h"
    runHook postInstall
  '';
  meta = {
    description = "PuzzleScript native libretro runtime with embedded QuickJS";
    homepage = "https://github.com/amberwhitehead/pzretro";
    license = [
      lib.licenses.mit
      lib.licenses.unfreeRedistributable
    ];
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
  };
}

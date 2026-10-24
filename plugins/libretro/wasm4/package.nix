# Only the native libretro backend; no browser, CLI or bundled cartridges.
{
  lib,
  stdenv,
  fetchgit,
  cmake,
}:
stdenv.mkDerivation {
  pname = "libretro-wasm4";
  version = "2.7.1";
  src = fetchgit {
    url = "https://github.com/aduros/wasm4.git";
    rev = "92490f261659921d8b724f10b5b842cdf5a0a1bb";
    hash = "sha256-QmSqQh+8w8pxoQcgHrsTfv/lIb5Xh7LkATnSMDUwjKo=";
    fetchSubmodules = true;
  };
  nativeBuildInputs = [ cmake ];
  cmakeDir = "../runtimes/native";
  cmakeFlags = [
    "-DLIBRETRO=ON"
    "-DWASM_BACKEND=wasm3"
  ];
  installPhase = ''
    runHook preInstall
    install -Dm755 wasm4_libretro.so "$out/lib/retroarch/cores/wasm4_libretro.so"
    install -Dm644 "$src/LICENSE.txt" "$out/share/doc/libretro-wasm4/LICENSE"
    install -Dm644 "$src/runtimes/native/vendor/wasm3/LICENSE" \
      "$out/share/doc/libretro-wasm4/wasm3-LICENSE"
    install -Dm644 "$src/runtimes/native/vendor/libretro/include/libretro.h" \
      "$out/share/doc/libretro-wasm4/libretro.h"
    runHook postInstall
  '';
  meta = {
    description = "WASM-4 native libretro runtime";
    homepage = "https://wasm4.org";
    license = [
      lib.licenses.isc
      lib.licenses.mit
    ];
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
  };
}

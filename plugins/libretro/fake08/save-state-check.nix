# Native headless ABI test. Build and run on build machines, never handhelds.
# `tests` permits the same harness to isolate regressions on unpatched cores.
{
  pkgs,
  core,
  tests ? [
    "running"
    "autoload"
    "reload"
  ],
}:
let
  fixtures = pkgs.applyPatches {
    name = "fake08-save-state-fixtures";
    src = core.src;
    patches = [ ./eris-save-states.patch ];
  };
in
pkgs.runCommand "fake08-save-state-check"
  {
    nativeBuildInputs = [ pkgs.stdenv.cc ];
  }
  ''
    $CC -std=c11 -Wall -Wextra -Werror -pedantic \
      -I${core.src}/platform/libretro ${./save-state-check.c} \
      ${core}/lib/retroarch/cores/fake08_libretro.so \
      -Wl,-rpath,${core}/lib/retroarch/cores -o harness
    cp ${fixtures}/test/carts/savestatetest.p8 "$PWD/cart.p8"
    for loading in memory path; do
      ./harness "$PWD/cart.p8" save state.bin "$loading"
      ${pkgs.lib.concatMapStringsSep "\n" (test: ''
        ./harness "$PWD/cart.p8" ${test} state.bin "$loading"
      '') tests}
    done
    touch "$out"
  ''

{
  pkgs,
  package,
  contract,
}:
let
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
  probe = import ./probe.nix { inherit pkgs; };
in
pkgs.runCommand "korri-pyxel-native-check"
  {
    nativeBuildInputs = [
      pkgs.bun
      pkgs.typescript
      pkgs.pkg-config
      pkgs.stdenv.cc
    ];
    buildInputs = [ pkgs.SDL2 ];
  }
  ''
    export HOME="$TMPDIR/home"
    export KORRI_NATIVE_PROOF_DIR="$TMPDIR/native-proof"
    mkdir -p "$HOME" work/plugins/pyxel work/contracts/generated
    cp ${package}/plugin.ts work/plugins/pyxel/
    cp ${contractSource} work/contracts/generated/korrid.ts
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler work/plugins/pyxel/plugin.ts
    cp ${./launch.test.ts} work/plugins/pyxel/launch.test.ts
    bun ./work/plugins/pyxel/launch.test.ts "$PWD/plans" ${package}/bin/unused
    # Test producer only; never in the game/plugin closure. Keep SDL loaded for
    # Python's later dynamic import, then push Start after the real window exists.
    cc -shared -fPIC ${../bitsybox/start-button-probe.c} \
      $(pkg-config --cflags sdl2) -Wl,--no-as-needed $(pkg-config --libs sdl2) -pthread -ldl -o "$PWD/start-probe.so"
    export KORRI_START_PROBE="$PWD/start-probe.so"
    ${probe}/bin/korri-pyxel-native-probe ${package}
    test -s "$KORRI_NATIVE_PROOF_DIR/pyxel.png"
    touch "$out"
  ''

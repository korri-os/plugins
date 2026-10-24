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
  # Test producer only. It pushes real SDL controller events after a real window
  # is observed; it never ships in the runtime closure.
  source = pkgs.lib.fileset.toSource {
    root = ../..;
    fileset = pkgs.lib.fileset.unions [
      ./.
      ../libretro/native-check/plan.ts
    ];
  };
in
pkgs.runCommand "korri-pyxel-native-check"
  {
    nativeBuildInputs = [
      pkgs.bun
      pkgs.python3
      pkgs.typescript
      pkgs.xvfb-run
      pkgs.xdotool
      pkgs.xprop
      pkgs.openbox
      pkgs.pkg-config
      pkgs.stdenv.cc
    ];
    buildInputs = [ pkgs.SDL2 ];
  }
  ''
    export HOME="$TMPDIR/home"
    export SDL_VIDEODRIVER=x11
    export LD_LIBRARY_PATH=${
      pkgs.lib.makeLibraryPath [
        pkgs.libglvnd
        pkgs.mesa
      ]
    }
    export LIBGL_DRIVERS_PATH=${pkgs.mesa}/lib/dri
    export LIBGL_ALWAYS_SOFTWARE=1
    export __EGL_VENDOR_LIBRARY_FILENAMES=${pkgs.mesa}/share/glvnd/egl_vendor.d/50_mesa.json
    export XDG_RUNTIME_DIR="$TMPDIR/xdg-runtime"
    mkdir -m700 "$XDG_RUNTIME_DIR"
    mkdir -p "$HOME" work/plugins/pyxel work/contracts/generated
    cp ${package}/plugin.ts work/plugins/pyxel/
    cp ${contractSource} work/contracts/generated/korrid.ts
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler work/plugins/pyxel/plugin.ts
    cp ${./launch.test.ts} work/plugins/pyxel/launch.test.ts
    bun ./work/plugins/pyxel/launch.test.ts "$PWD/plans" ${package}/bin/unused
    cc -shared -fPIC ${../bitsybox/start-button-probe.c} \
      $(pkg-config --cflags sdl2) -Wl,--no-as-needed $(pkg-config --libs sdl2) -pthread -ldl -o "$PWD/start-probe.so"
    export KORRI_START_PROBE="$PWD/start-probe.so"
    xvfb-run -a sh -c '
      openbox --sm-disable > "$TMPDIR/openbox.log" 2>&1 &
      wm=$!
      trap "kill $wm" EXIT
      for attempt in $(seq 1 100); do
        xprop -root _NET_SUPPORTING_WM_CHECK | grep -q "window id" && break
        sleep 0.05
      done
      python3 ${source}/plugins/pyxel/runtime.py ${package}
    '
    touch "$out"
  ''

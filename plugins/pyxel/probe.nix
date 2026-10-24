# Optional controlled acceptance tool. Never included in plugin closures.
{ pkgs }:
let
  source = pkgs.lib.fileset.toSource {
    root = ../..;
    fileset = pkgs.lib.fileset.unions [
      ./.
      ../libretro/native-check/plan.ts
    ];
  };
in
pkgs.writeShellApplication {
  name = "korri-pyxel-native-probe";
  runtimeInputs = [
    pkgs.python3
    pkgs.bun
    pkgs.xvfb-run
    pkgs.xdotool
    pkgs.xprop
    pkgs.openbox
    pkgs.imagemagick
  ];
  text = ''
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
    export XDG_RUNTIME_DIR
    XDG_RUNTIME_DIR=$(mktemp -d)
    trap 'rm -rf "$XDG_RUNTIME_DIR"' EXIT
    # The child shell expands its own variables after Xvfb starts.
    # shellcheck disable=SC2016
    xvfb-run -a sh -c '
      openbox --sm-disable > "$XDG_RUNTIME_DIR/openbox.log" 2>&1 &
      wm=$!
      trap "kill $wm" EXIT
      for attempt in $(seq 1 100); do
        xprop -root _NET_SUPPORTING_WM_CHECK | grep -q "window id" && break
        sleep 0.05
      done
      python3 ${source}/plugins/pyxel/runtime.py "$@"
    ' probe "$@"
  '';
}

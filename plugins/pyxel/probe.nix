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
    pkgs.mesa-demos
  ];
  text = ''
    export SDL_VIDEODRIVER=x11
    # Xvfb must initialize GLX before the client starts. Use nixpkgs' complete
    # software stack for both processes, including GBM (whose default searches
    # /run/opengl-driver and can otherwise mix the host's Mesa with this one).
    export LD_LIBRARY_PATH=${pkgs.libglvnd}/lib
    # shellcheck source=/dev/null
    source ${pkgs.mesa.llvmpipeHook}/nix-support/setup-hook
    export XDG_RUNTIME_DIR
    XDG_RUNTIME_DIR=$(mktemp -d)
    trap 'rm -rf "$XDG_RUNTIME_DIR"' EXIT
    # The child shell expands its own variables after Xvfb starts.
    # shellcheck disable=SC2016
    xvfb-run -a -e /dev/stderr sh -c '
      graphics_log="$XDG_RUNTIME_DIR/glxinfo.log"
      if ! glxinfo -B > "$graphics_log" 2>&1 || ! grep -q "OpenGL renderer string: llvmpipe" "$graphics_log"; then
        cat "$graphics_log" >&2
        echo "Pinned software GLX did not initialize before Pyxel" >&2
        exit 1
      fi
      if [ -n "''${KORRI_NATIVE_PROOF_DIR:-}" ]; then
        mkdir -p "$KORRI_NATIVE_PROOF_DIR"
        cp "$graphics_log" "$KORRI_NATIVE_PROOF_DIR/glxinfo.log"
      fi
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

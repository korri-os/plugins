# Optional live acceptance tool. Never included in game/plugin closures.
{ pkgs }:
pkgs.writeShellApplication {
  name = "korri-libretro-native-probe";
  runtimeInputs = [
    pkgs.python3
    pkgs.bun
    pkgs.xvfb-run
  ];
  text = ''
    export SDL_VIDEODRIVER=x11 SDL_RENDER_DRIVER=software
    export XDG_RUNTIME_DIR
    XDG_RUNTIME_DIR=$(mktemp -d)
    trap 'rm -rf "$XDG_RUNTIME_DIR"' EXIT
    xvfb-run -a python3 ${./.}/runtime.py "$@"
  '';
}

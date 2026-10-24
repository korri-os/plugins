# The publisher's locked nixpkgs owns Pyxel's source + Cargo source pins.
# Reuse its cached native engine rather than rebuild it to add a launcher.
{ pkgs }:
let
  engine = pkgs.pyxel;
in
assert pkgs.lib.assertMsg (
  engine.version == "2.9.9"
) "Review Pyxel startup behavior before updating";
pkgs.writeShellScriptBin "korri-pyxel" ''
  export PYTHONPATH=${engine}/${pkgs.python3.sitePackages}
  export PYTHONNOUSERSITE=1
  exec ${pkgs.python3.interpreter} ${./launch.py} "$@"
''

# The publisher's locked nixpkgs owns Pyxel's source + Cargo source pins.
# Reuse its cached native engine, but do not ship its third-party sample carts.
{ pkgs }:
let
  engine = pkgs.pyxel;
  runtime =
    pkgs.runCommand "pyxel-runtime-${engine.version}"
      {
        # A copied bytecode filename must not pull the unfiltered samples back into
        # the runtime closure. Source and native module do not refer to that output.
        disallowedReferences = [ engine ];
      }
      ''
        mkdir -p "$out/${pkgs.python3.sitePackages}"
        cp -r ${engine}/${pkgs.python3.sitePackages}/pyxel "$out/${pkgs.python3.sitePackages}/pyxel"
        chmod -R u+w "$out"
        rm -r "$out/${pkgs.python3.sitePackages}/pyxel/examples"
        find "$out" -type d -name __pycache__ -prune -exec rm -r {} +
        test -z "$(find "$out" -name '*.pyxapp' -print -quit)"
      '';
in
assert pkgs.lib.assertMsg (
  engine.version == "2.9.9"
) "Review Pyxel startup behavior before updating";
(pkgs.writeShellScriptBin "korri-pyxel" ''
  export PYTHONPATH=${runtime}/${pkgs.python3.sitePackages}
  export PYTHONNOUSERSITE=1
  exec ${pkgs.python3.interpreter} ${./launch.py} "$@"
'').overrideAttrs
  (_: {
    passthru = { inherit runtime; };
  })

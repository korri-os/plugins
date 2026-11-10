# Core exports korrid.ts as an isolated file. Its ./surface import comes from
# Core's generated surface treaty. Retain only these two consumed sources.
{
  pkgs,
  contract,
  surface,
}:
let
  surfaceSource = builtins.path {
    path = surface;
    name = "surface.ts";
  };
in
pkgs.runCommand "plugin-contract" { } ''
  mkdir -p "$out"
  cp ${contract} "$out/korrid.ts"
  cp ${surfaceSource} "$out/surface.ts"
''

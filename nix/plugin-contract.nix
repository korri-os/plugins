# Core exports korrid.ts as an isolated file. Its ./surface import comes from
# Core's generated surface treaty. Shared setting identifiers are a third
# generated dependency. Keep the full consumed treaty together for each check.
{
  pkgs,
  contract,
  surface,
  settings,
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
  cp ${settings} "$out/settings.ts"
''

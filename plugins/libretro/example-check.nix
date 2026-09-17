# Keep the committed catalogue example equal to the source that mGBA ships.
{ pkgs, mkPlugin }:
let
  libretro = import ./default.nix { inherit pkgs mkPlugin; };
  generated = libretro.packages."korri-plugin-mgba".generatedPlugin;
  committed = ./examples/mgba.plugin.ts;
in
pkgs.runCommand "korri-libretro-example-check" { } ''
  if ! diff -u ${committed} ${generated}; then
    echo "plugins/libretro/examples/mgba.plugin.ts is stale." >&2
    echo "Regenerate it from the mgba catalogue entry." >&2
    exit 1
  fi
  touch "$out"
''

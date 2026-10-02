{
  pkgs,
  package,
  cartridges,
  fake08Plugin,
}:
let
  source = ../plugins/starter-pack;
  originals = import (source + /cartridges.nix) { inherit pkgs; };
  # Read fetchurl's real pins, not a second cartridge inventory.
  pins = pkgs.writeText "starter-pack-original-fetchurl-pins.json" (
    builtins.toJSON (map (cart: { inherit (cart) name outputHash url; }) originals)
  );
  python = pkgs.python3.withPackages (packages: [ packages.pillow ]);
in
pkgs.runCommand "korri-starter-pack-package-check" { } ''
  payload=${cartridges}/share/starter-pack
  ${python}/bin/python ${./check-starter-pack.py} \
    "$payload" ${pins} ${package} ${fake08Plugin}
  ${pkgs.typescript}/bin/tsc --noEmit --strict --target es2022 ${package}/plugin.ts
  for file in CREDITS.md README.md CC-BY-NC-SA-4.0.txt; do
    cmp ${source}/"$file" "$payload/$file"
  done
  diff -r ${source}/notices "$payload/notices"
  touch "$out"
''

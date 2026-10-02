{ pkgs }:
let
  originals = import ./cartridges.nix { inherit pkgs; };
in
pkgs.runCommand "korri-starter-pack-cartridges" { } ''
  destination="$out/share/starter-pack"
  mkdir -p "$destination/cartridges" "$destination/notices"
  ${pkgs.lib.concatMapStringsSep "\n" (
    cart: "cp ${cart} \"$destination/cartridges/${cart.name}\""
  ) originals}
  cp ${./CREDITS.md} "$destination/CREDITS.md"
  cp ${./README.md} "$destination/README.md"
  cp ${./CC-BY-NC-SA-4.0.txt} "$destination/CC-BY-NC-SA-4.0.txt"
  cp ${./notices}/*.txt "$destination/notices/"
  cd "$destination/cartridges"
  sha256sum -- *.p8.png > "$destination/SHA256SUMS"
''

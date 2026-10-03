{ pkgs }:
let
  originals = import ./cartridges.nix { inherit pkgs; };
  quests = import ./solarus-quests.nix { inherit pkgs; };
  solarusNotices = import ./solarus-notices.nix { inherit pkgs; };
in
pkgs.runCommand "korri-starter-pack-cartridges" { } ''
  destination="$out/share/starter-pack"
  mkdir -p "$destination/cartridges" "$destination/notices"
  ${pkgs.lib.concatMapStringsSep "\n" (
    cart: "cp ${cart} \"$destination/cartridges/${cart.name}\""
  ) originals}
  ${pkgs.lib.concatMapStringsSep "\n" (quest: ''
    ${pkgs.python3}/bin/python ${./package-solarus-quest.py} ${quest} \
      ${
        pkgs.lib.escapeShellArgs [
          quest.name
          quest.url
          quest.outputHash
        ]
      } "$destination"
  '') quests}
  mkdir -p "$destination/notices/solarus-licenses"
  ${pkgs.lib.concatMapStringsSep "\n" (
    license: "cp ${license} \"$destination/notices/solarus-licenses/${license.name}\""
  ) solarusNotices.licenses}
  cp ${./SOLARUS-PROVENANCE.md} "$destination/notices/solarus-licenses/PROVENANCE.md"
  ${pkgs.python3}/bin/python ${./package-solarus-quest.py} --credits \
    ${solarusNotices.credits} "$destination/notices/voadi"
  cp ${./CREDITS.md} "$destination/CREDITS.md"
  cp ${./README.md} "$destination/README.md"
  cp ${./CC-BY-NC-SA-4.0.txt} "$destination/CC-BY-NC-SA-4.0.txt"
  cp ${./notices}/*.txt "$destination/notices/"
  cd "$destination/cartridges"
  sha256sum -- *.p8.png *.solarus > "$destination/SHA256SUMS"
''

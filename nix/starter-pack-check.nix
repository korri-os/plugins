{
  pkgs,
  package,
  cartridges,
  fake08Plugin,
  solarusPlugin,
  zquestPlugin,
}:
let
  source = ../plugins/starter-pack;
  originals = import (source + /cartridges.nix) { inherit pkgs; };
  quests = import (source + /solarus-quests.nix) { inherit pkgs; };
  solarusNotices = import (source + /solarus-notices.nix) { inherit pkgs; };
  # Read the producers' real fetchurl pins, never a second source inventory.
  pins = pkgs.writeText "starter-pack-original-fetchurl-pins.json" (
    builtins.toJSON (map (cart: { inherit (cart) name outputHash url; }) originals)
  );
  questPins = pkgs.writeText "starter-pack-quest-fetchurl-pins.json" (
    builtins.toJSON (
      map (quest: {
        inherit (quest) name outputHash url;
        # An attrset with outPath serializes as a JSON string. This test-only
        # field keeps the actual fetchurl output without that special coercion.
        sourcePath = toString quest;
      }) quests
    )
  );
  # Original PICO notices still compare byte-for-byte. Independently compare
  # generated quest notices with the original tarballs in check-starter-pack.py.
  questNoticeExclusions = pkgs.lib.escapeShellArgs (
    map (quest: "--exclude=${pkgs.lib.removeSuffix ".tar.gz" quest.name}") quests
  );
  python = pkgs.python3.withPackages (packages: [ packages.pillow ]);
in
pkgs.runCommand "korri-starter-pack-package-check" { } ''
  payload=${cartridges}/share/starter-pack
  # Evaluate the packaged plugin.ts itself, so the check reads the declared
  # games exactly as published rather than a second copy of them.
  mkdir -p "$TMPDIR/declaration"
  echo '{"type":"module"}' > "$TMPDIR/declaration/package.json"
  ${pkgs.typescript}/bin/tsc --target es2022 --module es2022 \
    --outDir "$TMPDIR/declaration" ${package}/plugin.ts
  ${pkgs.nodejs}/bin/node --input-type=module -e \
    "import * as plugin from '$TMPDIR/declaration/plugin.js'; console.log(JSON.stringify(plugin.games))" \
    > "$TMPDIR/games.json"
  ${python}/bin/python ${./check-starter-pack.py} \
    "$payload" ${pins} ${questPins} ${package} ${fake08Plugin} ${solarusPlugin} ${zquestPlugin} \
    "$TMPDIR/games.json"
  ${pkgs.typescript}/bin/tsc --noEmit --strict --target es2022 ${package}/plugin.ts
  for file in CREDITS.md README.md CC-BY-NC-SA-4.0.txt; do
    cmp ${source}/"$file" "$payload/$file"
  done
  diff -r ${questNoticeExclusions} --exclude=solarus-licenses --exclude=lantern-hollow ${source}/notices "$payload/notices"
  cmp ${source}/lantern-hollow/lantern-hollow.qst "$payload/cartridges/lantern-hollow.qst"
  for file in README.md ASSETS.md LICENSE.txt; do
    cmp ${source}/lantern-hollow/"$file" "$payload/notices/lantern-hollow/$file"
  done
  diff -r ${source}/lantern-hollow/source "$payload/notices/lantern-hollow/source"
  ${pkgs.lib.concatMapStringsSep "\n" (
    license: "cmp ${license} \"$payload/notices/solarus-licenses/${license.name}\""
  ) solarusNotices.licenses}
  cmp ${source}/SOLARUS-PROVENANCE.md "$payload/notices/solarus-licenses/PROVENANCE.md"
  ${python}/bin/python ${./check-solarus-credits.py} ${solarusNotices.credits} "$payload/notices/voadi"
  touch "$out"
''

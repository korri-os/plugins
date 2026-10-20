# Build-time metadata only. Evaluate the actual source with Core's closed module
# loader; do not parse TypeScript or import a derivation during Nix evaluation.
{
  pkgs,
  evaluator,
  source ? ../plugin.ts,
}:
pkgs.runCommand "proton-cachyos-tool-name" { nativeBuildInputs = [ pkgs.jq ]; } ''
  mkdir source
  cp ${source} source/plugin.ts
  ${evaluator}/bin/korri-publish declaration @korri "$PWD/source" plugin.ts > declaration.json
  jq -er '
    select(.name == "proton" and .artifacts.cachyos.id == "@korri:proton/cachyos") |
    .artifacts.cachyos.version | select(type == "string" and test("^[A-Za-z0-9][A-Za-z0-9._+-]*$")) |
    "proton-cachyos-" + .
  ' declaration.json > "$out"
''

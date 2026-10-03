{
  pkgs,
  package,
  fake08Plugin,
  solarusPlugin,
  hostPackage,
}:
let
  # Existing PublisherBindings schema. This test key grants no trust and never
  # signs anything; image-time seeding only computes immutable approval digests.
  bindings = pkgs.writeText "starter-pack-test-publishers.json" (
    builtins.toJSON {
      "@korri" = {
        publicKey = "starter-pack-test:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
        cacheUrl = "https://cache.example.invalid";
      };
    }
  );
in
# Host composition is a check input only. Seed the three explicit exact roots,
# as Core image composition does, without reading or writing host state. These
# digest checks do not replace runtime signatures, bindings or exact approvals.
pkgs.runCommand "korri-starter-pack-admission" { nativeBuildInputs = [ pkgs.jq ]; } ''
  mkdir -p "$out"
  ${hostPackage}/bin/korri-plugin seed-graph ${bindings} \
    ${package} ${fake08Plugin} ${solarusPlugin} > "$out/receipts.json"
  jq -e --arg pack ${package} --arg fake08 ${fake08Plugin} --arg solarus ${solarusPlugin} '
    length == 3 and
    (map({id, package}) | sort_by(.id)) == [
      {id: "@korri:fake08", package: $fake08},
      {id: "@korri:solarus", package: $solarus},
      {id: "@korri:starter-pack", package: $pack}
    ] and
    .[2].id == "@korri:starter-pack" and
    all(.[];
      .desired.state == "Enabled" and .previous == null and
      .provenance == {kind: "RawCache", cache_url: "https://cache.example.invalid"} and
      (.approval | test("^[0-9a-f]{64}$")))
  ' "$out/receipts.json"

  # Both existing leaves retain the complete standalone receipt and approval.
  # Select by identity: unrelated leaves are ordered by their exact store paths.
  ${hostPackage}/bin/korri-plugin seed \
    ${fake08Plugin} https://cache.example.invalid > fake08-leaf.json
  jq -S . fake08-leaf.json > fake08-leaf-sorted.json
  jq -S '.[] | select(.id == "@korri:fake08")' "$out/receipts.json" > graph-fake08.json
  cmp fake08-leaf-sorted.json graph-fake08.json
  ${hostPackage}/bin/korri-plugin seed \
    ${solarusPlugin} https://cache.example.invalid > solarus-leaf.json
  jq -S . solarus-leaf.json > solarus-leaf-sorted.json
  jq -S '.[] | select(.id == "@korri:solarus")' "$out/receipts.json" > graph-solarus.json
  cmp solarus-leaf-sorted.json graph-solarus.json

  # Repeated selections and reordered roots must produce identical receipts.
  ${hostPackage}/bin/korri-plugin seed-graph ${bindings} \
    ${package} ${fake08Plugin} ${solarusPlugin} > repeated.json
  cmp "$out/receipts.json" repeated.json
  ${hostPackage}/bin/korri-plugin seed-graph ${bindings} \
    ${solarusPlugin} ${fake08Plugin} ${package} > reordered.json
  cmp "$out/receipts.json" reordered.json

  if ${hostPackage}/bin/korri-plugin seed-graph ${bindings} \
    ${package} ${solarusPlugin} > missing-fake08.json 2> missing-fake08-error; then
    echo 'starter-pack admission accepted a missing selected FAKE-08 output' >&2
    exit 1
  fi
  grep -Fq 'missing exact selected dependency ${fake08Plugin}' missing-fake08-error
  if ${hostPackage}/bin/korri-plugin seed-graph ${bindings} \
    ${package} ${fake08Plugin} > missing-solarus.json 2> missing-solarus-error; then
    echo 'starter-pack admission accepted a missing selected Solarus output' >&2
    exit 1
  fi
  grep -Fq 'missing exact selected dependency ${solarusPlugin}' missing-solarus-error
  if ${hostPackage}/bin/korri-plugin seed-graph ${bindings} ${package} \
    > missing.json 2> missing-error; then
    echo 'starter-pack admission accepted both missing selected runtime outputs' >&2
    exit 1
  fi
  grep -Fq 'missing exact selected dependency' missing-error
  # Core refuses duplicate roots; stability must not weaken that admission rule.
  if ${hostPackage}/bin/korri-plugin seed-graph ${bindings} \
    ${package} ${fake08Plugin} ${solarusPlugin} ${fake08Plugin} \
    > duplicate.json 2> duplicate-error; then
    echo 'starter-pack admission accepted a duplicate selected output' >&2
    exit 1
  fi
  grep -Fq 'duplicate selected plugin output' duplicate-error
''

{
  pkgs,
  package,
  fake08Plugin,
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
# Host composition is a check input only. Seed the complete explicit selection,
# as Core image composition does, without reading or writing host state.
pkgs.runCommand "korri-starter-pack-admission" { nativeBuildInputs = [ pkgs.jq ]; } ''
  mkdir -p "$out"
  ${hostPackage}/bin/korri-plugin seed-graph ${bindings} \
    ${package} ${fake08Plugin} > "$out/receipts.json"
  jq -e --arg pack ${package} --arg runtime ${fake08Plugin} '
    length == 2 and
    .[0].id == "@korri:fake08" and .[0].package == $runtime and
    .[1].id == "@korri:starter-pack" and .[1].package == $pack and
    all(.[];
      .desired.state == "Enabled" and .previous == null and
      .provenance == {kind: "RawCache", cache_url: "https://cache.example.invalid"} and
      (.approval | test("^[0-9a-f]{64}$")))
  ' "$out/receipts.json"
  # The leaf's existing approval must remain unchanged in the selected graph.
  ${hostPackage}/bin/korri-plugin seed \
    ${fake08Plugin} https://cache.example.invalid > leaf.json
  jq -S . leaf.json > leaf-sorted.json
  jq -S '.[0]' "$out/receipts.json" > graph-leaf.json
  cmp leaf-sorted.json graph-leaf.json
  # Root order and repeated reads must not change the approved exact graph.
  ${hostPackage}/bin/korri-plugin seed-graph ${bindings} \
    ${fake08Plugin} ${package} > repeated.json
  cmp "$out/receipts.json" repeated.json
  if ${hostPackage}/bin/korri-plugin seed-graph ${bindings} ${package} \
    > missing.json 2> missing-error; then
    echo 'starter-pack admission accepted a missing selected FAKE-08 output' >&2
    exit 1
  fi
  grep -Fq 'missing exact selected dependency' missing-error
''

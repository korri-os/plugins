{
  pkgs,
  package,
  fake08Plugin,
  solarusPlugin,
  zquestPlugin,
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
  seed = "${hostPackage}/bin/korri-plugin";
in
# Host composition is a check input only. Seed the four explicit exact roots,
# as Core image composition does, without reading or writing host state. These
# digest checks do not replace runtime signatures, bindings or exact approvals.
pkgs.runCommand "korri-starter-pack-admission" { nativeBuildInputs = [ pkgs.jq ]; } ''
  mkdir -p "$out"
  ${seed} seed-graph ${bindings} \
    ${package} ${fake08Plugin} ${solarusPlugin} ${zquestPlugin} > "$out/receipts.json"
  jq -e --arg pack ${package} --arg fake08 ${fake08Plugin} --arg solarus ${solarusPlugin} \
    --arg zquest ${zquestPlugin} '
    length == 4 and
    (map({id, package}) | sort_by(.id)) == [
      {id: "@korri:fake08", package: $fake08},
      {id: "@korri:solarus", package: $solarus},
      {id: "@korri:starter-pack", package: $pack},
      {id: "@korri:zquest-classic", package: $zquest}
    ] and
    .[3].id == "@korri:starter-pack" and
    all(.[];
      .desired.state == "Enabled" and .previous == null and
      .provenance == {kind: "RawCache", cache_url: "https://cache.example.invalid"} and
      (.approval | test("^[0-9a-f]{64}$")))
  ' "$out/receipts.json"

  # Every runtime leaf retains the complete standalone receipt and approval.
  # Select by identity: unrelated leaves are ordered by their exact store paths.
  for leaf in fake08:${fake08Plugin} solarus:${solarusPlugin} zquest-classic:${zquestPlugin}; do
    id="''${leaf%%:*}"; path="''${leaf#*:}"
    ${seed} seed "$path" https://cache.example.invalid > "$id-leaf.json"
    jq -S . "$id-leaf.json" > "$id-leaf-sorted.json"
    jq -S --arg id "@korri:$id" '.[] | select(.id == $id)' "$out/receipts.json" > "graph-$id.json"
    cmp "$id-leaf-sorted.json" "graph-$id.json"
  done

  # Repeated selections and reordered roots must produce identical receipts.
  ${seed} seed-graph ${bindings} \
    ${package} ${fake08Plugin} ${solarusPlugin} ${zquestPlugin} > repeated.json
  cmp "$out/receipts.json" repeated.json
  ${seed} seed-graph ${bindings} \
    ${zquestPlugin} ${solarusPlugin} ${fake08Plugin} ${package} > reordered.json
  cmp "$out/receipts.json" reordered.json

  # Each missing runtime is refused by exact path.
  if ${seed} seed-graph ${bindings} \
    ${package} ${solarusPlugin} ${zquestPlugin} > missing-fake08.json 2> missing-fake08-error; then
    echo 'starter-pack admission accepted a missing selected FAKE-08 output' >&2
    exit 1
  fi
  grep -Fq 'missing exact selected dependency ${fake08Plugin}' missing-fake08-error
  if ${seed} seed-graph ${bindings} \
    ${package} ${fake08Plugin} ${zquestPlugin} > missing-solarus.json 2> missing-solarus-error; then
    echo 'starter-pack admission accepted a missing selected Solarus output' >&2
    exit 1
  fi
  grep -Fq 'missing exact selected dependency ${solarusPlugin}' missing-solarus-error
  if ${seed} seed-graph ${bindings} \
    ${package} ${fake08Plugin} ${solarusPlugin} > missing-zquest.json 2> missing-zquest-error; then
    echo 'starter-pack admission accepted a missing selected ZQuest Classic output' >&2
    exit 1
  fi
  grep -Fq 'missing exact selected dependency ${zquestPlugin}' missing-zquest-error
  if ${seed} seed-graph ${bindings} ${package} \
    > missing.json 2> missing-error; then
    echo 'starter-pack admission accepted all missing selected runtime outputs' >&2
    exit 1
  fi
  grep -Fq 'missing exact selected dependency' missing-error
  # Core refuses duplicate roots; stability must not weaken that admission rule.
  if ${seed} seed-graph ${bindings} \
    ${package} ${fake08Plugin} ${solarusPlugin} ${zquestPlugin} ${fake08Plugin} \
    > duplicate.json 2> duplicate-error; then
    echo 'starter-pack admission accepted a duplicate selected output' >&2
    exit 1
  fi
  grep -Fq 'duplicate selected plugin output' duplicate-error
''

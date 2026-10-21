# Package, admission and offline unit checks for one acquisition plugin
# (@korri:pico8, @korri:homebrewhub, @korri:retrobrews). The package must hold
# only the generated manifest and plugin.ts: tests, fixtures and live probes
# stay in this repository. Nothing here reaches the network.
{
  pkgs,
  package,
  name,
  hosts,
  contract,
  hostPackage,
}:
let
  # A store-root string retains the whole Korri checkout as an input. Copy
  # only the consumed contract so unrelated core files cannot invalidate tsc.
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
  pluginDir = ../plugins + "/${name}";
  tests = pkgs.lib.fileset.toSource {
    root = pluginDir;
    fileset = pkgs.lib.fileset.unions [
      (pluginDir + "/plugin.test.ts")
      (pluginDir + "/fixtures")
    ];
  };
  expectedHosts = builtins.toJSON hosts;
in
pkgs.runCommand "korri-${name}-plugin-check"
  {
    nativeBuildInputs = [
      pkgs.bun
      pkgs.jq
      pkgs.typescript
    ];
  }
  ''
    jq -e --argjson hosts '${expectedHosts}' '
      .publisher == {namespace: "@korri"} and
      .entry == "plugin.ts" and .sources == ["plugin.ts"] and
      .packages == {} and .files == {} and .services == {} and .ports == {} and
      (has("requires") | not) and
      (if $hosts == [] then (has("hosts") | not) else .hosts == $hosts end)
    ' ${package}/manifest.json
    (cd ${package} && find . -mindepth 1 | sort) > contents.txt
    printf '%s\n' ./manifest.json ./plugin.ts | diff -u - contents.txt
    ${hostPackage}/bin/korri-plugin seed ${package} https://cache.example.invalid > receipt.json
    jq -e '.id == "@korri:${name}" and .desired.state == "Enabled" and .previous == null' receipt.json
    mkdir -p work/plugins/${name} work/contracts/generated
    cp ${package}/plugin.ts work/plugins/${name}/plugin.ts
    cp -R --no-preserve=mode ${tests}/. work/plugins/${name}/
    cp ${contractSource} work/contracts/generated/korrid.ts
    cd work
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler plugins/${name}/plugin.ts
    bun test plugins/${name}/plugin.test.ts
    touch "$out"
  ''

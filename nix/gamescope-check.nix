{
  pkgs,
  package,
  gamescopePackage,
  contract,
}:
let
  # The option table as built: upstream source plus every package patch.
  patchedSource = pkgs.applyPatches {
    name = "gamescope-${gamescopePackage.version}-patched-source";
    inherit (gamescopePackage) src patches;
  };
in
pkgs.runCommand "korri-gamescope-plugin-check"
  {
    nativeBuildInputs = [
      pkgs.bun
      pkgs.typescript
      pkgs.jq
      pkgs.python3
    ];
  }
  ''
    jq -e --arg gamescope '${gamescopePackage}' '
      .publisher == {namespace: "@korri"} and
      .entry == "plugin.ts" and .sources == ["compose.ts", "plugin.ts"] and
      (.packages | keys) == ["display-change", "gamescope"] and
      .packages.gamescope == $gamescope and
      .files == {gamescope: ($gamescope + "/bin/gamescope"), "display-change": (.packages["display-change"] + "/bin/gamescope-display-change")} and
      .services == {} and .ports == {}
    ' ${package}/manifest.json
    test -x ${gamescopePackage}/bin/gamescope
    test -x "$(jq -r '.files["display-change"]' ${package}/manifest.json)"
    ${gamescopePackage}/bin/gamescope --version 2> version.txt
    grep -F '${gamescopePackage.version}' version.txt
    ${gamescopePackage}/bin/gamescope --help > help.txt 2>&1
    for flag in backend fullscreen expose-wayland; do
      grep -F -- "--$flag" help.txt
    done
    mkdir -p work/plugins/gamescope work/contracts/generated
    cp ${package}/*.ts work/plugins/gamescope/
    cp ${../plugins/gamescope/compose.test.ts} work/plugins/gamescope/compose.test.ts
    cp ${../plugins/gamescope/display-change.sh} work/plugins/gamescope/display-change.sh
    cp ${../plugins/gamescope/test-display-change.py} work/plugins/gamescope/test-display-change.py
    cp -r ${contract}/. work/contracts/generated/
    cd work
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler plugins/gamescope/plugin.ts
    bun test plugins/gamescope/compose.test.ts
    python3 plugins/gamescope/test-display-change.py
    cp ${./gamescope-options-check.ts} gamescope-options-check.ts
    bun gamescope-options-check.ts ${patchedSource}/src/main.cpp ${gamescopePackage}/bin/gamescope
    touch "$out"
  ''

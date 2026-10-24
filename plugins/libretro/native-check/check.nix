# Four selected cores only; reusable on native x86_64 and ARM64 build hosts.
{
  pkgs,
  packages,
  contract,
}:
let
  selected = pkgs.lib.getAttrs [ "tic80" "wasm4" "lowresnx" "pzretro" ] packages;
  packageList = pkgs.writeText "native-runner-packages.json" (builtins.toJSON selected);
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
in
pkgs.runCommand "korri-native-fantasy-runners-check"
  {
    nativeBuildInputs = [
      pkgs.bun
      pkgs.python3
      pkgs.wabt
      pkgs.xvfb-run
      pkgs.typescript
    ];
  }
  ''
    export HOME="$TMPDIR/home"
    mkdir -p "$HOME" fixtures work/plugins/libretro work/contracts/generated
    cp ${contractSource} work/contracts/generated/korrid.ts
    ${pkgs.lib.concatStringsSep "\n" (
      pkgs.lib.mapAttrsToList (name: package: ''
        mkdir -p work/plugins/${name}
        cp ${package}/*.ts work/plugins/${name}/
      '') selected
    )}
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler work/plugins/*/*.ts
    bun ${./launch.test.ts} ${packageList}
    cp ${./fixtures/game.nx} fixtures/game.nx
    cp ${./fixtures/game.pz} fixtures/game.pz
    wat2wasm ${./fixtures/game.wat} -o fixtures/game.wasm
    python3 - ${./fixtures/game.lua} "$PWD/fixtures/game.tic" <<'PY'
    import pathlib, struct, sys
    code = pathlib.Path(sys.argv[1]).read_bytes()
    pathlib.Path(sys.argv[2]).write_bytes(struct.pack('<BHB', 5, len(code), 0) + code)
    PY
    chmod -R a-w fixtures
    ${pkgs.lib.concatStringsSep "\n" (
      pkgs.lib.mapAttrsToList (
        name: package:
        let
          extension =
            {
              tic80 = "tic";
              wasm4 = "wasm";
              lowresnx = "nx";
              pzretro = "pz";
            }
            .${name};
        in
        ''
          xvfb-run -a python3 ${./.}/runtime.py ${package} ${name} "$PWD/fixtures/game.${extension}"
        ''
      ) selected
    )}
    touch "$out"
  ''

{
  pkgs,
  package,
  contract,
  hostPackage,
  korridPackage,
}:
let
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
  tsconfig = pkgs.writeText "skate3-plugin-tsconfig.json" (
    builtins.toJSON {
      compilerOptions = {
        target = "ES2022";
        module = "ESNext";
        moduleResolution = "Bundler";
        strict = true;
        noEmit = true;
        skipLibCheck = true;
      };
      include = [ "plugins/skate-3/plugin.ts" ];
    }
  );
in
pkgs.runCommand "korri-skate3-plugin-check"
  {
    nativeBuildInputs = [
      pkgs.bun
      pkgs.typescript
    ];
  }
  ''
    mkdir -p work/plugins/skate-3 work/contracts/generated work/nix
    cp ${package}/plugin.ts work/plugins/skate-3/plugin.ts
    cp ${contractSource} work/contracts/generated/korrid.ts
    cp ${./skate3-check.ts} work/nix/skate3-check.ts
    cp ${tsconfig} work/tsconfig.json
    cd work
    tsc --project tsconfig.json
    bun nix/skate3-check.ts ${package} \
      ${hostPackage}/bin/korri-plugin \
      ${korridPackage}/bin/korrid \
      ${pkgs.coreutils}/bin/env
    touch "$out"
  ''

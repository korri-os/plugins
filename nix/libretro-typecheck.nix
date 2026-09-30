{
  pkgs,
  helper,
  settings,
  contract,
}:
let
  # A store-root string retains the whole Korri checkout as an input. Copy
  # only the consumed contract so unrelated core files cannot invalidate tsc.
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
  tsconfig = pkgs.writeText "libretro-helper-tsconfig.json" (
    builtins.toJSON {
      compilerOptions = {
        target = "ES2022";
        module = "ESNext";
        moduleResolution = "Bundler";
        strict = true;
        noEmit = true;
        skipLibCheck = true;
      };
      include = [ "plugins/libretro/*.ts" ];
    }
  );
in
pkgs.runCommand "korri-libretro-helper-typecheck"
  {
    nativeBuildInputs = [ pkgs.typescript ];
  }
  ''
    mkdir -p work/plugins/libretro work/contracts/generated
    cp ${helper} work/plugins/libretro/retroarch.ts
    cp ${settings}/settings.ts work/plugins/libretro/settings.ts
    cp ${contractSource} work/contracts/generated/korrid.ts
    cp ${tsconfig} work/tsconfig.json
    cd work
    tsc --project tsconfig.json
    touch "$out"
  ''

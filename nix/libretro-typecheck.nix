{
  pkgs,
  helper,
  settings,
  contract,
}:
let
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
    cp ${contract} work/contracts/generated/korrid.ts
    cp ${tsconfig} work/tsconfig.json
    cd work
    tsc --project tsconfig.json
    touch "$out"
  ''

{
  pkgs,
  helper,
  settings,
  contract,
  plugins,
  catalogue,
}:
let
  # A store-root string retains the whole Korri checkout as an input. Copy
  # only the consumed contract so unrelated core files cannot invalidate tsc.
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
  # Keep nixpkgs' target restrictions. x86_64 checks every core; other targets
  # must not force unsupported native packages merely to check declarations.
  checkedCatalogue = pkgs.lib.filterAttrs (
    _: spec: pkgs.lib.meta.availableOn pkgs.stdenv.hostPlatform spec.core
  ) catalogue;
  generatedPlugins = pkgs.lib.concatStringsSep "\n" (
    pkgs.lib.mapAttrsToList (
      name: _: "cp ${plugins."korri-plugin-${name}".generatedPlugin} work/plugins/libretro/${name}.ts"
    ) checkedCatalogue
  );
  expectedSystems = pkgs.writeText "libretro-systems.json" (
    builtins.toJSON (builtins.mapAttrs (_: spec: spec.systems) checkedCatalogue)
  );
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
    nativeBuildInputs = [
      pkgs.typescript
      pkgs.bun
    ];
  }
  ''
    mkdir -p work/plugins/libretro work/contracts/generated
    ${generatedPlugins}
    cp ${helper} work/plugins/libretro/retroarch.ts
    cp ${settings}/settings.ts work/plugins/libretro/settings.ts
    cp ${contractSource} work/contracts/generated/korrid.ts
    cp ${tsconfig} work/tsconfig.json
    cd work
    tsc --project tsconfig.json
    bun ${../plugins/libretro/content-check.ts} plugins/libretro ${expectedSystems}
    touch "$out"
  ''

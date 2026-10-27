# Focused producer gate: actual installed declarations, independent native ABI
# probe, generator boundary tests and the helper's pinned launch contract.
{
  pkgs,
  plugins,
  contract,
}:
let
  snes = plugins.korri-plugin-snes9x2010;
  other = plugins.korri-plugin-fake08;
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
in
pkgs.runCommand "korri-libretro-netplay-check"
  {
    nativeBuildInputs = [
      pkgs.buildPackages.python3
      pkgs.buildPackages.bun
      pkgs.buildPackages.typescript
      pkgs.buildPackages.stdenv.cc
    ];
  }
  ''
    # Like RetroArch (and Python), supply libm symbols used by some cores.
    cc -Wall -Wextra -Werror ${./system-info-check.c} \
      -Wl,--no-as-needed -lm -ldl -o system-info-check
    bun ${./netplay-check.ts} ${snes} ${other} "$PWD/system-info-check" \
      ${snes.coreInfo}
    cp ${./generate-netplay.py} generate-netplay.py
    cp ${./test_generate_netplay.py} test_generate_netplay.py
    python3 test_generate_netplay.py

    mkdir -p work/plugins/libretro work/contracts/generated
    cp ${snes}/*.ts work/plugins/libretro/
    mv work/plugins/libretro/plugin.ts work/plugins/libretro/snes9x2010.ts
    cp ${other}/plugin.ts work/plugins/libretro/fake08.ts
    cp ${contractSource} work/contracts/generated/korrid.ts
    cd work
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler plugins/libretro/*.ts
    touch "$out"
  ''

# Strict checks against the current Core treaty, not the publisher's old pin.
{ pkgs, contract }:
pkgs.runCommand "steam-runtime-declarations-check"
  {
    nativeBuildInputs = [
      pkgs.typescript
      pkgs.bun
    ];
  }
  ''
    mkdir -p work/plugins/{steam,fex,proton} work/contracts/generated
    cp ${contract} work/contracts/generated/korrid.ts
    cp ${../plugin.ts} work/plugins/steam/plugin.ts
    cp ${../plugin.test.ts} work/plugins/steam/plugin.test.ts
    cp ${../../fex/plugin.ts} work/plugins/fex/plugin.ts
    cp ${../../proton/plugin.ts} work/plugins/proton/plugin.ts
    cd work
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler plugins/{steam,fex,proton}/plugin.ts
    bun test plugins/steam/plugin.test.ts
    touch "$out"
  ''

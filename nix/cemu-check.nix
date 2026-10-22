{
  pkgs,
  package,
  cemuPackage,
  contract,
}:
let
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
in
pkgs.runCommand "korri-cemu-package-check"
  {
    nativeBuildInputs = with pkgs; [
      bun
      typescript
      python3
      shellcheck
      strace
      xorg.xorgserver
      xorg.xauth
    ];
  }
  ''
    mkdir -p work/plugins/cemu work/contracts/generated
    cp ${package}/plugin.ts work/plugins/cemu/plugin.ts
    cp ${../plugins/cemu/plugin.test.ts} work/plugins/cemu/plugin.test.ts
    cp ${contractSource} work/contracts/generated/korrid.ts
    cd work
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler plugins/cemu/plugin.ts
    bun plugins/cemu/plugin.test.ts
    shellcheck ${cemuPackage}/bin/cemu
    ${pkgs.xvfb-run}/bin/xvfb-run -a python3 ${../plugins/cemu/runtime-check.py} ${cemuPackage} "$out/runtime"
    mkdir -p "$out"
    cp -R ${cemuPackage}/nix-support/cemu-build "$out/"
  ''

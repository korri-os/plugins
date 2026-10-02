{
  pkgs,
  package,
  core,
  contract,
}:
let
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
in
pkgs.runCommand "korri-fake08-package-check"
  {
    nativeBuildInputs = [
      pkgs.python3
      pkgs.bun
      pkgs.typescript
    ];
  }
  ''
    python3 ${./core-check.py} ${core}/lib/retroarch/cores/fake08_libretro.so
    # Typecheck the actual generated plugin, shared helper and pinned settings.
    mkdir -p work/plugins/libretro work/contracts/generated
    cp ${package}/*.ts work/plugins/libretro/
    cmp ${package.source}/retroarch.ts ${package}/retroarch.ts
    cp ${contractSource} work/contracts/generated/korrid.ts
    tsc --strict --noEmit --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler work/plugins/libretro/*.ts
    bun ${./plugin-check.ts} ${package}
    cmp ${core.src}/LICENSE.MD ${core}/share/doc/libretro-fake08/LICENSE.MD
    test -s ${core}/share/doc/libretro-fake08/original-notices/libs/z8lua/eris.c
    test -s ${core}/share/doc/libretro-fake08/original-notices/libs/simpleini/ConvertUTF.h
    # Deliberately small installed shape. Do not ship upstream sample/platform art.
    test "$(find ${core}/lib -type f | wc -l)" -eq 2
    test ! -d ${core}/bin
    touch "$out"
  ''

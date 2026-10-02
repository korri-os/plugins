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
    notices=${core}/share/doc/libretro-fake08/original-notices
    # Standalone licenses omit notices in the actual linked sources. Preserve
    # every byte, including miniz's Raiber MIT and public-domain sections and
    # LodePNG's newer copyright, in both native outputs.
    for file in libs/miniz/miniz.c libs/lodepng/lodepng.cpp libs/lodepng/lodepng.h; do
      cmp ${core.src}/"$file" "$notices/$file"
    done
    grep -Fq 'Copyright 2016 Martin Raiber' "$notices/libs/miniz/miniz.c"
    grep -Fq 'The above copyright notice and this permission notice shall be included in' \
      "$notices/libs/miniz/miniz.c"
    grep -Fq 'This is free and unencumbered software released into the public domain.' \
      "$notices/libs/miniz/miniz.c"
    grep -Fq '<http://unlicense.org/>' "$notices/libs/miniz/miniz.c"
    for file in lodepng.cpp lodepng.h; do
      grep -Fq 'Copyright (c) 2005-2020 Lode Vandevenne' "$notices/libs/lodepng/$file"
      grep -Fq 'This notice may not be removed or altered from any source' \
        "$notices/libs/lodepng/$file"
    done
    # Deliberately small installed shape. Do not ship upstream sample/platform art.
    test "$(find ${core}/lib -type f | wc -l)" -eq 2
    test ! -d ${core}/bin
    touch "$out"
  ''

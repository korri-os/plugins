{
  pkgs,
  package,
  engine,
  contract,
  hostPackage,
  korridPackage,
}:
let
  fixtures = import ./zquest-fixtures.nix { inherit pkgs engine; };
  publicFixture = import ./zquest-public-fixture.nix { inherit pkgs; };
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
  recordArguments = pkgs.writeShellScript "record-zquest-arguments" ''
    printf '%s\0' "$@"
  '';
  tsconfig = pkgs.writeText "zquest-plugin-tsconfig.json" (
    builtins.toJSON {
      compilerOptions = {
        target = "ES2022";
        module = "ESNext";
        moduleResolution = "Bundler";
        strict = true;
        noEmit = true;
        skipLibCheck = true;
      };
      include = [ "plugins/zquest-classic/plugin.ts" ];
    }
  );
in
pkgs.runCommand "korri-zquest-classic-plugin-check"
  {
    nativeBuildInputs = [
      pkgs.bun
      pkgs.typescript
      (pkgs.python3.withPackages (python: [ python.pillow ]))
      pkgs.xvfb-run
      pkgs.xdotool
      pkgs.pulseaudio
      pkgs.imagemagick
    ];
    LIBGL_ALWAYS_SOFTWARE = "1";
    GALLIUM_DRIVER = "llvmpipe";
    LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.libGL
      pkgs.libGLU
      pkgs.mesa
    ];
    LIBGL_DRIVERS_PATH = "${pkgs.mesa}/lib/dri";
    __GLX_VENDOR_LIBRARY_NAME = "mesa";
  }
  ''
    export HOME="$TMPDIR/home"
    export XDG_CACHE_HOME="$HOME/.cache"
    mkdir -p "$XDG_CACHE_HOME" work/plugins/zquest-classic work/contracts/generated work/nix
    cp ${package}/plugin.ts work/plugins/zquest-classic/plugin.ts
    cp ${contractSource} work/contracts/generated/korrid.ts
    cp ${./zquest-check.ts} work/nix/zquest-check.ts
    cp ${tsconfig} work/tsconfig.json
    cd work
    tsc --project tsconfig.json
    bun nix/zquest-check.ts ${package} ${hostPackage}/bin/korri-plugin \
      ${korridPackage}/bin/korrid ${recordArguments}
    python3 ${./zquest-publication-check.py} \
      ${package} ${engine} ${engine.assets} ${engine.publicSource}
    mkdir asset-reader
    cp ${../plugins/zquest-classic/public-assets-validate.py} asset-reader/public-assets-validate.py
    cp ${../plugins/zquest-classic/public-assets-metrics.json} asset-reader/public-assets-metrics.json
    cp ${../plugins/zquest-classic/public-assets-font-test.py} asset-reader/public-assets-font-test.py
    cp ${../plugins/zquest-classic/public-assets.py} asset-reader/public-assets.py
    cp ${../plugins/zquest-classic/tiny5.glyphs.txt} asset-reader/tiny5.glyphs.txt
    cp ${../plugins/zquest-classic/tiny5-OFL.txt} asset-reader/tiny5-OFL.txt
    cp ${../plugins/zquest-classic/ASSET-LICENSES.md} asset-reader/ASSET-LICENSES.md
    xvfb-run -a python3 asset-reader/public-assets-font-test.py \
      --source ${engine.publicSource} \
      --font ${engine.publicSource}/resources/ProggyVector-Regular.ttf \
      --allegro-library ${engine}/lib/liballeg.so
    xvfb-run -a python3 asset-reader/public-assets-validate.py \
      --resources ${engine.assets} --allegro-library ${engine}/lib/liballeg.so --midi-playback
    xvfb-run -a -s '-screen 0 800x600x24' python3 ${./zquest-runtime-check.py} \
      ${package} ${engine} ${korridPackage}/bin/korrid ${pkgs.stdenv.hostPlatform.system} ${fixtures} ${publicFixture}/public-room.qst
    touch "$out"
  ''

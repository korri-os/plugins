{
  pkgs,
  engine,
  cartridges,
}:
# Load the packaged Lantern Hollow in the packaged public engine, headless, and
# replay a short scripted input. Confirms the quest loads, plays without a
# replay error, and draws its own scenery rather than the missing-tiles error.
pkgs.runCommand "korri-starter-pack-lantern-hollow-check"
  {
    nativeBuildInputs = [
      (pkgs.python3.withPackages (python: [ python.pillow ]))
      pkgs.xvfb-run
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
    mkdir -p "$HOME"
    python3 ${./lantern-hollow-check.py} \
      ${engine} ${cartridges}/share/starter-pack/cartridges/lantern-hollow.qst "$TMPDIR/run"
    touch "$out"
  ''

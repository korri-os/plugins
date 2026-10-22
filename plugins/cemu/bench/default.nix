{ pkgs }:
let
  python = pkgs.python3;
in
pkgs.stdenv.mkDerivation {
  pname = "korri-cemu-bench";
  version = "0.1.0";
  src = pkgs.lib.fileset.toSource {
    root = ./.;
    fileset = pkgs.lib.fileset.unions [
      ./bench.py
      ./gamepad.py
      ./metrics.py
      ./present-watch.c
      ./test_metrics.py
    ];
  };
  nativeBuildInputs = [
    pkgs.pkg-config
    pkgs.makeWrapper
  ];
  buildInputs = [ pkgs.libxcb ];
  buildPhase = ''
    runHook preBuild
    $CC -std=c11 -D_POSIX_C_SOURCE=200809L -O2 -Wall -Wextra -Werror \
      present-watch.c $(pkg-config --cflags --libs xcb xcb-present) -o present-watch
    runHook postBuild
  '';
  doCheck = true;
  nativeCheckInputs = [ python ];
  checkPhase = ''
    ${python}/bin/python3 -m unittest -v test_metrics
  '';
  installPhase = ''
    mkdir -p "$out/bin" "$out/lib/cemu-bench"
    cp *.py "$out/lib/cemu-bench/"
    cp present-watch "$out/bin/"
    makeWrapper ${python}/bin/python3 "$out/bin/korri-cemu-bench" \
      --add-flags "$out/lib/cemu-bench/bench.py" \
      --set KORRI_BENCH_PRESENT_WATCH "$out/bin/present-watch" \
      --prefix PATH : ${
        pkgs.lib.makeBinPath [
          pkgs.systemd
          pkgs.util-linux
          pkgs.vulkan-tools
        ]
      }
  '';
  meta = {
    description = "Exact-session Korri FPS bench with Linux uinput and X Present telemetry";
    platforms = pkgs.lib.platforms.linux;
    mainProgram = "korri-cemu-bench";
  };
}

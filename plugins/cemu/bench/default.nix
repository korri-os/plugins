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
      ./present-fixture.c
      ./test_metrics.py
      ./test_rpc.py
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
      present-watch.c $(pkg-config --cflags --libs xcb xcb-present xcb-res) -o present-watch
    runHook postBuild
  '';
  doCheck = true;
  nativeCheckInputs = [
    python
    pkgs.xorg.xorgserver
  ];
  checkPhase = ''
    ${python}/bin/python3 -m unittest -v
    $CC -std=c11 -D_POSIX_C_SOURCE=200809L -O2 -Wall -Wextra -Werror \
      present-fixture.c $(pkg-config --cflags --libs xcb xcb-present) -o present-fixture
    export DISPLAY=:89
    Xvfb "$DISPLAY" -screen 0 640x480x24 -ac >xvfb.log 2>&1 &
    xvfb=$!
    fixture= observer=
    trap 'kill $observer $fixture $xvfb 2>/dev/null || true' EXIT
    sleep 1
    ./present-fixture &
    fixture=$!
    ./present-watch "$fixture" >present.csv 2>observer.log &
    observer=$!
    sleep 3
    kill "$observer"
    wait "$observer"
    ${python}/bin/python3 -c 'import csv; r=list(csv.DictReader(open("present.csv"))); assert len(r)>30, r; assert all(int(x["ust_us"])>0 for x in r); assert len({x["window"] for x in r})==1'
    kill "$fixture" "$xvfb"
    wait "$fixture"
    wait "$xvfb" || true
    trap - EXIT
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

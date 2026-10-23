{ pkgs }:
let
  python = pkgs.python3.withPackages (ps: [ ps.pillow ]);
in
pkgs.stdenv.mkDerivation {
  pname = "korri-cemu-bench";
  version = "0.1.0";
  src = pkgs.lib.fileset.toSource {
    root = ./.;
    fileset = pkgs.lib.fileset.unions [
      ./bench.py
      ./controller_profile.py
      ./gamepad.py
      ./input_observer.py
      ./input_replay.py
      ./test_input_replay.py
      ./metrics.py
      ./gameplay_gate.py
      ./frame_reference.py
      ./reporting.py
      ./save_safety.py
      ./save_proof.py
      ./references
      ./test_gameplay_gate.py
      ./test_save_safety.py
      ./test_save_proof.py
      ./present-watch.c
      ./present-fixture.c
      ./test_metrics.py
      ./test_controller_profile.py
      ./test_input_observer.py
      ./test_rpc.py
      ./wl4-title.events
      ./botw-load.events
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
    ${python}/bin/python3 - <<'PYWAIT'
    import csv, time
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        with open("present.csv") as source:
            if len(list(csv.DictReader(source))) > 30:
                break
        time.sleep(0.1)
    else:
        raise RuntimeError("Present fixture did not produce enough events within 30 seconds")
    PYWAIT
    kill "$observer"
    wait "$observer"
    ${python}/bin/python3 -c 'import csv; r=list(csv.DictReader(open("present.csv"))); assert len(r)>30, r; assert all(int(x["ust_us"])>0 for x in r); assert len({x["window"] for x in r})==1'
    kill "$fixture" "$xvfb"
    wait "$fixture"
    wait "$xvfb" || true
    trap - EXIT
  '';
  installPhase = ''
    mkdir -p "$out/bin" "$out/lib/cemu-bench" "$out/share/cemu-bench"
    cp *.py "$out/lib/cemu-bench/"
    cp present-watch "$out/bin/"
    cp -r references "$out/share/cemu-bench/"
    makeWrapper ${python}/bin/python3 "$out/bin/korri-cemu-bench-reference" \
      --add-flags "$out/lib/cemu-bench/frame_reference.py" \
      --prefix PATH : ${
        pkgs.lib.makeBinPath [
          pkgs.grim
          pkgs.util-linux
        ]
      }
    install -Dm444 botw-load.events "$out/share/cemu-bench/botw-load.events"
    install -Dm444 wl4-title.events "$out/share/cemu-bench/wl4-title.events"
    makeWrapper ${python}/bin/python3 "$out/bin/korri-cemu-bench" \
      --add-flags "$out/lib/cemu-bench/bench.py" \
      --set KORRI_BENCH_PRESENT_WATCH "$out/bin/present-watch" \
      --prefix PATH : ${
        pkgs.lib.makeBinPath [
          pkgs.grim
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

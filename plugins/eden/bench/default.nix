{ pkgs }:
let
  python = pkgs.python3.withPackages (ps: [ ps.evdev ]);
in
pkgs.stdenv.mkDerivation {
  pname = "korri-eden-bench";
  version = "0.2.2";
  src = pkgs.lib.fileset.toSource {
    root = ./.;
    fileset = pkgs.lib.fileset.fileFilter (file: file.hasExt "py" || file.hasExt "c") ./.;
  };
  nativeBuildInputs = [
    pkgs.makeWrapper
    pkgs.pkg-config
  ];
  buildInputs = [
    pkgs.xorg.libX11
    pkgs.xorg.libXpresent
    pkgs.xorg.libXres
    pkgs.xorg.libXrandr
    pkgs.xorg.libXfixes
    pkgs.xorg.libXext
  ];
  nativeCheckInputs = [
    python
    pkgs.ruff
    pkgs.mypy
    pkgs.xorg.xorgserver
  ];
  buildPhase = ''
    $CC -std=c11 -D_POSIX_C_SOURCE=200809L -O2 -Wall -Wextra -Werror \
      present-observer.c $(pkg-config --cflags --libs x11 xpresent xres) -o present-observer
  '';
  doCheck = true;
  checkPhase = ''
    export HOME="$TMPDIR"
    ${python}/bin/python3 -m unittest discover -v
    ruff check .
    ruff format --check .
    mypy --python-executable ${python}/bin/python3 --follow-untyped-imports --check-untyped-defs *.py
    $CC -std=c11 -D_POSIX_C_SOURCE=200809L -O2 -Wall -Wextra -Werror \
      present-producer.c $(pkg-config --cflags --libs x11 xpresent) -o present-producer
    export DISPLAY=:93
    Xvfb "$DISPLAY" -screen 0 640x480x24 -ac >xvfb.log 2>&1 &
    server=$!
    first= second= watcher=
    trap 'kill $watcher $first $second $server 2>/dev/null || true' EXIT
    sleep 1
    ./present-producer >first.window &
    first=$!
    ./present-producer >second.window &
    second=$!
    ./present-observer "$first" >present.csv 2>observer.log &
    watcher=$!
    sleep 2
    kill "$second" "$first"
    wait "$second"
    wait "$first"
    sleep 0.2
    kill "$watcher"
    wait "$watcher"
    ${python}/bin/python3 -c 'from metrics import read_presentations; from pathlib import Path; e=read_presentations(Path("present.csv")); w=int(Path("first.window").read_text()); frames=[x for x in e if x.event=="frame"]; assert len(frames)>20, (len(frames),Path("observer.log").read_text()); assert all(x.window==w for x in frames); assert any(x.event=="destroy" and x.window==w for x in e)'
    kill "$server"
    wait "$server" || true
    trap - EXIT
  '';
  installPhase = ''
    mkdir -p "$out/lib/eden-bench" "$out/bin"
    cp *.py "$out/lib/eden-bench/"
    cp present-observer "$out/bin/"
    makeWrapper ${python}/bin/python3 "$out/bin/korri-eden-bench" \
      --add-flags "$out/lib/eden-bench/bench.py" \
      --set KORRI_EDEN_PRESENT_OBSERVER "$out/bin/present-observer" \
      --prefix PATH : ${
        pkgs.lib.makeBinPath [
          pkgs.util-linux
          pkgs.systemd
        ]
      }
  '';
  meta = {
    description = "Exact-session FPS collector using game-window X11 Present completions";
    mainProgram = "korri-eden-bench";
    platforms = pkgs.lib.platforms.linux;
  };
}

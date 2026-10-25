{
  runCommand,
  stdenv,
  python3,
  patch,
  retroarchSource,
  overlayPatch,
}:
runCommand "retroarch-core-options-overlay-check"
  {
    nativeBuildInputs = [
      stdenv.cc
      python3
      patch
    ];
  }
  ''
    ulimit -c 0
    cp ${retroarchSource}/core_option_manager.{c,h} .
    chmod u+w core_option_manager.{c,h}
    python3 ${./retroarch-core-options-overlay-extract.py} \
      ${retroarchSource}/runloop.c core-options-selection.h
    bash ${./retroarch-core-options-overlay-build.sh} \
      ${retroarchSource} ${./retroarch-core-options-overlay-check.c} baseline
    mkdir baseline-run patched-native-run patched-overlay-run
    (cd baseline-run && ../baseline native > ../baseline.txt)
    # The regression must catch the unpatched program ignoring the overlay.
    if (cd baseline-run && ../baseline overlay > /dev/null 2>&1); then
      echo "unpatched RetroArch unexpectedly satisfied the overlay contract" >&2
      exit 1
    fi
    patch --fuzz=0 -p1 < ${overlayPatch}
    bash ${./retroarch-core-options-overlay-build.sh} \
      ${retroarchSource} ${./retroarch-core-options-overlay-check.c} patched
    (cd patched-native-run && ../patched native > ../patched-native.txt)
    cmp baseline.txt patched-native.txt
    (cd patched-overlay-run && ../patched overlay > ../patched-overlay.txt)
    echo "168 native-source cases per run; legacy and v2; menu and exit writes passed"
    echo "No-overlay output and serialized files match unpatched RetroArch byte-for-byte"
    touch "$out"
  ''

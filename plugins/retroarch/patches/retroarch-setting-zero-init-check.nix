{
  runCommand,
  stdenv,
  python3,
  patch,
  retroarchSource,
  zeroInitPatch,
}:
runCommand "retroarch-setting-zero-init-check"
  {
    nativeBuildInputs = [
      stdenv.cc
      python3
      patch
    ];
    # The compile command below chooses how unassigned locals are filled.
    hardeningDisable = [ "trivialautovarinit" ];
  }
  ''
    mkdir menu
    cp ${retroarchSource}/menu/menu_setting.c menu/
    chmod u+w menu/menu_setting.c
    build() {
      python3 ${./retroarch-setting-zero-init-extract.py} \
        menu/menu_setting.c setting-constructors-extracted.h
      # The pattern fill gives an unassigned field a nonzero value, so the
      # upstream defect fails on every run, whatever the stack held before.
      # The unpatched build must compile to reach the runtime comparison, so
      # the uninitialized warnings are off. Upstream setting_bool_setting has
      # unused parameters.
      $CC -std=c99 -Wall -Wextra -Werror -Wno-unused-parameter \
        -Wno-uninitialized -Wno-maybe-uninitialized \
        -ftrivial-auto-var-init=pattern \
        -I. -I${retroarchSource} -I${retroarchSource}/libretro-common/include \
        ${./retroarch-setting-zero-init-check.c} -o "$1"
    }
    build baseline
    # The regression must catch the unpatched constructors.
    if ./baseline > /dev/null 2> baseline.txt; then
      echo "unpatched RetroArch unexpectedly returned initialized settings" >&2
      exit 1
    fi
    grep -qF "setting_action_setting left ui_type=" baseline.txt
    echo "Unpatched RetroArch failed as expected: $(cat baseline.txt)"
    patch --fuzz=0 -p1 < ${zeroInitPatch}
    build patched
    ./patched
    touch "$out"
  ''

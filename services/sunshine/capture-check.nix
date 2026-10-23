{ pkgs }:
let
  approved = import ./approved-patches.nix;
  source = pkgs.applyPatches {
    name = "sunshine-capture-check-source";
    src = pkgs.sunshine.src;
    patchFlags = [
      "-p1"
      "--fuzz=0"
      "--no-backup-if-mismatch"
    ];
    patches = map (record: record.path) (approved.patches ++ approved.rkmppPatches);
  };
in
pkgs.stdenv.mkDerivation {
  name = "sunshine-korri-capture-check";
  dontUnpack = true;
  buildInputs = [
    pkgs.libyuv
    pkgs.libdrm
  ];
  buildPhase = ''
    $CXX -std=c++17 -O2 -Wall -Wextra -Werror -I${source}/src \
      ${./row-pair-test.cpp} -o row-pair-test -lyuv
    $CXX -std=c++17 -O2 -Wall -Wextra -Werror -I${source}/src \
      ${./capture-scheduling-test.cpp} -o capture-scheduling-test
    $CXX -std=c++17 -O2 -Wall -Wextra -Werror -I${source}/src \
      ${./kms-pacing-test.cpp} -o kms-pacing-test
    $CXX -std=c++17 -O2 -Wall -Wextra -Werror -I${source}/src \
      ${./kms-rt-guard-test.cpp} -o kms-rt-guard-test
    $CXX -std=c++17 -O2 -Wall -Wextra -Werror -I${source}/src -I${pkgs.libdrm.dev}/include/libdrm \
      ${./kms-vblank-wait-test.cpp} -o kms-vblank-wait-test
  '';
  doCheck = true;
  checkPhase = ''
    ./row-pair-test
    ./capture-scheduling-test
    ./kms-pacing-test
    ./kms-rt-guard-test
    ./kms-vblank-wait-test
    # The generic async thread may not promote an unguarded backend.
    if grep -F 'request_capture_scheduling' ${source}/src/video.cpp; then
      echo 'generic capture loop must not request FIFO' >&2
      exit 1
    fi
    grep -F 'DRM_VBLANK_EVENT' ${source}/src/platform/linux/kmsgrab.cpp
    grep -F 'wait_vblank_event(event_fd, cookie, event_deadline)' ${source}/src/platform/linux/kmsgrab.cpp
    # Native permission and Sunshine policy must remain aligned and narrow.
    grep -Fx 'LimitRTPRIO=5' ${../../plugins/sunshine/korri-sunshine.service}
    grep -F 'capture_rt_priority=5' ${../../plugins/sunshine/runtime.sh}
    if grep -Eq '^(CPUScheduling|Nice=|IOScheduling)|CAP_SYS_NICE' ${../../plugins/sunshine/korri-sunshine.service}; then
      echo 'Sunshine must not acquire service-wide scheduling authority' >&2
      exit 1
    fi
  '';
  installPhase = "touch $out";
}

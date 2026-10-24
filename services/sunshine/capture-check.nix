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
  nativeBuildInputs = [ pkgs.python3 ];
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
    python3 ${./test-rkmpp-pacing.py} ${source}/src/video.cpp
    # RAM and VRAM factories have similar patch context. RKMPP descriptors
    # must stay in VRAM capture, never in the RGB image factory.
    if sed -n '/class wlr_ram_t:/,/class wlr_vram_t:/p' ${source}/src/platform/linux/wlgrab.cpp \
      | grep -F 'make_unique<rkmpp_wl_t>'; then
      echo 'RKMPP Wayland device attached to RAM capture' >&2
      exit 1
    fi
    sed -n '/class wlr_vram_t:/,$p' ${source}/src/platform/linux/wlgrab.cpp \
      | grep -F 'make_unique<rkmpp_wl_t>'
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
    # Opening the separate pacing fd must use the same privileged worker and
    # DRM-master release policy as capture. Do not add a second capability site.
    grep -F 'event_fd = privileged_drm_worker::open_drm_card_fd_privileged(device);' ${source}/src/platform/linux/kmsgrab.cpp
    test "$(grep -c CAP_SYS_ADMIN ${source}/src/platform/linux/kmsgrab.cpp)" \
      = "$(grep -c CAP_SYS_ADMIN ${pkgs.sunshine.src}/src/platform/linux/kmsgrab.cpp)"
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

# Harvest: legacy:product/plugins/moonlight/packages/moonlight-embedded-korri/package.nix
{
  lib,
  stdenv,
  fetchFromGitHub,
  cmake,
  perl,
  pkg-config,
  alsa-lib,
  avahi,
  curl,
  expat,
  ffmpeg,
  libcec,
  libevdev,
  libpulseaudio,
  libpthreadstubs,
  libva,
  libvdpau,
  libxcb,
  libopus,
  json_c,
  SDL2,
  systemdMinimal,
  util-linux,
  libdrm,
  libglvnd,
  libX11,
}:

let
  # Opus custom modes make every opus_decoder_get_size() call build a CELT
  # mode, which runs opus_select_arch() and so reads /proc/cpuinfo on ARM.
  # opus_multistream_decode() calls it for each stream of each packet: on the
  # RG353M that was about 60% of Moonlight's audio thread. Moonlight decodes
  # standard Opus multistream only, so build without custom modes, the
  # upstream default that nixpkgs overrides.
  opusStandardModes = libopus.override { withCustomModes = false; };

  # Stateless V4L2 decoders (Hantro, Cedrus, rkvdec) need FFmpeg's V4L2
  # Request API hwaccel, which upstream FFmpeg does not carry. The patch is
  # Jonas Karlman's series as LibreELEC ships it for FFmpeg 9.0.2:
  # LibreELEC.tv e9e6b8531df13bc9058ca1771dab5f0c4fd5e98e,
  # packages/multimedia/ffmpeg/patches/v4l2-request/0001-v4l2-request.patch.
  # Stateful h264_v4l2m2m (Qualcomm) is unchanged by it.
  ffmpegV4l2Request = (ffmpeg.override { libopus = opusStandardModes; }).overrideAttrs (old: {
    patches = (old.patches or [ ]) ++ [ ./patches/ffmpeg/0001-v4l2-request.patch ];
    configureFlags = (old.configureFlags or [ ]) ++ [
      "--enable-libudev"
      "--enable-v4l2-request"
    ];
    buildInputs = (old.buildInputs or [ ]) ++ [ systemdMinimal ];
  });
in
stdenv.mkDerivation rec {
  pname = "moonlight-embedded-korri";
  version = "2.7.1-korri";

  # Base patches vendored from nix-on-rocks/packages/moonlight-embedded/.
  # 0001 is praxis88 PR #932; 0001a and 0002 are nix-on-rocks downstream.
  src = fetchFromGitHub {
    owner = "moonlight-stream";
    repo = "moonlight-embedded";
    rev = "775444287305849ebdf4736c75298ad0713e2d5d";
    hash = "sha256-h+hI9TQUGMI8VDzvnuRGDjxm8D7GuC/L4/0rwTFocgA=";
    fetchSubmodules = true;
  };
  patches = [
    ./patches/0001-vendored-ffmpeg-drm-prime-pr932.patch
    ./patches/0001a-fix-libdrm-cmake-find-and-main-help.patch
    ./patches/0002-add-v4l2m2m-sdl-nv12-platform.patch
    ./patches/0013-add-auto-window-resize-flag.patch
    ./patches/0014-disable-gamepad-quit-combo.patch
    ./patches/0015-crop-coded-alignment-padding-on-present.patch
    # New Korri security patch, not a legacy harvest: pin the broker's certificate.
    ./patches/0020-pin-broker-authorized-server-certificate.patch
    # Korri: stateless decoders through FFmpeg's V4L2 Request hwaccel.
    ./patches/0021-add-v4l2request-stateless-platform.patch
    ./patches/0022-v4l2request-zero-copy-gl-background-window.patch
  ];

  nativeBuildInputs = [
    cmake
    perl
    pkg-config
  ];

  buildInputs = [
    alsa-lib
    avahi
    curl
    expat
    ffmpegV4l2Request
    libcec
    libevdev
    libpulseaudio
    libpthreadstubs
    libva
    libvdpau
    libxcb
    opusStandardModes
    json_c
    SDL2
    systemdMinimal
    util-linux
    libdrm
    libglvnd
    libX11
  ];

  strictDeps = true;

  cmakeFlags = [
    "-DCMAKE_BUILD_TYPE=Release"
    "-DBCM_LIBRARY=OFF"
    "-DENABLE_PI=OFF"
    "-DENABLE_MMAL=OFF"
    "-DENABLE_IMX=OFF"
    "-DENABLE_AML=OFF"
    "-DENABLE_FFMPEG=ON"
    "-DENABLE_SDL=ON"
    "-DENABLE_FFMPEG_DRM=ON"
    "-DENABLE_V4L2M2M=ON"
  ];

  postInstall = ''
    mkdir -p "$out/nix-support/moonlight-embedded-korri"

    if [ -f "$out/bin/moonlight" ]; then
      printf 'present\n' > "$out/nix-support/moonlight-embedded-korri/moonlight-binary-present"
    else
      echo "error: moonlight binary missing from $out/bin" >&2
      exit 1
    fi

    korriInputplumberMapping="$out/share/moonlight/korri-inputplumber-gamecontrollerdb.txt"
    cp "$out/share/moonlight/gamecontrollerdb.txt" "$korriInputplumberMapping"
    substituteInPlace "$korriInputplumberMapping" \
      --replace-fail '030000005e0400008e02000001000000,Microsoft Xbox 360,a:b0,b:b1,back:b6,dpdown:h0.1,dpleft:h0.2,dpright:h0.8,dpup:h0.4,leftshoulder:b4,leftstick:b9,lefttrigger:a2,leftx:a0,lefty:a1,rightshoulder:b5,rightstick:b10,righttrigger:a5,rightx:a3,righty:a4,start:b7,x:b2,y:b3,platform:Linux,' \
      '030000005e0400008e02000001000000,Microsoft Xbox 360,a:b0,b:b1,back:b6,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,leftshoulder:b4,leftstick:b9,lefttrigger:a2,leftx:a0,lefty:a1,rightshoulder:b5,rightstick:b10,righttrigger:a5,rightx:a3,righty:a4,start:b7,x:b2,y:b3,platform:Linux,'
    printf '%s\n' \
      '030000005e040000120b000001000000,Microsoft Xbox Series S|X Controller,a:b0,b:b1,x:b2,y:b3,back:b6,start:b7,guide:b8,leftstick:b9,rightstick:b10,leftshoulder:b4,rightshoulder:b5,dpup:h0.1,dpright:h0.2,dpdown:h0.4,dpleft:h0.8,leftx:a0,lefty:a1,rightx:a3,righty:a4,lefttrigger:a2,righttrigger:a5,platform:Linux,' \
      >> "$korriInputplumberMapping"
    printf 'present\n' > "$out/nix-support/moonlight-embedded-korri/korri-inputplumber-gamecontrollerdb-present"

    if [ -f CMakeCache.txt ]; then
      cp CMakeCache.txt "$out/nix-support/moonlight-embedded-korri/CMakeCache.txt"
    fi
  '';

  meta = {
    description = "Moonlight Embedded with DRM PRIME, V4L2 M2M, V4L2 Request and Korri viewer patches";
    homepage = "https://github.com/moonlight-stream/moonlight-embedded";
    license = lib.licenses.gpl3Plus;
    mainProgram = "moonlight";
    platforms = [
      "aarch64-linux"
      "x86_64-linux"
    ];
  };
}

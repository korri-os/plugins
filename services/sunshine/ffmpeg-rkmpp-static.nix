{
  stdenv,
  lib,
  fetchFromGitHub,
  cmake,
  pkg-config,
  nasm,
  perl,
  libdrm,
  rockchipMpp,
  nv-codec-headers-13,
}:

let
  approved = import ./approved-patches.nix;
  v4l2m2mPatchesApproved = builtins.all (
    record: builtins.hashFile "sha256" record.path == record.sha256
  ) approved.v4l2m2mPatches;
  # Sunshine links against a static FFmpeg whose ABI is reviewed in
  # approved-patches.nix. Build the RKMPP encoder against that exact commit
  # so the nvenc/vaapi/x86 paths keep the same libavcodec contract.
  ffmpegSrc = fetchFromGitHub {
    owner = "FFmpeg";
    repo = "FFmpeg";
    rev = approved.reviewedFfmpegCommit;
    hash = approved.reviewedFfmpegSourceHash;
  };
in
assert v4l2m2mPatchesApproved;
stdenv.mkDerivation {
  pname = "sunshine-ffmpeg-rkmpp";
  version = "${approved.reviewedLibavcodecVersion}-${
    builtins.substring 0 12 approved.reviewedFfmpegCommit
  }";

  src = fetchFromGitHub {
    owner = "LizardByte";
    repo = "build-deps";
    rev = approved.reviewedBuildDepsCommit;
    hash = approved.reviewedBuildDepsSourceHash;
  };

  nativeBuildInputs = [
    cmake
    pkg-config
    nasm
    perl
  ];

  buildInputs = [
    libdrm
    rockchipMpp
  ];

  postPatch = ''
    # build-deps expects FFmpeg as a git submodule. Replace the empty submodule
    # directory with the reviewed source tree.
    mkdir -p third-party/FFmpeg
    rm -rf third-party/FFmpeg/FFmpeg
    cp -R ${ffmpegSrc} third-party/FFmpeg/FFmpeg
    chmod -R u+w third-party/FFmpeg/FFmpeg
    patch -d third-party/FFmpeg/FFmpeg -p1 \
      < ${./patches/ffmpeg/0001-add-rkmpp-h264-encoder.patch}
    patch -d third-party/FFmpeg/FFmpeg -p1 \
      < ${./patches/ffmpeg/0002-adapt-rkmpp-to-reviewed-ffmpeg.patch}
    ${lib.concatMapStringsSep "\n" (record: ''
      patch -d third-party/FFmpeg/FFmpeg -p1 < ${record.path}
    '') approved.v4l2m2mPatches}
    # APPLY_GIT_PATCH uses `git apply`, which silently no-ops outside a git
    # checkout. Apply Sunshine's CBS patches with plain patch instead.
    for cbsPatch in patches/FFmpeg/FFmpeg/cbs/*.patch; do
      patch -d third-party/FFmpeg/FFmpeg -p1 < "$cbsPatch"
    done

    substituteInPlace cmake/ffmpeg/ffmpeg.cmake \
      --replace-fail '        --enable-gpl' \
                     '        --enable-gpl;--enable-version3;--enable-libdrm;--enable-rkmpp;--enable-encoder=h264_rkmpp' \
      --replace-fail '--enable-encoder=h264_v4l2m2m' \
                     '--enable-encoder=h264_v4l2m2m,hevc_v4l2m2m'
  '';

  cmakeFlags = [
    "-DFFMPEG_INSTALL_PREFIX=${placeholder "out"}"
    (lib.cmakeBool "BUILD_ALL" false)
    (lib.cmakeBool "BUILD_FFMPEG" true)
    (lib.cmakeBool "BUILD_FFMPEG_ALL_PATCHES" false)
    (lib.cmakeBool "BUILD_FFMPEG_CBS_PATCHES" true)
    (lib.cmakeBool "BUILD_FFMPEG_AMF" false)
    (lib.cmakeBool "BUILD_FFMPEG_MF" false)
    (lib.cmakeBool "BUILD_FFMPEG_NV_CODEC_HEADERS" false)
    (lib.cmakeBool "BUILD_FFMPEG_SVT_AV1" false)
    (lib.cmakeBool "BUILD_FFMPEG_LIBVA" false)
    (lib.cmakeBool "BUILD_FFMPEG_VULKAN" false)
    (lib.cmakeBool "BUILD_FFMPEG_X264" false)
    (lib.cmakeBool "BUILD_FFMPEG_X265" false)
  ];

  enableParallelBuilding = true;

  postInstall = ''
    # Sunshine v2026.914 configures against ffnvcodec headers in the prepared
    # binaries even without CUDA; without them its CMake fetches
    # nv_codec_headers_13_1 (n13.1.15.0) from Git, which the sandbox refuses.
    cp -r ${nv-codec-headers-13}/include/ffnvcodec "$out/include/"
    grep -F 'NVENCAPI_MAJOR_VERSION 13' "$out/include/ffnvcodec/nvEncodeAPI.h" >/dev/null
    test -f "$out/lib/libavcodec.a"
    test -f "$out/lib/libavutil.a"
    test -f "$out/lib/libswscale.a"
    test -f "$out/lib/libcbs.a"
    grep -F AV_HWDEVICE_TYPE_RKMPP "$out/include/libavutil/hwcontext.h"
    # One static archive must contain both encoder families. Separate FFmpeg
    # closures cannot supply both to the same Sunshine executable.
    nm -g "$out/lib/libavcodec.a" | grep -F 'ff_h264_rkmpp_encoder' >/dev/null
    nm -g "$out/lib/libavcodec.a" | grep -F 'ff_h264_v4l2m2m_encoder' >/dev/null
  '';

  passthru = {
    buildDepsRev = approved.reviewedBuildDepsCommit;
    ffmpegCommit = approved.reviewedFfmpegCommit;
    libavcodecVersion = approved.reviewedLibavcodecVersion;
    patchSetSha256 = approved.v4l2m2mPatchSetSha256;
  };

  meta = {
    description = "Sunshine-compatible static FFmpeg with RKMPP and V4L2 M2M encoding";
    homepage = "https://github.com/LizardByte/build-deps";
    license = lib.licenses.gpl3Plus;
    platforms = [ "aarch64-linux" ];
  };
}

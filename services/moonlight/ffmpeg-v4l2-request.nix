# FFmpeg for Moonlight only, with the V4L2 Request API hwaccel. Stateless
# decoders such as Allwinner Cedrus (H700) need it; upstream FFmpeg 9.0.2
# carries only the stateful v4l2_m2m wrappers.
#
# ffmpeg-patches/0001-v4l2-request.patch is LibreELEC.tv master's
# packages/multimedia/ffmpeg/patches/v4l2-request/0001-v4l2-request.patch
# (blob e549fb5e8d544d852765f1bcebb173b9b5e462a8, last changed in LibreELEC
# commit e9e6b8531df13bc9058ca1771dab5f0c4fd5e98e). LibreELEC generates it with
# tools/ffmpeg/gen-patches.sh from Kwiboo's branch v4l2-request-n9.0.2 at
# https://code.ffmpeg.org/Kwiboo/FFmpeg.git, against FFmpeg n9.0.2.
{ ffmpeg, systemdLibs }:

ffmpeg.overrideAttrs (old: {
  pname = "${old.pname}-v4l2-request";
  patches = (old.patches or [ ]) ++ [ ./ffmpeg-patches/0001-v4l2-request.patch ];
  buildInputs = (old.buildInputs or [ ]) ++ [ systemdLibs ];
  configureFlags = (old.configureFlags or [ ]) ++ [
    "--enable-libudev"
    "--enable-v4l2-request"
  ];
  postInstall = (old.postInstall or "") + ''
    grep -q '^#define CONFIG_H264_V4L2REQUEST_HWACCEL 1$' config_components.h || {
      echo "error: FFmpeg built without the h264 V4L2 Request hwaccel" >&2
      exit 1
    }
  '';
})

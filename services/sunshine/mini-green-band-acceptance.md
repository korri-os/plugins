# Mini V2 encoder geometry, 2026-10-26 (#53)

The right and bottom green bands have the same encoder-storage cause. They
are not caused by Sunshine's rotated KMS capture or row-pair NV12 converter.
The fix belongs in Linux 7.2 Iris, not in an additional approved FFmpeg patch.

## Isolating the stage

All evidence below is on zao under `/tmp/mini-green/`. The original reported
recordings remain under `/tmp/p3/view/mini-base/` and `mini-new/`.

1. The standalone `sunshine-v4l2m2m-probe` creates every source NV12 pixel
   itself. Sunshine, KMS, rotation and libyuv do not run. With the installed
   driver it reproduces both the 1240-wide right band and the 720-high bottom
   band. Source Y is `16+(x+y+frame*4)%220`; all source UV bytes are 128.
2. `old-driver-old-ffmpeg/1280x720.h264.ioctl` records raw OUTPUT `S_FMT`
   returning **1280x736**, stride 1280, sizeimage 1,413,120. CAPTURE is
   1280x720. The raw storage is aligned to 32 rows, not to the visible height.
3. An off-device-built `LD_PRELOAD` observer dumps the first MMAP OUTPUT
   buffer immediately before `VIDIOC_QBUF`. In
   `old-driver-new-ffmpeg/1280x720.output.nv12`, **every** visible Y byte in
   rows 0–719 equals the generated source, and every visible UV byte is 128.
   Only Y rows 720–735 and UV rows 360–367 are zero. The observer source and
   build expression are `dump-output.c` and `dump-output.nix` in that evidence
   directory's parent. `output-evidence.txt` records the assertions.
4. Linux 7.2 `iris_venc_s_fmt_input()` defaults the crop to aligned storage.
   `iris_hfi_gen1_set_resolution()` then sends aligned `fmt_src` and
   `fmt_dst` dimensions as firmware frame sizes, ignoring the crop. Firmware
   scales storage padding into the picture. Zero Y/UV decodes as (0,135,0).
5. The proposed FFmpeg OUTPUT `S_SELECTION` alone does **not** fix gen1.
   It succeeds, but old/new FFmpeg produce byte-identical 1280x720 probe
   bitstreams on the installed driver. The ioctl traces are in
   `old-driver-new-ffmpeg/`. That candidate is not shipped.

The original 0040-only Sunshine baseline recording has solid green rows
706–719 in all 736 content frames. The standalone gradient probe has 12 fully
zero-decoded rows (708–719); filtering at the content/padding boundary differs.
Both receive the same 16 zero source-padding rows, after scaling.

## Kernel contract

The Korri kernel patch
`9999-media-qcom-iris-gen1-visible-encoder-resolution.patch` makes three changes:

- Default crop uses the originally requested visible OUTPUT size.
- Gen1 input HFI frame size uses the crop, including an explicit selection.
- Gen1 output HFI frame size uses the requested scale size, not coded alignment.

The separate HFI stride/plane-height property still describes aligned storage.
Decoder behavior is unchanged. Both default-crop and explicit-selection paths
are tested with the real C setters. Existing approved FFmpeg needs no new ioctl.

An intermediate kernel-only candidate changed the HFI sizes but not the default
crop. It created a new four-row band at 1920x1080 with old FFmpeg. It is rejected;
only the complete default-crop fix is suitable for deployment. No coupled
kernel/plugin rollout or HEVC SPS rewriting is needed.

Sunshine side for final acceptance is the existing #272 fix (0040), unchanged:
`/nix/store/3rfpxmzcg0hvlcc6qnbx4vr1x5x28xvg-korri-plugin`.
The FFmpeg patch set remains
`4aeb0e1fcd2602fca166659fcff9ad74c37abb6d27797ba4eda0c2ef0b7cdf2e`.
The historical untracked repeat-header patch was not copied: the current product
kernel already carries the request-keyframe/repeat-header patches, and recovery
IDRs are checked by decoding each one independently.

## Reproduction and checks

Run only after the owner grants the Mini. Build off-device, sign the exact
module/probe outputs and copy them through the signed Nix store. Load the module
with `rmmod qcom_iris` then `insmod PATH`, with Sunshine Disabled and no encoder
users. Do not replace the installed module or update boot files for this test.

On the Mini, `run-v4l2m2m-probe.sh PROBE_BINARY` now records H.264 and HEVC at
1240x1080, 1280x720 and 1920x1080. Off-device,
`verify-v4l2m2m-streams.py OUTPUT_DIRECTORY` checks all 120 frames per file,
four flagged recovery IDRs, independently decodable headers, exact visible
geometry and the known first-frame pixel coordinates. This last check catches
squeeze even when the SPS dimensions look correct.

The test sources and logs, PNGs, raw streams and simultaneous `grim` screenshots
are retained in `/tmp/mini-green/`. Physical acceptance does not qualify a
persistent system update. The owner must choose that deployment separately.

## Stop/restore incident

The Mini stopped sending SSH banners while `ab-device.sh restore` was stopping
Sunshine after the final 1280x720 recording (2026-10-27 00:11:24 UTC). Ping and
TCP still worked. The final module was loaded. The cause is unresolved; do not
attribute this to storage or to the crop patch without the previous-boot logs.
The detailed chronology and source review are `/tmp/mini-green/hang-chronology.md`.

The last completed final-kernel-only recordings at this point are 1240x1080
(740 content frames) and 1280x720 (721). Both have zero green edges. The 1920
final-kernel-only recording and clean device-state check still need recovery.
Six final-kernel standalone H.264/HEVC probes already pass, including 1920.
Gen1 stop/close firmware waits have a 1000 ms timeout, but the surrounding
instance/core locks and runtime-PM calls can block. The geometry patch does not
change that code. A deployment must account for this unresolved stop incident.

# Sunshine v2026.914 device acceptance — 2026-10-24 to 2026-10-26

Branch `sunshine/upstream-v2026.914`, rebased on main `071bbd7`. Devices tested at
the owner's direction: AYN Odin 2 Portal and Retroid Pocket Mini V2. The RG353M
was added on 2026-10-26, after its RKVENC kernel driver was restored. The
RG35XX Pro was set aside for now.

**Result: the Odin passes. Its picture was sideways on both builds
(korri-os/korri#273); `834f473` fixes that, and the Odin now streams upright
(see `output-transform-acceptance.md`). The Mini
cannot be judged: decoded recordings show that Sunshine's capture on the Mini
returns black frames on the published 2025.924 build as well as on 2026.914,
with both KMS and `capture=wlr` (korri-os/korri#272). The frame counts below
were measured before any picture was decoded and do not show this.
The RG353M passes on its RKMPP encoder (see "RG353M").**

## Picture check (2026-10-26)

Recorded 20 s streams were decoded with FFmpeg and checked frame by frame.

| Device | Build | Decoded frames | Blank frames | Notes |
|---|---|---|---|---|
| Odin | 2025.924 | 1639, 0 errors | 14 (one burst) | sideways picture |
| Odin | 2026.914 | 1618, 0 errors | 5 (one burst) | sideways picture |
| Mini | 2025.924, KMS | 4 runs: 0, 291, 0, 11 blank | | later sessions mostly black |
| Mini | 2026.914, KMS | 4 runs: 924, 787, 1, 1 blank | | later 871-944 of ~1000 |
| Mini | both, `capture=wlr` | 8 runs | all frames black | |

On the Mini, simultaneous `grim` screenshots always showed the correct
picture. The black starts at the EGL import of the compressed scanout buffer
(XR24, modifier `0x500000000000001`); dma-buf fences were already signalled
and `glFinish` did not help. Every Mini frame also has a 14-row green band at
the bottom on both builds (Iris alignment, korri-os/korri#53).

## Method

- Compared builds (aarch64). Main `071bbd7`: plugin `znzzy4dg34rfdlci52wy65zglccsx2hc`,
  Sunshine `s1075aipggxqhkd8ilyh6yic74dpgmyd` (2025.924.154138). Branch: plugin
  `72j8jzmv3gidw23jwkdx10qw8si70vw7`, Sunshine `6amm24blly3ik1arwc1l6n41k2a2x6hl`
  (2026.914.233613).
- The installed `korri-sunshine.service` kept its user, groups, capabilities,
  sockets and hardening. A runtime drop-in replaced only `ExecStart`, and was
  removed afterwards. Builds took turns on the same device and settings.
- Client: moonlight-embedded 2.7.0, `-platform fake -viewonly`, H.264, 10 Mb/s,
  1280x720@60, 75 s per run, over USB. Frames counted by an `LD_PRELOAD`
  observer. Sunshine CPU sampled for 40 s in the middle of each run.
- Packages were built on zao and signed with its Korri builder key. Nothing was
  built on a device, and `require-sigs` stayed on.

## Odin 2 Portal (h264_v4l2m2m, Iris)

| Run | Build | Received fps | Missing frames | Sunshine CPU |
|---|---|---|---|---|
| 1 | main 2025.924 | 60.000 | 0 | 159.4% |
| 1 | 2026.914 | 59.948 | 0 | 152.8% |
| 2 | main 2025.924 | 60.019 | 0 | 155.4% |
| 2 | 2026.914 | 59.923 | 0 | 150.7% |

Mean received fps fell by 0.1%. Sunshine CPU fell by 5.6 points. The only
extra log line is the expected `h264_vulkan` encoder probe failure. A client
paired under 2025.924 kept working on 2026.914.

### korrid certificate control (2026.914)

Driven as korrid (uid and gid 976) on `/run/korri-certificate-control/control.sock`:

- `attest` with the right host UUID matched; a wrong UUID did not.
- Before provisioning, the client was refused.
- `provision` changed state once; a repeat changed nothing.
- The provisioned client authenticated without a PIN and listed `Korri Stream`.
- A client that was never provisioned was refused.
- After `revoke`, the same client was refused again.

No korrid change is needed.

## Retroid Pocket Mini V2 (h264_v4l2m2m, rotated KMS RAM capture 1080x1240, transform 3)

| Run | Build | Received fps | Missing frames | Sunshine CPU |
|---|---|---|---|---|
| 1 | main 2025.924 | 58.015 | 0 | 173.6% |
| 1 | 2026.914 | 49.781 | 0 | 168.4% |
| 2 | main 2025.924 | 57.809 | 0 | 174.4% |
| 2 | 2026.914 | 50.101 | 0 | 166.1% |

Cause of most of the gap: upstream `44bf39be` (#4967). When no new frame is
ready, Sunshine re-sends the previous frame after a minimum-FPS wait. The old
base waited one frame interval (16.7 ms at 60 fps) while its log claimed 33.3 ms.
Upstream fixed the wait to two intervals (33.3 ms), as documented. strace showed
timeout medians of 16.71 ms (old) and 33.76 ms (new).

On the same 2026.914 probe build, `minimum_fps_target=60` raised received fps
from 49.87 to 57.44. Fresh captures stayed at 49.3–49.5 per second. The setting
restores repeated frames, not content, so the branch does not set it.

Remaining open item: main completed about 51.05 fresh captures per second and
the branch about 49.32 (3.4% fewer). The bottleneck is the rotated
`GetTextureSubImage` readback in patch 0033 on the capture thread (p50 5.6 ms
old, 5.9 ms new; p95 25.7 ms old, 29.0 ms new). The DRM worker thread used
0.6% CPU. This difference is not isolated and comes from single sessions.

These Mini numbers count delivered frames only. The later picture check found
many of those frames black on both builds (see "Picture check"), so they do not
show a working stream.

## RG353M (h264_rkmpp, zero-copy KMS DRM_PRIME, 640x480) — 2026-10-26

The device runs the kernel generation from korri-os/korri
`docs/acceptance/rg353m-rkmpp-kernel-2026-10-24.md`: `mpp_rkvenc` binds
`fdf40000.rkvenc` at boot and `/dev/mpp_service` exists. This is the first run
of the 2026.914 RKMPP pacer on RKMPP hardware.

Compared builds (aarch64): main `57de061`, plugin
`znzzy4dg34rfdlci52wy65zglccsx2hc` (unchanged from `071bbd7`), Sunshine
`s1075aipggxqhkd8ilyh6yic74dpgmyd`; branch `0585c7e`, plugin
`8nxfgikp1yld31fbf7i5ypvx4jfkld20`, Sunshine
`zrdgnndckg0wya1na1qa8x5za1cwqmh7`. Same method as above, but 640x480 and
over the RG353M USB link. Every stream was also dumped and decoded in full.

| Run | Build | Received fps | Missing frames | Sunshine CPU |
|---|---|---|---|---|
| 30-1 | main 2025.924 | 30.008 | 0 | 37.3% |
| 30-1 | 2026.914 | 29.995 | 0 | 37.6% |
| 30-2 | main 2025.924 | 30.015 | 0 | 37.2% |
| 30-2 | 2026.914 | 29.998 | 0 | 37.4% |
| 60-1 | main 2025.924 | 60.010 | 0 | 42.7% |
| 60-1 | 2026.914 | 56.356 | 272 | 43.2% |
| 60-2 | 2026.914 | 59.971 | 0 | 42.9% |
| 60-2 | main 2025.924 | 60.014 | 0 | 42.6% |
| 60-3 | main 2025.924 | 60.020 | 0 | 42.8% |
| 60-3 | 2026.914 | 59.994 | 0 | 43.1% |
| 60-4 | 2026.914 | 59.977 | 0 | 43.1% |
| 60-4 | main 2025.924 | 60.014 | 0 | 42.9% |

- Both builds selected `h264_rkmpp` and logged `Using zero-copy KMS DRM_PRIME
  capture for RKMPP` for the session. All 12 recordings decoded at 640x480
  with 0 FFmpeg errors, and the pictures of the two builds match.
- The 2026.914 pacer holds the negotiated rate at 30 and 60 fps. Sunshine CPU
  is within 0.5 points of main.
- 60-1 on 2026.914 lost 272 frames as 16 bursts of exactly 17. Each burst
  followed a client `Video decode unit queue overflow` and an IDR request.
  The three repeat runs, which alternated the build order, lost none. The
  pacer cannot cause a burst of that size: after a stall it emits at most one
  or two catch-up frames, and it is the same schedule as main's, renamed. The
  cause is not isolated; treat it as one unexplained event.
- Server log lines matching "error" fell from 26 to 20. After the client
  connects, each build logs only one: `GPU driver doesn't support universal
  planes: /dev/dri/card0` (Panfrost, while KMS looks for the display
  controller). Both builds report `Executing [Desktop]`, as on the Odin.

### RKMPP buffer failure no longer crashes Sunshine (korri-os/korri#28)

The RG353M kept 23 Sunshine core dumps from 2026-10-24 04:46-04:48 UTC, taken
while `system_heap` was not loaded. All share one stack: `probe_encoders`,
`av_hwframe_get_buffer`, `rkmpp_drm_pool_alloc`, `av_log`, `SEGV_MAPERR`.
`rkmpp_drm_pool_alloc` logged an MPP buffer failure against the RKMPP device
context, which has no `AVClass`. `867da69` logs it against the frames context.

Reproduced by moving `/dev/dma_heap` aside, so MPP 1.1.0 falls back to its DRM
allocator and every allocation fails (`drm_alloc failed ret -1`). Hiding only
`/dev/dma_heap/system`, or removing its group access, makes buffer-group
creation fail earlier and does not reach this path.

| Build, 45 s with `/dev/dma_heap` hidden | SEGV core dumps | Result |
|---|---|---|
| main 2025.924 (`s1075aipg`) | 8, every 7 s, same stack | crash loop |
| branch `867da69` (plugin `nyiw8z3c`) | 0 | `Failed to get MPP buffer: -1`, no working encoder, clean exit |

After `/dev/dma_heap` was restored, the fixed build found `h264_rkmpp` with no
restart. The device was restored to its installed Sunshine, with no drop-in
and no pairing state.

## Not tested on hardware

- Controller input through the protected input seat. Its authority comes from a
  korrid-published launch sidecar that a direct test client does not create.
  `sunshine-korri-input-seat-patch` runs the patched binary in a root VM (x86
  locally; aarch64 in CI).
- RG35XX Pro (set aside); x86 NVENC.

## Device state afterwards

- RG353M: installed Sunshine (2025.924) active, no drop-in, no pairing state.
- Odin: installed Sunshine plugin active, no drop-in, no pairing state.
- Mini: `@korri:sunshine` was installed for this test through `korri-plugin`
  from the bound publisher cache. It is now Disabled. `korri-plugin remove`
  refuses without an authoritative lifecycle policy, so the package record
  remains until removal goes through korrid.

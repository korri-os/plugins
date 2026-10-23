# Odin Cemu — patched Mesa 26.2.5 Turnip, 2026-10-23 UTC

**The patched 26.2.5 Turnip loads the staged BotW save and runs gameplay. No
`Unhandled ALU op`, crash or device loss occurred in 7 launches. The one valid
720p baseline is 42 / 41 / 41 FPS (median / p10 / p1), against 39 / 38 / 36 on
25.3.2. Only 1 of 7 launches reached the save, so this is one sample. The
async-on question and the soak stay open. The Odin was returned to the 25.3.2
test build.**

This continues the [25.3.2 pin](odin2portal-turnip2532-2026-10-23.md) and the
[async-off report](odin2portal-async-off-2026-10-23.md). Branch
`exp/cemu-turnip-26-2-fmadz`. Only USB `root@<device-usb-ip>:2222` was used.
The Mini V2 was not touched. No push, merge or publication occurred.

## Patch and build

| Item | Value |
|---|---|
| Patch | [`patches/mesa-26.2-ir3-fmadz.patch`](../../patches/mesa-26.2-ir3-fmadz.patch): `ir3_context_init` runs its final `nir_opt_algebraic_late` + DCE to a fixed point |
| Upstream draft (not submitted) | [`patches/mesa-26.2-ir3-fmadz.upstream.md`](../../patches/mesa-26.2-ir3-fmadz.upstream.md) |
| Code commits | `fcd4559` (seed `AsyncCompile=false`), `e417888` (patched Turnip) |
| Mesa source | `mesa-26.2.5.tar.xz`, `sha256-eUs9FykHXa5+vUfHKDt8oM213sZo9/EcwKXYL2E4oKU=` |
| Turnip-only ICD (built on fuji) | `/nix/store/g33aq3b8mljbiay5ls6nin7kkwxi3xbq-mesa-turnip-cemu-fmadz-26.2.5` |
| Cemu | `/nix/store/gdjgvqfcqqns4v1k83nxd1mrf29fynvs-cemu-0-unstable-2026-10-22-29f2f1f` |
| Production-namespace plugin, built only | `/nix/store/wyy71hxdls7nkg17xd7r452nc1x3r6s2-korri-plugin` |
| Personal test plugin (from `e417888`) | `/nix/store/35zj7x7favdjq4j8bayb7c0d3vrn9kwz-korri-plugin` |
| Test approval | `4dd5c0e2d7274cf1a8006b6dc69f3e6ca957d99b31c5f2db09ced8531dc37750` |

The Mesa build ran the existing `ir3_disasm` and `ir3_delay_test` on fuji;
both passed. The test plugin uses the same scratch composition as before:
`plugin.ts` with `s/@korri:/@simonwjackson:/g`, built with `mkPlugin`. Its
content is byte-identical to the previous worker's `6qxnpp1x…` build. Only the
input-addressed path differs, because the source tree changed.

## Delivery and installation

Zao signed the closure recursively with its transport key
(`korri-cache-zao-1`). A new zstd file cache was signed with the personal
publisher key (`simonwjackson-plugins-1`). No key was printed or copied.
`nix store verify` passed for both keys. `nix copy` moved the three new store
paths to Odin. The device's private cache
`file:///var/lib/korri-private-cache/cache` received only the three new
narinfos and their NARs, owned `korri:users` 0644. No existing file was
overwritten. On Odin, `nix store verify` against the publisher key passed.
Then `korri-plugin inspect`, exact-approval `update` and `enable` passed.
Device policy stayed `require-sigs=true`, `max-jobs=0`, empty builders,
`fallback=false`. Publisher configuration SHA-256 stayed `c4fb4282…acb3`.

## Bench setup

Native May settings: 1280×720, `GX2DrawdoneSync=false`,
`vkAccurateBarriers=false`, `VSync=0`, FPS++ 45 FPS preset with its 40 FPS
advanced value. `AsyncCompile` was the only native value changed by the test.
The Gamescope modifier was hash-guarded (pre-modifier library `ccc3e6ac…`,
temporary `5f2f907f…`, the same temporary hash as the 25.3.2 runs). Game-layer
`cpu.min=100` and `gpu.min=100` were set by revision-checked RPC. Each run
restored the staged save (`sha256:0f0d9c70…fabfb5a`) and used the earlier
`botw-load.events` route with the bench-only P2 profile. The caches found at
setup (not the old poisoned ones; BotW had been played at 05:34–05:36 UTC)
were copied aside first. The panel was powered on for runs, as before.

## Driver proof

Every launch mapped the patched driver in Cemu and the system driver in
Gamescope (from `/proc/PID/maps` and `environ`):

| Process | `libvulkan_freedreno.so` | `VK_DRIVER_FILES` |
|---|---|---|
| Cemu | `g33aq3b8…-mesa-turnip-cemu-fmadz-26.2.5` | that package's `freedreno_icd.aarch64.json` |
| Gamescope | `nc0xr281…-mesa-26.2.3` (system) | unset |

Cemu's log: `Using GPU: Turnip Adreno (TM) 740`, `Driver version: Mesa 26.2.5`,
`Async compile: false` (or `true` for the async runs). No unit journal or Cemu
log contains `Unhandled ALU op`, `Trace/breakpoint`, `Error -4` or
`VK_ERROR_DEVICE_LOST`. `coredumpctl` recorded no core for any run.
`/run/opengl-driver` still resolves to system Mesa 26.2.3.

**Past the 26.2.3 crash point:** 26.2.3 crashed while loading this save
(pipeline BLAKE3 `026211ce…`, fresh and cached). In `baseline-03` the 30 s frame
is the loading screen (RMSE 0.044 against the 25.3.2 loading frame). The
100/160 s frames match the 25.3.2 Zora's Domain gameplay frames (RMSE 0.009 and
0.019 at 96×54). Frames were compared numerically only and were never opened.
That pipeline's compilation was not traced by hash. The evidence is that the
same save load and scene now run with no compiler error.

## Bench table

All runs: 100 s warm-up after the 40 s input script, then 180 s measurement.
Values are one-second X Present bins. Peaks are `cpu7-middle-thermal`.

| Run | Driver | Async | Reached staged save | median / p10 / p1 / min | Peak °C |
|---|---|---|---|---|---:|
| 25.3.2 `resume…/baseline-02` (earlier) | 25.3.2 | off | yes | **39 / 38 / 36 / 33** | 96.7 |
| 25.3.2 `resume…/soak`, 900 s (earlier) | 25.3.2 | off | yes | **40 / 38 / 34 / 4** | 97.5 |
| `turnip262/baseline-02` | 26.2.5 patched | off | **no** | 45 / 45 / 45 / 36 (title sequence, not comparable) | 86.4 |
| `turnip262/baseline-03` | 26.2.5 patched | off | **yes** | **42 / 41 / 41 / 35** | **95.5** |
| `turnip262/async-on` | 26.2.5 patched | on | no | 45 / 45 / 45 / 44 (not comparable) | 82.4 |
| `turnip262/async-on-02` (`--input-delay 12`) | 26.2.5 patched | on | no (static frame) | 45 / 45 / 45 / 38 (not comparable) | 84.8 |
| `turnip262/async-on-03` | 26.2.5 patched | on | no | 45 / 45 / 44 / 37 (not comparable) | 80.8 |
| `turnip262/soak-aborted-no-load` | 26.2.5 patched | off | no; stopped at 81 s | — | — |
| `turnip262/soak-02-aborted-no-load` | 26.2.5 patched | off | no; stopped at 77 s | — | — |

A run counts as "reached staged save" only if its 30 s frame has the loading-
screen signature and its later frames match the 25.3.2 gameplay frames. The
non-loading runs present at the FPS++ 45 cap with changing frames, lower
temperatures and a 30 s frame unlike the loading screen. They measured the
title/attract sequence. In `baseline-02`, the first launch with the new driver,
`IOSU_ACT` came 19 s after `Run title` (0.7 s in other runs). That is consistent
with the A presses landing before the title was ready. The cause of the other
misses was not found. The bench proves P2 received the presses and the profile
was applied and restored each time.

**Comparison:** the one valid patched baseline is 3 FPS higher at median, p10
and p1 than the 25.3.2 baseline, at a similar peak temperature. It meets the
40 FPS median target that 25.3.2 missed by 1. One sample does not establish a
real difference; run-to-run variance of this route is unknown.

## Async compile on

Three async-on launches on the patched driver had no SIGTRAP, no core and no
`activeVertexDS` assertion. **None of them reached the staged save**, and the
25.3.2 assertion fired while that save was loading. So this is **not evidence**
that the assertion is gone. That question stays open.

## Soak

Not run. Both soak attempts missed the save load and were stopped at the 30 s
check through the run's own exact-stop path, so the bench did not measure the
title sequence for 15 minutes.

## Intervention on another session's object

The first baseline launch was refused by the bench: `External/unknown controller
state`. A second InputPlumber composite, `/org/shadowblip/InputPlumber/CompositeDevice1`
("Microsoft X-Box One pad", profile "Korri Microsoft X-Box One pad", targets
`gamepad1`, `mouse0`, `keyboard0`) had existed since **09:08 UTC**. Another
session created it. Its only source, `evdev://event16`, was last re-added at
**10:45 UTC** and was gone. With the parent's approval, after these guards
passed (0 source devices, no game unit, no foreign emulator or Gamescope
process, no other SSH session), it was stopped at **13:54:07 UTC** through
InputPlumber's normal `Stop` method. Nothing else in InputPlumber changed.
Its full property dump is kept on Odin in
`turnip262/composite1-{introspect,properties}.txt`, so it can be recreated.
CompositeDevice0, seat P1 and `ManageAllDevices=false` were unchanged afterwards.
The refused attempt is kept as `turnip262/baseline-refused-composite`.

## Restoration

`turnip262/restoration.json` and `final-audit.json` (15:05 UTC) prove:

- Library bytes exactly as before the test (`8aa9f6be…`). The modifier bytes
  were restored before the revision-checked RPC unsets. Resolved launch
  settings and layers match the pre-test snapshot.
- Native Cemu settings: the pre-test bytes (`aef6d70d…`, async on) with only
  `Graphic/AsyncCompile=false` (`a1d81eaf…`). This is the parent's decision (B)
  and matches the new shipped seed.
- P1 profile `738dffbb…`. The bench applied and restored P2 in every run.
- Pipeline/driver caches restored to the exact bytes found at setup. The
  test-generated ones were moved to `turnip262/generated-cache/{0,1}`, not
  deleted. `_shaders.bin` was unchanged. The patched driver also added entries
  to the account's `mesa_shader_cache`. Those entries are keyed by driver build
  and were left in place.
- `SessionCompleted`. No game, acquisition or failed unit. Empty host-session
  directory. No Cemu, Gamescope, bench or recorder process. No bench pad. Only
  CompositeDevice0. Same boot `00ca24e7…` and system generation. Panel power off,
  as found.
- Speaker stayed **muted** for the whole campaign. Its volume was 0.50 at setup
  and **0.35** after `soak-02` (15:01–15:04 UTC). Nothing in this campaign sets
  the volume, and the cause was not found. The volume was left as found, muted.
- **Plugin reinstalled to the previous build:** `korri-plugin inspect`, `update`
  and `enable` of `/nix/store/g7adybv05pxjyi1klapk19xrjbm7b0ql-korri-plugin`
  (approval `99fa60a3…`). Its wrapper points at the Mesa 25.3.2 ICD again.
  `previous` now records the patched build.

No unit reset, recovery-journal edit, korrid restart, system update, firmware
write or system Mesa change occurred. No build ran on a device.

## Recommendation

**Keep 25.3.2 on the device for now. Keep the patched 26.2.5 on this
experimental branch, and do not land it as the default yet.**

The patch does its job: the 26.2.x `fmadz` compiler crash is gone in real
gameplay, and the single valid sample is faster (42 vs 39 median). Cost and
open risk: one sample only, no 15-minute soak, no answer to the async-on
assertion, and a save-load route that missed 6 of 7 launches with the new build.
That miss rate is not explained, and it could hide a startup-timing change. Next:
add a load-detection wait to the bench route, or use physical observation. Then
repeat baseline, soak and async-on on the patched build before switching. The
patch is still not submitted upstream. The upstream draft needs a NIR unit test
first.

Evidence: Odin `/var/lib/korri/cemu-bench-staging/turnip262/` (bench reports,
raw Present/telemetry, env/maps, journals, Cemu logs, screenshots,
restoration, audit). Zao `/tmp/cemu-turnip262/t2/` (scripts, signed cache,
delivery logs, numeric image statistics). Screenshots and saves are not
committed.

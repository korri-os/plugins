# Mini V2 BotW ladder — 2026-10-23 UTC

**Data-loss finding:** the owner's `5f3c80b8…` record remains, but 7 of its 58 payload
blobs are missing. Its restore failed. With supervisor approval, the complete May
snapshot `80c5f056…` was selected last instead.

**No Mini configuration has passed a soak.** The 25.3.2 / 620×540 attempts reset the
whole device twice, at 06:57 and 14:46 UTC, before measurement. Patched 26.2.5 reached
verified gameplay but missed median 30 at both higher resolutions. The Mini is idle on
**25.3.2 / 31:27 / 620×540**, with default launch settings, original P1/item bytes and
Speaker muted. This is a fallback, not a stability qualification.

**Correction:** the earlier 827×720 and 620×540 short runs retained the Device
`performance` governor. They did **not** use default launch settings. The private helper
read `layer.cpu.governor`, but the wire stores `layer.governor`. Its revert skipped the
actual field. Revision-checked RPC restored `schedutil` and original 0–100 CPU/GPU
defaults before the second soak attempt.

## Source and delivery

Branch `feat/cemu-mini`, initially `ebbed6a` from `feat/cemu-odin`.

| Commit | Change |
|---|---|
| `492bd65` | First commit: native seed `Graphic/AsyncCompile=false`, only when absent; package/runtime checks require it and preserve an existing person's `true` edit. Temporary workaround for the draw_execute / activeVertexDS race. Cost: synchronous compilation stalls. |
| `4bb37ae` | Optional CC0-1.0 BotW 31:27 aspect and five matching resolutions. Mirrors Github989's 4:3/5:4 pattern, retains original 1280×720 game texture dimensions, exposes Square HUD Mode, changes no selection default. Package check covers choices, conditions and unchanged defaults. |
| `4130355` | Earlier checkpoint while the owner played; superseded by this report. |
| `7aea623` | Formatter-only changes to the touched Nix package and runtime check; Cemu output path unchanged. |

Cemu remains `29f2f1fae4631e2317977debd9eacd55cc28dd7d`. This branch retains the
aarch64-only Turnip 25.3.2 pin. The authorized scratch composition combines this branch
with `exp/cemu-turnip-26-2-fmadz` at merge `f5064b817c2872235aacccb50c5843e6ff033522`;
it adds patched Mesa 26.2.5 without changing the Cemu commit or native choices. No
emulator source patch, CPU-affinity feature, per-device profile or new Korri
configuration schema was added. The README also warns that Cemu's manual pack updater
can remove the local aspect additions.

| Artifact | Exact path |
|---|---|
| Native-aspect Cemu | `/nix/store/lwh1bkqvr2agjs4h6asb32dhg1bamida-cemu-0-unstable-2026-10-22-29f2f1f` |
| Installed personal plugin | `/nix/store/avjc0gvac9b49cc4bapgl23yva0bmbrk-korri-plugin` |
| Native-aspect production plugin, built only | `/nix/store/lg7aw924dyx9i1xj202b8ajr6g9grdl6-korri-plugin` |
| Patched native-aspect Cemu | `/nix/store/wkxzqsyqb52c6zpdi8x90ln9hnghn1gj-cemu-0-unstable-2026-10-22-29f2f1f` |
| Patched personal plugin | `/nix/store/wzgx3daiksdxsa3jscsk7gr0xs2hncvk-korri-plugin` |
| Patched ICD | `/nix/store/g33aq3b8mljbiay5ls6nin7kkwxi3xbq-mesa-turnip-cemu-fmadz-26.2.5` |
| Bench | `/nix/store/ycx1s593595i2c2hyax3l5i58d6iqcw8-korri-cemu-bench-0.1.0` |

Original builds ran on yari and zao, never on a handheld. The combined ARM build used
the supervisor-authorized default daemon builders: Cemu on fuji, package checks on yari;
the combined x86 checks ran on zao. The first explicit `nix-builder-yari` alias failed
to resolve; no target build fallback was used. The personal test composition substitutes
only `@korri:` → `@<publisher>:` in plugin.ts and uses Core's normal mkPlugin builder.
No manifest was rewritten. Zao used the existing transport and personal publisher
signing keys; no key was printed or copied.

Signed `nix copy`, normal `korri-plugin inspect`, exact-approval `install` / `update`,
and `enable` passed. Original 25.3.2 approval:
`c07d4687477d8fbdb1785a12301d79a860dabf30809f30346a9981b7e40a12c1`. The actual pre-
existing Mini cache binding is `file://<plugin-cache>`, not
Odin's cache path. Patched 26.2.5 inspection/update/enable passed with exact approval
`b016bd1063b5e13fd17a354af6dc2c4ea2c530745fdec0401bc1fbc05c47735d`. Its immutable
wrapper points to the patched ICD, ships `AsyncCompile=false`, and contains all native-
aspect presets. The provided earlier 26.2.5 artifact lacked those presets, so it was not
used as-is. Publisher configuration retained SHA-256
`996cf8dafc4800f0f22d40a2c58a1f44f2825b50c02ac8eb68396c02c0871d33`. Signature checks
stayed required; target builders were empty, max-jobs zero, and fallback false. No push,
branch landing, publication or system update occurred. Only the authorized throwaway
integration merge was made.

## Device and save grounding

The supplied generation-29 inventory was no longer current at first contact.
The supervisor authorized generation 30 as found. Its installation and 04:33:28
reboot preceded this run; the supervisor reports it was not from Core
origin/main. Results apply only to this exact system, not an assumed main build.

| Fact | Verified before the reset |
|---|---|
| USB-only route | `root@<device-usb-ip>:2222` |
| System generation | 30 |
| Current / system-profile target | `/nix/store/861m162v29s7cj9dcsfmdr7ldgh5qgfz-nixos-system-rpminiv2-sd-card-26.11.20260923.4975466` |
| Bundle | `/nix/store/c6n0dpw4dn4rm65dp6jbvwdw20kay4qd-korri-bundle-0.0.0` |
| Campaign boot ID | `d3e5cc22-ca07-47e7-8766-3151c22ad060` |
| Running korrid | `/nix/store/44f51pv8m97037rl8ip7anmanv1zykck-korrid-0.0.0/bin/korrid` |
| GPU / Cemu driver | Turnip Adreno 650 / Mesa 25.3.2 |
| Initial free root bytes | 11,808,706,560; no GC needed |
| Speaker | `Volume: 0.00 [MUTED]` at every collected guard/pause audit |

Both korrid's control socket and service were stopped, with no live game, for
the approved offline `catalog pair /var/lib/korri/games/wiiu wiiu`, then started
normally. It added one game, hashed 13,660,330,872 bytes and reported zero
diagnostics. No recovery journal edit or unit reset occurred.

WUA SHA-256 matched
`064e512446009a42e6de6399b6665c96abe820be039cb3b5a968e40591d8c9ff`.
All 54 staged files matched `botw-save.sha256` and were copied beneath the real
account's declared saveRoot. Existing private `.config` required creation as
`korri`, not `korrid`; no unrelated account permissions were broadened.

Initial launches encountered synced Odin save-history splits: heads
`43947273…` / `c11f33a0…`, then a later arriving `e7f6f30c…` head. The supervisor
approved supported `app.saves.restore` of the exact staged snapshot:
`sha256:80c5f05621c3f48a86622995eb65ea8cd390b80fb36b64d7fe85a18c932f5ae0`.
Its 54 file hashes equal the staging manifest. History was retained, not edited.
Every native rung restored that snapshot. Actual Cemu slot-3 game_data.sav reads
were observed by fanotify **after** launch-time materialization, avoiding the
earlier inode-watch limitation. No movement followed loading. The scene was not
visually identified; it is not a verified shrine or Zora's Domain claim.

### Owner's real session — requested final source, payload unavailable

Bench paused when the unowned unit
`korri-game-36656694d99744650abe6bc6acb66322.service` appeared at 06:17:58.
It was left alone. At 06:29:32, after the owner's go, korrid/native state was
idle and save status was Synced with one head:

```text
sha256:5f3c80b89dc30d31241ab548f5df818f42362714cfbd7c1cd766213b41bc8f77
endedAt: 2026-10-23T06:26:26.000Z
durationSeconds: 509
```

That duration/start time matches the owner's session, not a bench run. Its record was
saved privately before further staged restores. At that point the history/status was
captured, not a verified backup of every payload blob.

The final supported `app.saves.restore(5f3c80b8…)` failed with `SavePayloadUnavailable`:
“This save's files are not available on any reachable device.” **The exact owner-session
payload was not restored.**

This worker verified the Mini's actual `/var/lib/korrid/saves/objects` files, using the
`sha256` and `bytes` from the real record. The record has 58 files: 51 blobs exist and
pass size/SHA-256, while these seven are missing:

- `00050000/101c9400/user/80000001/3/game_data.sav`
- `00050000/101c9400/user/80000001/3/caption.sav`
- `00050000/101c9400/user/80000001/3/caption.jpg`
- `00050000/101c9400/user/80000001/option.sav`
- `00050000/101c9400/user/80000001/tracker/trackblock01.sav`
- `system/act/80000001/account.dat`
- `system/pdm/80000001/PlayStats.dat`

The supervisor independently reported the same record and the same seven missing blobs
on Odin; this worker did not access Odin. No other authorized payload source exists. No
file was hand-copied and no history record was edited.

Timeline: owner session ended **06:26:26**; staged restores and benches followed;
unclean resets occurred at **06:57** and **14:46**; patched benches followed at
15:19–15:37. Missing blobs were found only during final restoration. **Cause is
unknown:** retention/object GC versus an unsynced write lost during the resets has not
been distinguished. Record presence and earlier Synced status are not proof of payload
availability. The supervisor will file the Korri finding at Land; this worker did not
file an issue.

Under the supervisor's explicit fallback instruction, all **54/54** blobs of May source
`80c5f056…` were checked by size and SHA-256, then selected through `app.saves.restore`.
Its new continuation preserves the owner's record in its ancestry, but its payload is
the older May save, **not** the lost owner session. No game was launched after this
selection. Future bench preflight must verify and preserve the owner's payload, not only
its history record; that cannot recover the seven missing blobs now.

## Native-aspect selection and output

The owner superseded 16:9 during `baseline-03`; that exact bench was interrupted
normally. All subsequent tests used the account's own native preset entries:

- Aspect: `31:27 (1240x1080 handheld)`.
- Square HUD: `Enabled (Experimental, Will Have Some Issues)`, exposed by the
  upstream near-square pattern. Its visual correctness remains unreviewed.
- FPS++ normal `30FPS Limit`, retained advanced
  `30FPS (ideal for 240/120/60Hz displays)`; Cemu logged an active **30 FPS** limit.
- May settings: `GX2DrawdoneSync=false`, `vkAccurateBarriers=false`, `VSync=0`;
  `AsyncCompile=false`; multi-core recompiler.
- Native Cemu `Graphic/FullscreenScaling=1` (`kStretch`, CemuConfig.h) to fill
  the exact output, including rounding in low-resolution choices.

The initial short passing resolution was **620x540**: 334,800 pixels, exactly one
quarter of the panel's 1,339,200 logical pixels. It retained the Device `performance`
governor due the helper error above. No taskset, TU_DEBUG or CPU profile change was
used. The resumed tests verified default launch settings before each launch. The
plugin's shipped selection stays 16:9/unselected for others. Existing account packs were
explicitly upgraded with a hash guard, not silently rewritten by the wrapper.

Captured native-baseline Gamescope argv includes:

```text
--backend wayland --fullscreen --expose-wayland
--output-width 1240 --output-height 1080 -- <Cemu and literal game argv>
```

Actual chain: korrid plugin-launch → Gamescope → gamescopereaper → Cemu.
Bubblewrap was not observed. Actual mappings showed Cemu on pinned 25.3.2 and
Gamescope on system Mesa 26.2.3, with no Gamescope ICD override.

**Numeric pixels only:** no screenshot was opened in a viewer or with the read tool.
Native-baseline screen-160.png is 1240×1080 with **0 / 0 / 0 / 0** contiguous near-black
rows/columns (top / bottom / left / right, mean ≤1/255). Outer-edge luminance means were
94.24 / 79.37 / 100.65 / 75.81 on a 0–255 scale. The 16:9 reference had 191 / 192 black
top/bottom rows. This proves no captured broad letterboxing for the native baseline,
**not** HUD/menu readability, spacing or clipping correctness. Later raw screenshots
were retrieved after USB returned. The old 620×540 and 827×720 frames also have zero
black edge strips. The patched 1028×896 and 827×720 gameplay frames are 1240×1080 with
zero edge strips. Their numeric statistics are retained privately. Owner visual
acceptance is still needed for the experimental Square HUD choice.

## Measured ladder

Original 25.3.2 rungs: 30 s input delay and the same 40 s load script, then **100 s
warmup + 180 s sample**. FPS is nearest-rank percentiles of one-second X Present bins,
not compositor Hz or reciprocal frame-time percentiles. Peaks include warmup. The keep
rule prioritizes median, then p10; an isolated p1/min improvement alone did not justify
a clock change.

Paths below are relative to
`/var/lib/korri/cemu-bench-staging/mini-ladder-20261023/` on the Mini.

| Rung | Setting | Aspect / internal resolution | Median | p10 | p1 | Peak °C | Kept / reverted | Screenshot |
|---|---|---|---:|---:|---:|---:|---|---|
| Reference `baseline-02` | May, async off, FPS++ 30; save read untraced in this run | 16:9 / 1280×720 | 30 | 30 | 30 | 70.5 | Reference only, superseded | `baseline-02/screen-160.png` |
| 1 `native-baseline` | May, async off, FPS++ 30, Square HUD, fill scaling, default clocks | 31:27 / 1028×896 | 25 | 24 | 22 | 87.2 | Baseline; below target | `native-baseline/screen-160.png` |
| 2 `clocks` | Game cpu.min=100 / gpu.min=100 | 31:27 / 1028×896 | 25 | 24 | 23 | 88.0 | **Reverted**, no median/p10 gain | `clocks/screen-160.png` |
| 2 `governor` | Device governor=performance, game minima absent | 31:27 / 1028×896 | 25 | 24 | 23 | 88.4 | No median/p10 gain; attempted revert failed, corrected at 14:31 | `governor/screen-160.png` |
| 3 `resolution-827x720` | Resolution; Device governor=performance retained | 31:27 / 827×720 | 29 | 28 | 27 | 89.2 | Intermediate improvement, superseded | `resolution-827x720/screen-160.png` |
| 3 `resolution-620x540` | Resolution; Device governor=performance retained | 31:27 / 620×540 | **30** | **30** | **29** | **85.7** | **Initial passing short rung only** | `resolution-620x540/screen-160.png` |
| Patched 26.2.5 `patched-1028x896-r2` | May, async off, 30 cap, verified schedutil/default limits | 31:27 / 1028×896 | 25 | 24 | 24 | 88.0 | **Below target**, min 23; gameplay proven | Host `frames-patched-1028x896-r2/*post-title-100.png` |
| Patched 26.2.5 `patched-827x720` | May, async off, 30 cap, verified schedutil/default limits | 31:27 / 827×720 | 29 | 29 | 28 | 86.8 | **Below median target**, min 26; gameplay proven | Host `frames-patched-827x720/*post-title-100.png` |
| Soak `soak` | 25.3.2, 620×540, performance governor | 31:27 / 620×540 | — | — | — | 86.1 | **Failed:** uncontrolled reset before measurement | Zero-byte screen-30.png |
| Soak `soak-return2532` | 25.3.2, 620×540, verified schedutil/default limits | 31:27 / 620×540 | — | — | — | 77.1 | **Failed:** second uncontrolled reset before measurement | Zero-byte screen-30.png |

Best-rung minimum: **27 FPS**. 827×720 minimum: 26; clocks/governor minimum:
22 / 23; native-baseline minimum: 12. A zero placeholder from a refused run is
never a measured result. The 16:9 reference is not a qualified same-scene aspect
A/B, so its difference must not all be attributed to aspect ratio.

The later instruction was to stop climbing once the target held with margin. 620×540
meets median 30 with p10 three FPS above 27. Therefore 413×360, Gamescope FSR, shadows,
AA, LOD/draw distance, CPU options, affinity and further pack/CPU changes were not run.
The later Mesa candidate was separately authorized. No AO option was found in Github989.
The independent barrier skip is already covered by vkAccurateBarriers=false at this pin.
TU_DEBUG stayed unset. No new schema-dependent gain was claimed or shipped.

Other attempts: `baseline` and `native-baseline-refused` stopped before Cemu
because of save splits; `baseline-03` was interrupted at the native-aspect
instruction. They have no qualified complete sample.

### Patched-driver input and gameplay proof

Per the supervisor's Odin warning, capped title-screen FPS is never a result. The first
1028×896 attempt (`patched-1028x896`) is **not measured**: it sent no input and ended at
a 120 s title-gate deadline. Whole-frame color matching was too strict because BotW's
title backgrounds vary; it did not prove failure to reach the title. No FPS value from
that attempt is accepted.

The private bench-only revision waits for two successive title-foreground matches before
starting the unchanged three-A load script. The foreground mask has 880 white pixels
shared across all five earlier pre-input frames, excluding all five verified gameplay
frames. Whole-image backgrounds are not the gate. It requires 95% of that mask to remain
near-white in two captures. Screenshots are analyzed only with Pillow; none is
displayed. A copy of the existing bench changes only its pre-input wait; product/plugin
launch behavior is unchanged.

After the title gate, host captures at about +30 s and +100 s record transition and
gameplay statistics. Gameplay must match the earlier slot-3 gameplay frames (31×27 RGB
descriptor MAE below the calibrated 31.484/255 boundary, and closer than all pre-input
reference frames). Calibration accepts five gameplay and two title-like positives and
rejects all five non-gameplay references. Final run acceptance also requires the actual
post-launch Cemu slot-3 game_data.sav read, 100 s warmup and 180 s complete Present
bins. No scene proof means **not measured**. The valid 1028×896 retry matched title
foreground at 38.9/45.6 s and released input at 47.1 s after launch. Its +30 s frame has
gameplay MAE108.319/255 (loading transition, inferred from sequence); its +100 s frame
has gameplay MAE3.552 versus title MAE51.288. These offsets are from title readiness,
not from process launch. It then completed all 180 gameplay bins with the expected
slot-3 read. Cemu logged Mesa 26.2.5 / Adreno 650 and mapped the exact patched ICD.
Median/p10 remained 25/24, so it failed the performance target. The 827×720 run also
reached gameplay: its +100 s frame has gameplay MAE5.136, title MAE50.856 and zero
title-mask coverage. The +30 s transition frame has gameplay MAE107.016. No title-screen
FPS is accepted. The 827×720 run completed 180 gameplay bins at **29 / 29 / 28 FPS**,
minimum 26, peak 86.8 °C. Both patched runs used verified schedutil/default limits and had
no reset. Neither reaches median 30, so neither justifies the higher resolution. These
are not controlled thermal A/Bs across bundles/start states. The supervisor required
short tests only; no patched-driver soak was run.

## Reset investigation and resumed device identity

| UTC | Verified evidence |
|---|---|
| 06:57:14.872747 | Host campaign log returned the completed 620×540 result and issued the soak command. |
| 06:57:50.200450 | Previous Mini journal's final entry. No shutdown or reboot request follows. Last durable guard was 34.1 s into startup; no measurement or Cemu game_data.sav read was recorded. |
| 06:58:25 / 06:58:31 | Zao's NCM transmit-queue watchdogs. These are USB-network watchdogs, **not** GPU-watchdog evidence. |
| 06:58:36 / 06:58:53 | Host saw Mini USB disconnect and re-enumeration. Mini boot became `745719f5-0810-42ae-977b-11f0c3b71f4b`. |
| 07:06–07:59 | Zao later rebooted eleven times. Its earlier boot continued through 07:00:31, so no simultaneous zao reboot explains the first Mini event. |
| 13:31–13:32 | USB enumeration and direct USB route absent; hardware work stopped. No LAN/Tailscale fallback. |
| 14:21:30 | USB returned, same `745719f5…` boot, generation 30 and system unchanged, no game. Thus the 13:31 absence does **not** establish another Mini reboot. |
| 14:05:35 / 14:24:35 | Journals prove external bundle changes: `vxmm8d95ndax40x650pz47bgxyif05bk-korri-bundle-0.0.0`, then `3cwcwp1m7890gmim78wi51mqj99789aw-korri-bundle-0.0.0`. Adopted as found with supervisor approval; this worker did not activate them or restart their units. |
| 14:31 | Verified original BotW item bytes restored while preserving three unrelated new catalog items; P1 restored, Speaker resolved by name/muted, governor explicitly reverted to schedutil, all limits at original defaults. |
| 14:45 | Second 25.3.2 / 620×540 soak started, with enabled personal plugin and unchanged publisher trust checked before launch. |
| 14:45:42.494982 | Last durable previous-boot journal entry: UFS write-booster buffer warning. Last valid guard: 31.4 s, Speaker muted, no critical trip. No measurement or game_data.sav read. |
| 14:46:27.911058 / 14:46:44.896702 | Host USB disconnect/re-enumeration, followed by new boot `786223b4-f3b2-4708-afad-30c1df1a3338`. Same system and `3cwc…` bundle. |

Both attempts are **failed soaks**, not measured low-FPS results. Their zero-byte
screenshots and NUL-padded/truncated logs are retained as crash evidence, not images or
valid complete samples. No screenshot was opened. The supervisor then authorized only
patched-driver **100 s + 180 s short runs**, with verified default governor, and
required all game testing to stop on another reset.

| Candidate | Evidence and limit |
|---|---|
| Thermal shutdown | No collected critical trip. Second attempt's observed peak was 77.1 °C; last sample maximum 71.7 °C. Monitoring ended before reset, so this cannot exclude a later thermal/power event. |
| GPU/kernel hang | Neither previous boot records an msm/adreno fault, GPU hang or kernel panic at the cutoff. Earlier first-boot DPU `no encoder found for crtc 0` errors exist, but do not establish a reset cause. `/sys/fs/pstore` is empty after the second reset. Absence of a durable error is not proof that the GPU was healthy. |
| Battery / power / cable | Last second-attempt sample: battery 25%, 3.778310 V, status Charging, 29 °C; charger 4.617296 V, health Good, online; USB source 5 V/3 A reported. These are one pre-reset sample, not transient measurements. No latched PMIC reset reason was found. |
| Memory / storage | Last MemAvailable was 2,986,384 kB; no OOM record. UFS reported `dCurWBBuf: 0 WB disabled until free-space is available` before and during the second attempt. Root still had 9.8 GiB available (91% used). This warning alone is not a proven storage failure or full filesystem. |
| Userspace | Both reset before a measured sample or observed gameplay-save read. A normal Cemu exit does not explain the whole-device reboot. |

**Root cause remains undetermined. No configuration has passed a Mini soak.** No reboot
command, system activation, firmware/partition write, unit reset, recovery-journal edit,
target build or trust weakening was issued.

## Final restoration

Completed at **2026-10-23T15:43:48Z**, except the unavailable owner payload described
above. Old morning-recovery commands are superseded and must not be run.

| State | Verified final result |
|---|---|
| Build | Normal inspect/update/enable restored personal plugin `avjc0gva…`, Cemu `lwh1bkqv…`, Turnip 25.3.2; original exact approval `c07d4687…`. Patched build remains previous, not selected. |
| Native account | 31:27 / 620×540, FPS++ 30, Square HUD, fill scaling, May settings and async off; exact tested snapshot SHA-256 `b9d04b3439647b51db1febe7eedd0df3538408db38867e96e92ba812005a41f1`. |
| Launch settings | Original CPU/GPU 0–100, no Game minima, Device governor absent/resolved schedutil; actual CPU policies all schedutil. No taskset, TU_DEBUG or native CPU-profile experiment retained. |
| Library | Exact original BotW item bytes; three unrelated added catalog items preserved. Whole-file SHA-256 `ed7e632cd175f4c6572bd9e1065b35872b763a0a441de2800a6dd534050211e6`. |
| P1 / input | Original SHA-256 `738dffbb744252cd1a089411cc54640626e7157984fa263db3e7b697610ba25a`, original metadata, UID/GID 1000:1000; no bench pad; only CompositeDevice0; ManageAllDevices=false. |
| Audio / processes | Speaker resolved by name and `Volume: 0.00 [MUTED]`; idle RPC/native state, no game/acquisition units, no Cemu/wrapper/bench processes, empty host-session directory. |
| Identity / trust | Same generation 30/system; bundle `3cwcwp1m7890gmim78wi51mqj99789aw-korri-bundle-0.0.0`; boot `786223b4-f3b2-4708-afad-30c1df1a3338`; publisher SHA unchanged and signatures required. No third reset. |
| Save — last mutation | Owner5f restore failed. Approved complete source `80c5f056…` selected as continuation `sha256:466882dd8033a57f3454e1c7dffa4804d3ace969ce77bda4fc0e7025a43c3b1e`; save-location payload equals May source, all 54 source blobs verified, ancestry reaches owner5f. One head, status NotChecked (not a peer-sync claim). No subsequent game/config mutation or launch. |

The final default-governor fallback itself has **not** passed a completed short sample
or a soak. Its earlier 30/30 short result was under performance governor. Do not present
this as a qualified 30 FPS configuration.

## Checks and retained evidence

Final focused ARM and x86 package/admission checks passed, including strict
TypeScript/callback tests, installed-wrapper ShellCheck, Turnip selection, new
aspect/default checks, real Cemu CLI/Xvfb/offline-pack startup and native-edit
preservation, and actual Core admission/execution. The new seed/aspect assertions
first failed against their previous packages, then passed. An initial red Nix
help probe timed out at 15 seconds; direct real help and subsequent full focused
checks passed. No full repository suite or full verification ran.

Final ARM check outputs: `i2ss08h7…-korri-cemu-package-check` and `wm9hyl52…-korri-cemu-admission`; x86: `4f4qyjik…-korri-cemu-package-check` and `75d467gi…-korri-cemu-admission`. Those original architecture builds used explicit builders (yari for ARM;
empty builders/local max-jobs1 for x86), never a target build. The pinned scratch
integration also passed ARM package/admission outputs `vygw0l9m…` / `4q8shfj0…` and x86
`xn31cz9h…` / `9nxaivbi…`. Its ARM jobs used the approved default daemon machines after
the alias failure; x86 used empty builders/local max-jobs1. The combined package checks
include the exact installed ir3 patch, actual ICD/library and unchanged global selection
defaults.

Also passed: 12 bench unit tests, mypy/Ruff/format on its 9 Python files;
mypy/Ruff/format on both touched Python checks; Nixfmt on the two touched Nix files;
Python compilation; git diff --check; commit-hook secret scans. The outside-sandbox real
Cemu `--setgid-account` check was rerun successfully on zao after the outage, managed
with keepAfterChild=true. Formatter changes leave the actual ARM Cemu output unchanged.
All five completed native 25.3.2 rungs were retrieved and independently reproduced from
raw Present CSV: 180/180 bins match each recorded array. The patched 1028×896 and
827×720 runs likewise reproduce all 180 bins each. The combined three Python checks
passed mypy, Ruff and format; its three Nix files passed Nixfmt. The 12 bench unit tests
were rerun and passed. Numeric frame-classifier calibration used real captured images;
no image viewer was used.

Private zao evidence: `/tmp/cemu-mini-evidence/` (0700). Important files: `second-reset-{journal,kernel,cemu.log}`, `second-reset-recovery.json`, `combined-{arm-build-default,x86-checks}.log`, `patched-*`, `frames-patched-*`, `foreground-calibration-test.txt`, `run-gated-host.py`, `campaign-resume.log`, `resume-owner-state.json`,
`native-baseline-edge-stats.json`, `host-kernel-reset-window.txt`, `host-boots-utc.txt`,
`reset-preflight.txt`, `final-{arm-checks,x86-checks,setgid-runtime}*`, and the
superseded `morning-restore.py`. Final restoration uses the reviewed private `final-restore-selected.py` for configuration; the failed owner-restore log and approved
fallback are retained in `final-owner-selected.log`, `save-payload-audit.json`, `final-fallback-save-selected.json`, its source-metadata correction
`final-fallback-proof-corrected.json`, and `final-readonly-audit.json`, not hidden by a
restoration-success claim. Device evidence: `/var/lib/korri/cemu-bench-staging/mini-ladder-20261023/`. Screenshots, saves, helper code and private histories are not
committed.

| Acceptance | Result |
|---|---|
| Median ≥30; p10 ≥27 at native aspect | **Historical short pass only:** 30/30 at 620×540 with performance governor. Patched/default 1028×896 25/24 and 827×720 29/29 fail median. Final default-governor fallback is unqualified. |
| 15-minute soak, no crash | **Failed:** two uncontrolled resets on 25.3.2/620×540; no completed measurement. No Mini configuration passed a soak. |
| Requested patched-driver short tests | **Completed with gameplay proof:** 100 s + 180 s each, expected driver/maps, save I/O and numeric frames. One earlier gate timeout is not measured. |
| Native files/existing launch settings; neutral shipping defaults | **Passed:** no new Korri schema, affinity/debug default or global 31:27 selection. |
| Default launch settings, original item/P1, mute and idle restored | **Passed**, independently audited after final selection. |
| Exact owner's latest session restored | **Failed: data-loss finding.** Seven of 58 blobs missing; approved verified May fallback selected last instead. |
| Native output / HUD and menus | Zero black edge strips at 1240×1080 on captured gameplay; visual HUD/menu correctness remains **not established**. |

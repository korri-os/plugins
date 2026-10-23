# Mini V2 BotW ladder — 2026-10-23 UTC

**Best passing rung so far: 31:27, 620×540, FPS++ 30, default launch settings:
30 / 30 / 29 FPS (median / p10 / p1), peak 85.7 °C.**

**Soak: not run (device lost). Final restoration: blocked by device loss.**
Correction to the earlier live status: a soak command was issued, but its startup
was not independently confirmed and no completed soak result was collected.
Do not treat the short passing rung as a 15-minute stability qualification.

At 13:32 UTC the supervisor confirmed that the Mini no longer enumerates on USB
and required hardware work to stop. No LAN or Tailscale route was used. The
morning recovery commands below are **not yet executed**.

## Source and delivery

Branch `feat/cemu-mini`, initially `ebbed6a` from `feat/cemu-odin`.

| Commit | Change |
|---|---|
| `492bd65` | First commit: native seed `Graphic/AsyncCompile=false`, only when absent; package/runtime checks require it and preserve an existing person's `true` edit. Temporary workaround for the draw_execute / activeVertexDS race. Cost: synchronous compilation stalls. |
| `4bb37ae` | Optional CC0-1.0 BotW 31:27 aspect and five matching resolutions. Mirrors Github989's 4:3/5:4 pattern, retains original 1280×720 game texture dimensions, exposes Square HUD Mode, changes no selection default. Package check covers choices, conditions and unchanged defaults. |
| `4130355` | Earlier checkpoint while the owner played; superseded by this report. |
| `7aea623` | Formatter-only changes to the touched Nix package and runtime check; Cemu output path unchanged. |

Cemu remains `29f2f1fae4631e2317977debd9eacd55cc28dd7d`. The aarch64-only
Turnip 25.3.2 pin remains. No emulator source patch, CPU-affinity feature,
per-device profile or new Korri configuration schema was added. The README also
warns that Cemu's manual pack updater can remove the local aspect additions.

| Artifact | Exact path |
|---|---|
| Native-aspect Cemu | `/nix/store/lwh1bkqvr2agjs4h6asb32dhg1bamida-cemu-0-unstable-2026-10-22-29f2f1f` |
| Installed personal plugin | `/nix/store/avjc0gvac9b49cc4bapgl23yva0bmbrk-korri-plugin` |
| Native-aspect production plugin, built only | `/nix/store/lg7aw924dyx9i1xj202b8ajr6g9grdl6-korri-plugin` |
| Bench | `/nix/store/ycx1s593595i2c2hyax3l5i58d6iqcw8-korri-cemu-bench-0.1.0` |

Builds ran on yari and zao, never on a handheld. The personal test composition
substitutes only `@korri:` → `@<publisher>:` in plugin.ts and uses Core's normal
mkPlugin builder. No manifest was rewritten. Zao used the existing transport
and personal publisher signing keys; no key was printed or copied.

Signed `nix copy`, normal `korri-plugin inspect`, exact-approval `install` /
`update`, and `enable` passed. Final approval:
`c07d4687477d8fbdb1785a12301d79a860dabf30809f30346a9981b7e40a12c1`.
The actual pre-existing Mini cache binding is
`file://<plugin-cache>`, not Odin's cache path.
Publisher configuration retained SHA-256
`996cf8dafc4800f0f22d40a2c58a1f44f2825b50c02ac8eb68396c02c0871d33`.
Signature checks stayed required; target builders were empty, max-jobs zero,
and fallback false. No push, merge, publication or system update occurred.

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

### Owner's session, preserved for final selection

Bench paused when the unowned unit
`korri-game-36656694d99744650abe6bc6acb66322.service` appeared at 06:17:58.
It was left alone. At 06:29:32, after the owner's go, korrid/native state was
idle and save status was Synced with one head:

```text
sha256:5f3c80b89dc30d31241ab548f5df818f42362714cfbd7c1cd766213b41bc8f77
endedAt: 2026-10-23T06:26:26.000Z
durationSeconds: 509
```

That duration/start time matches the owner's session, not a bench run. Its
record was saved privately **before** further staged-save restores. It is newer
than staging and is the exact source to select **last** in morning recovery.
Do not leave the owner on staging or a later bench capture. Supported restore
appends a new continuation record; the selected source's game-save payload must
match the owner's record even though the new continuation has a different ID.

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

The best passing account configuration changes only Resolution to **620x540**:
334,800 pixels, exactly one quarter of the panel's 1,339,200 logical pixels.
It requires no retained game/device clock override, taskset, TU_DEBUG or CPU
profile change. The plugin's shipped selection stays 16:9/unselected for others.
Existing account packs were explicitly upgraded with a hash guard, not silently
rewritten by the wrapper.

Captured native-baseline Gamescope argv includes:

```text
--backend wayland --fullscreen --expose-wayland
--output-width 1240 --output-height 1080 -- <Cemu and literal game argv>
```

Actual chain: korrid plugin-launch → Gamescope → gamescopereaper → Cemu.
Bubblewrap was not observed. Actual mappings showed Cemu on pinned 25.3.2 and
Gamescope on system Mesa 26.2.3, with no Gamescope ICD override.

**Numeric pixels only:** no screenshot was opened in a viewer or with the read
tool. Native-baseline screen-160.png is 1240×1080 with **0 / 0 / 0 / 0**
contiguous near-black rows/columns (top / bottom / left / right, mean ≤1/255).
Outer-edge luminance means were 94.24 / 79.37 / 100.65 / 75.81 on a 0–255 scale.
The 16:9 reference had 191 / 192 black top/bottom rows. This proves no captured
broad letterboxing for the native baseline, **not** HUD/menu readability,
spacing or clipping correctness. Later screenshots were created but their edge
statistics could not be retrieved after device loss. Owner visual acceptance is
still needed for the experimental Square HUD choice.

## Measured ladder

Completed native rungs: 30 s input delay, the same 40 s load script, then
**100 s warmup + 180 s sample**. FPS is nearest-rank percentiles of one-second
X Present bins, not compositor Hz or reciprocal frame-time percentiles.
Peaks include warmup. The keep rule prioritizes median, then p10; an isolated
p1/min improvement alone did not justify a clock change.

Paths below are relative to
`/var/lib/korri/cemu-bench-staging/mini-ladder-20261023/` on the Mini.

| Rung | Setting | Aspect / internal resolution | Median | p10 | p1 | Peak °C | Kept / reverted | Screenshot |
|---|---|---|---:|---:|---:|---:|---|---|
| Reference `baseline-02` | May, async off, FPS++ 30; save read untraced in this run | 16:9 / 1280×720 | 30 | 30 | 30 | 70.5 | Reference only, superseded | `baseline-02/screen-160.png` |
| 1 `native-baseline` | May, async off, FPS++ 30, Square HUD, fill scaling, default clocks | 31:27 / 1028×896 | 25 | 24 | 22 | 87.2 | Baseline; below target | `native-baseline/screen-160.png` |
| 2 `clocks` | Game cpu.min=100 / gpu.min=100 | 31:27 / 1028×896 | 25 | 24 | 23 | 88.0 | **Reverted**, no median/p10 gain | `clocks/screen-160.png` |
| 2 `governor` | Device governor=performance, game minima absent | 31:27 / 1028×896 | 25 | 24 | 23 | 88.4 | **Reverted**, no median/p10 gain | `governor/screen-160.png` |
| 3 `resolution-827x720` | Resolution only | 31:27 / 827×720 | 29 | 28 | 27 | 89.2 | Intermediate improvement, superseded | `resolution-827x720/screen-160.png` |
| 3 `resolution-620x540` | Resolution only; default launch settings | 31:27 / 620×540 | **30** | **30** | **29** | **85.7** | **Best passing rung so far** | `resolution-620x540/screen-160.png` |
| Soak request | Best 620×540 configuration | 31:27 / 620×540 | — | — | — | — | **Not run (device lost)** | No soak screenshot collected |

Best-rung minimum: **27 FPS**. 827×720 minimum: 26; clocks/governor minimum:
22 / 23; native-baseline minimum: 12. A zero placeholder from a refused run is
never a measured result. The 16:9 reference is not a qualified same-scene aspect
A/B, so its difference must not all be attributed to aspect ratio.

The later instruction was to stop climbing once the target held with margin.
620×540 meets median 30 with p10 three FPS above 27. Therefore 413×360,
Gamescope FSR, shadows, AA, LOD/draw distance, CPU options, affinity and further
patches were not run. No AO option was found in Github989. The independent
barrier skip is already covered by vkAccurateBarriers=false at this pin.
TU_DEBUG stayed unset. No new schema-dependent gain was claimed or shipped.

Other attempts: `baseline` and `native-baseline-refused` stopped before Cemu
because of save splits; `baseline-03` was interrupted at the native-aspect
instruction. They have no qualified complete sample.

## Unclean reset and later USB loss: cause undetermined

| UTC | Evidence / confidence |
|---|---|
| **06:57:14.872747** | **Verified:** last host campaign-log modification contains the completed 620×540 result, then `TARGET WITH MARGIN: stop climbing; soak resolution-620x540`. The next call invokes run.py soak. Clock/governor rungs had already finished. |
| Around **06:57:50** | **Reported by supervisor:** Mini's previous journal stops without a shutdown or reboot request; it later booted the same generation 30. The cutoff is about 35 s after the soak command, before its prescribed warmup could finish. Device journal/kernel were not retrieved by this worker. |
| **06:58:25 / 06:58:31** | **Verified in zao's previous-boot kernel journal:** the Mini's cdc_ncm interface reports transmit-queue NETDEV WATCHDOG timeouts. This is a **host USB-network watchdog**, not evidence of a Mini GPU watchdog. |
| **06:58:36.487205** | **Verified:** the Mini's USB device disconnects. |
| **06:58:53.379234** | **Verified:** `RP Mini V2 NixOS`, serial `rpminiv2-nixos`, re-enumerates; NCM and ACM return. |
| **07:11** | **Reported by supervisor:** Mini had been up about 12 minutes, idle, with no game unit. Post-reset files/settings were not audited by this worker. |
| **07:06:48–07:59:45** | **Verified host boot history:** zao subsequently had eleven new boots. Its old boot journal continued through 07:00:31. A simultaneous zao OS reboot therefore does not explain the earlier 06:57 Mini event. Other shared power/USB faults remain untested. |
| **13:31–13:32** | **Verified:** no <device-usb-ip> interface; routing <device-usb-ip> falls back to the LAN gateway; USB SSH times out. **Supervisor confirmed** no Mini gadget or serial enumeration and ordered hardware work stopped. No alternative route was attempted. |

| Candidate | What is known / missing |
|---|---|
| Thermal shutdown | Last completed rung peaked at 85.7 °C; recorded CPU/GPU critical trips are 110 °C, PMIC 145 °C. No collected guard reported a critical trip. Reset-time sensor/kernel evidence is missing; this does **not** rule thermal shutdown out. |
| GPU/kernel hang | Completed rung exited successfully; no collected crash/device-loss guard fired. Soak startup's device log/kernel/pstore are missing. The host NCM timeout proves loss of USB service, not its GPU cause. |
| Battery / power / cable | Capacity, voltage and reset-time supply state were not measured. Battery temperature is not a charge/voltage measurement. No cause can be assigned from the retained data. |
| Userspace Cemu exit | No completed-rung Cemu crash was reported. A normal userspace exit alone would not establish an explanation for a whole-device unclean reboot. |

**No root cause is proven.** There is one reported uncontrolled Mini reset, not
proof of a repeated same-rung failure. Later non-enumeration is a separate open
event. The supervisor authorized a retry/diagnosis, but USB was lost before it
could run. No device build, reboot command, firmware write, system activation,
unit reset or recovery-journal edit was issued by this worker.

## State left for morning recovery — not a restoration claim

| State | Last known state / required action |
|---|---|
| Launch settings | Clock minima were reverted after their rung; performance governor was reverted before resolution tests. Best rung used original CPU/GPU 0–100 and schedutil. Re-query after USB returns; unset any remaining Game cpu.min/gpu.min or Device cpu.governor through revision-checked RPC only. No game override is needed by the passing rung. |
| Library | Temporary BotW-only Gamescope modifier was re-added for the soak request. Final removal is unverified. Restore **only BotW's original item bytes**, from library-before.yaml, under the saved whole-file hash guard; preserve unrelated items. |
| Cemu account | Last selected 31:27 / 620×540 / FPS++ 30 / Square HUD / fill scaling / May settings / async off. Keep that best short-run configuration, not shipped 16:9 defaults. Exact tested native snapshot: `resolution-620x540/native.xml`. No taskset, TU_DEBUG or CPU-profile experiment was reached. |
| P1 profile | Completed rungs restored P1. Soak may have installed P2 before the reset; current bytes/metadata are unknown. Restore only if active bytes match known P1/P2; use owner-controller.xml's P1 bytes, timestamps and ACLs, retaining UID/GID 1000:1000. |
| Speaker | Last checked `Volume: 0.00 [MUTED]`; current post-loss state unknown. Resolve the Speaker node again; node ID 50 is not assumed across boot. Mute without changing volume. |
| Processes / bench pad | Completed-rung cleanup succeeded. Reboot would terminate old processes/pad, and the supervisor saw idle at 07:11, but no final independent audit was possible. Require idle RPC, no game units/cgroup members/Cemu/wrapper/pad, original CompositeDevice0 and false ManageAllDevices. Do not kill an unowned session. |
| Save — **last step** | Select **owner source `5f3c80b8…`**, ended 06:26:26, duration509, using only app.saves.restore. Staging/bench progress must not be the final selection. Owner source remains in history; final selection was **not performed**. |

### Exact morning commands (zao → USB only)

Run before anyone plays again. If the owner has since played another session,
identify that newer **owner** snapshot first; do not mistake a bench record for
owner progress. Do not run this if the private helper is missing or its hash
has changed. The helper remains private, not shipped in this repository.

```sh
# Refuse LAN fallback. Interface names may have changed; require a direct USB subnet.
python3 - <<'PY'
import subprocess
r = subprocess.check_output(['ip', 'route', 'get', '<device-usb-ip>'], text=True).splitlines()[0].split()
assert r[0] == '<device-usb-ip>' and 'via' not in r and r[r.index('src') + 1].startswith('<device-usb-ip>'), r
PY
printf '%s  %s\n' \
  6ec914287aba7a0ea3404388c0c839341a9367ecd9122ff09d097779817bafdf \
  /tmp/cemu-mini-evidence/morning-restore.py | sha256sum -c -
scp -P 2222 -o BatchMode=yes /tmp/cemu-mini-evidence/morning-restore.py \
  root@<device-usb-ip>:/var/lib/korri/cemu-bench-staging/mini-ladder-20261023/
# Collect old device journal/kernel, current kernel/power and pstore before changing config.
ssh -p 2222 -o BatchMode=yes root@<device-usb-ip> \
  '/nix/store/zc0vzc0vp0amc9iqm3cd542bmim6vh09-python3-3.13.9/bin/python3 /var/lib/korri/cemu-bench-staging/mini-ladder-20261023/morning-restore.py collect'
# Review collection. Then restore configuration/profile and select the owner save LAST.
ssh -p 2222 -o BatchMode=yes root@<device-usb-ip> \
  '/nix/store/zc0vzc0vp0amc9iqm3cd542bmim6vh09-python3-3.13.9/bin/python3 /var/lib/korri/cemu-bench-staging/mini-ladder-20261023/morning-restore.py restore'
rsync -a -e 'ssh -p 2222 -o BatchMode=yes' \
  root@<device-usb-ip>:/var/lib/korri/cemu-bench-staging/mini-ladder-20261023/ \
  /tmp/cemu-mini-evidence/device-after-recovery/
```

The private helper refuses a changed system/bundle, active game or recovery
block, unexpected library/native/controller edits, or missing owner source.
It uses Game scope for CPU/GPU minima and Device scope for governor. It never
resets units, edits korrid records, restarts services, launches a game or writes
firmware. It records configuration proof before the **last** game-state mutation,
app.saves.restore of the owner's exact source, then checks the selected save
payload. Results go to `mini-ladder-20261023/morning-recovery/`.

Only syntax and offline block-boundary/duplicate-refusal tests ran for this
recovery helper. **Device restoration remains untested and unexecuted.** A hash
or identity refusal needs review, not removal of the guard. After recovery,
inspect the old Mini kernel/journal/pstore and supply state before another long
run. A fresh 15-minute qualification is still required; if the same rung resets
again, mark it failed, revert it and move on as instructed.

## Checks and retained evidence

Final focused ARM and x86 package/admission checks passed, including strict
TypeScript/callback tests, installed-wrapper ShellCheck, Turnip selection, new
aspect/default checks, real Cemu CLI/Xvfb/offline-pack startup and native-edit
preservation, and actual Core admission/execution. The new seed/aspect assertions
first failed against their previous packages, then passed. An initial red Nix
help probe timed out at 15 seconds; direct real help and subsequent full focused
checks passed. No full repository suite or full verification ran.

Final ARM check outputs: `i2ss08h7…-korri-cemu-package-check` and
`wm9hyl52…-korri-cemu-admission`; x86: `4f4qyjik…-korri-cemu-package-check` and
`75d467gi…-korri-cemu-admission`. Both architecture builds used explicit builders
(yari for ARM; empty builders/local max-jobs1 for x86), never a target build.

Also passed: 12 bench unit tests, mypy/Ruff/format on its 9 Python files;
mypy/Ruff/format on both touched Python checks; Nixfmt on the two touched Nix
files; Python compilation; git diff --check; commit-hook secret scans.
The outside-sandbox real Cemu `--setgid-account` check was rerun successfully on
zao after the outage, managed with keepAfterChild=true. Formatter changes leave
the actual ARM Cemu output unchanged. Native-baseline raw reproduction passed
all 180 FPS bins; later raw files await USB retrieval, while their exact returned
metrics remain in the host campaign log.

Private zao evidence: `/tmp/cemu-mini-evidence/` (0700). Important files:
`campaign-resume.log`, `resume-owner-state.json`, `native-baseline-edge-stats.json`,
`host-kernel-reset-window.txt`, `host-boots-utc.txt`, `reset-preflight.txt`,
`final-{arm-checks,x86-checks,setgid-runtime}*`, and `morning-restore.py`.
Device evidence: `/var/lib/korri/cemu-bench-staging/mini-ladder-20261023/`.
Screenshots, saves, helper code and private histories are not committed.

| Acceptance | Result |
|---|---|
| Median ≥30; p10 ≥27 at native aspect | **Passed short rung:** 30 / 30, 620×540, 180 s |
| 15-minute soak holds target, no crash, peak recorded | **Not run (device lost)**; short-rung peak85.7°C is not soak proof |
| Measured ladder table complete | **Recorded through first passing rung**, later rungs intentionally stopped per revised instruction |
| Shipped behavior uses Cemu-native files/existing launch settings only | **Passed**; no new Korri schema or unmeasured debug/affinity default |
| Launch settings restored to device defaults | **Last completed rung used defaults; final post-reset restoration unverified** |
| Original item, P1, mute and owner's latest save restored | **Pending hardware access**, guarded commands above |
| Native output / HUD and menus | Baseline numeric no-bar proof passed; visual HUD/menu correctness **not established** |

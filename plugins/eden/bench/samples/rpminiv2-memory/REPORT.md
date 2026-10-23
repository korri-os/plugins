# Mini memory-first SMO attempt — 2026-10-23 UTC

**The 30 FPS target is not met. The recovery window expired at 18:56:29.
The current native INI restoration is unverified. Only the user may perform
a physical power-button reset; no remote reboot was attempted.**

No accepted gameplay window or 900-second soak exists.

This extends [the earlier diagnosis](../rpminiv2-staging/DIAGNOSIS.md). The signed
plugin, normal library admission, native save seed and Vulkan first light worked.
Those are not gameplay/performance acceptance. No Mini-specific shipping default
has been added.

## Current recovery status

The last launch is `1fdb894c480392ffb90c1d63df2cea0a`, renderer host PID 42708,
requested NCE with native 0.5× rendering. Its managed host supervisor was later
found terminated by SIGTERM after the conversation fetch failure. The exact
termination time and the on-device controller's final state are unknown.

At 18:11:29 a new SSH observation failed during banner exchange. A 120-second
connection attempt also failed. The parent independently observed a live kernel
(ping about 2 ms), TCP 2222 and 39217 accepting connections, but no SSH banner.
**Memory thrashing is inferred, not a separately confirmed OOM for this launch.**
The baseline runs below establish severe memory pressure and one kernel OOM.

The quiet recovery attempts offered only an exact-owned-unit stop and native
INI restoration. None passed banner exchange, so none executed that script.
The recovery worker has ended; no further device actions are queued. There is no reboot, poweroff, firmware operation, global kill,
product-service stop for RAM, swap/zram change, or new authentication route.
The kiosk capability was read only on the Mini. It was never copied/logged on the
host, so a direct-RPC stop is unavailable while SSH cannot read that credential.
No unauthenticated request is substituted.

The five quiet recovery attempts used one SSH connection, no multiplexing, a
60-second connect limit and at least five quiet minutes after a failed attempt.
All five failed; the last ended at 18:52:02. The worker stopped at the 45-minute
deadline, 18:56:29, measured from the first verified failed observation.
Until a successful restoration proof is retrieved, **the 0.5×/Seat P2 native INI
must be treated as unrestored. Do not launch Eden again before restoring it.**
See [the final attempt record](ARCHIVE.sha256) and
[the explicit incomplete outcome](final-outcome.json). A successful exit from
the recovery worker means its waiting loop ended, **not** that cleanup succeeded.

## Memory ladder and outcome

All trials keep Eden's native `memory_layout_mode=0` (4 GB), the Switch minimum.
No CPU/GPU minimum, governor, affinity, mod, driver environment or system memory
policy was changed. Handheld mode and the temporary guest P1→bench Seat P2 mapping
were common test preparation, not shipping defaults.

| Step | Native setting / evidence | FPS median / p10 / p1 | Memory / thermal evidence | Decision / restoration |
|---|---|---|---|---|
| Baseline, NCE requested | `r1-nce-diagnosed`, `06ce618a9471d5c33e468ac9236797de` | unavailable / unavailable / unavailable; 0 accepted bins | Whole-run peak summed session RSS 5,215,624 KiB; minimum MemAvailable 36,248 KiB; peak 64.0 °C; global full memory PSI avg10 peak 30.63%; separate shmem not yet sampled | Failed warmup; exact cgroup empty; INI restored to baseline hash; native Core recovery required |
| Baseline, Dynarmic requested | `r1-dynarmic`, `d72ddb318165f9c21b773299b7574332` | unavailable / unavailable / unavailable | Kernel OOM at 17:23:34; victim anon RSS 870,232 KiB and shmem RSS 3,983,652 KiB; these are a victim sample, not a measured session peak | OOM; own cgroup empty; INI restored; native recovery proof below |
| Memory 1 | `vram_usage_mode=0`, Conservative | No new run / no claimed gain | Already the native default and most conservative enum; Aggressive is the only other value | Keep default; no fabricated tuning rung |
| Memory 2 | Automatic native ASTC | No new run / no claimed gain | Live Turnip A650 reports ASTC LDR and all 28 formats pass Eden's exact native-support predicate | Already native-capable; no native-force INI key exists |
| Memory 3 | `resolution_setup=1`, 0.5×; NCE requested | Not retrieved / not accepted | Launch succeeded; subsequent userspace access failed; telemetry, shmem peak, temperature and image not retrieved | Supervision interrupted; restoration currently unverified |
| Memory 4 | Disk shader cache / async shader build | Not reached | Disk shader cache is already true; asynchronous shader build defaults false | No mutation or claimed gain |
| Remaining original ladder | clocks, display choices, sourced mods, accuracy/cache, legacy artifact, cores 4–7, TU_DEBUG, patches | Not reached | Memory gate did not complete | No changes made |

No row has an accepted matched Bonneton screenshot. The earlier image is the
native Start screen, not verified gameplay. The 1,095 non-Skip Present events in
the diagnosed NCE CSV are not a valid FPS window: no completions were present near
the end of warmup. Do not divide that event count by its early span and call it a
baseline. The original collector reports backend execution as unproven.

`nce-summary.json` aggregates all 132 supplemental samples. The collector's own
report covers a narrower interval and therefore has lower RSS/thermal maxima.
RSS sums can count shared pages more than once. NCE summed-session RSS and the
Dynarmic victim's process RSS are not an apples-to-apples backend comparison.
Zero sampled cgroup OOM counters in NCE do not disprove global memory pressure.

## Grounding the native memory keys

The exact Eden 0.2.1 source used by the staged binary is
`/nix/store/inmrhbhn9k0lnrcw8v4hi9rc2nwp9k95-source`.

- `src/common/settings_enums.h:130–145` defines ASTC decoding/recompression,
  Conservative/Aggressive VRAM, 4 GB memory layout, and resolution enum 1 = 0.5×.
- `src/common/settings.h:441–495` defines `vram_usage_mode=Conservative`,
  `accelerate_astc=Gpu`, and `astc_recompression=Uncompressed` defaults.
- `src/video_core/vulkan_common/vulkan_device.cpp:785–820` computes native ASTC
  support from `textureCompressionASTC_LDR` and the 28 ASTC optimal-format checks.
- `src/video_core/renderer_vulkan/maxwell_to_vk.cpp:237–258` transcodes/recompresses
  ASTC only when `!device.IsOptimalAstcSupported()`.
- `src/video_core/renderer_vulkan/vk_texture_cache.cpp:1595–1627` follows the same
  native-support condition for conversion.

A prebuilt `vulkaninfo` probe, run as the existing runtime user against the live
Mesa 26.2.3 Turnip Adreno 650, passed that exact predicate for all 28 formats.
The device-side `vulkan-capabilities.json` and `astc-native-proof.json` retain it.
`accelerate_astc` values 0/1/2 select Cpu/Gpu/CpuAsynchronous fallback decoding.
`astc_recompression` 0/1/2 selects Uncompressed/Bc1/Bc3 when native ASTC is absent.
Neither is a force-native switch. This does not claim that every SMO texture is
ASTC; it establishes how native ASTC would be handled without inventing a key.

The observed original native INI had Conservative 0, resolution 3 (1×), GPU ASTC
decode 1, recompression 0, disk shader cache true, async shaders false and 4 GB
layout 0, all with their native default flags true. The only new memory setting
actually changed was resolution 1, with its native default flag false.

## Dynarmic OOM and native Core recovery

Verified kernel journal observation at 17:23:34: launch `d72ddb31…`, renderer
34044, was globally OOM-killed; anon RSS 870,232 KiB, shmem RSS 3,983,652 KiB.
The full kernel excerpt and idle service-memory inventory remain on the Mini;
they were not retrieved before SSH stopped responding in the next trial.
The idle inventory is at
`/var/lib/korri/eden-bench-staging/mini-20261023/idle-memory-after-dynarmic.json`.
Its largest Chromium RSS samples were 135,668 / 117,084 / 48,124 / 38,484 /
32,056 / 24,512 KiB; korrid 42,232 KiB, sway 27,344 KiB, Xwayland 25,324 KiB.
These are individual RSS values, not unique physical memory or promised savings.
No service was stopped to reduce them.

The [Core journal](ARCHIVE.sha256) records a portal-freezer systemctl
timeout at 17:19:04, then input coordination fenced at 17:23:33, immediately before
the kill. Thus the observed post-OOM blockage is proven, but OOM alone is not
proven to cause fencing.

Suggested Core finding for the parent to file: **“an OOM-killed game leaves korrid
HostRecoveryBlocked until korrid restarts.”** Include the preceding freezer
timeout, exact launch and journal chronology, not just the OOM headline.

The parent approved only native recovery, with all old records unchanged and
only this launch's native completion/snapshot/play entry allowed. The actual
restart began after an empty 1,263-second observation window and stable korrid
PID 33493; the retained active record and its hash were preserved first. No
session record was edited, deleted or manually cleared.

At 17:49:48 the replacement korrid PID was 42167. Its native recovery completed:

- RPC idle passed; the retained active record became absent through Core.
- Device/catalog YAML was semantically identical before/after.
- All 177 old immutable snapshot records were semantically unchanged.
- Only this launch's interrupted snapshot and matching play entry were added.
- New snapshot `sha256:479144091c8d6de337e7ec65cf17969bfd42e849de0a46a59effe1c1a6915468`
  has exactly the same save locations/file hashes as its pre-OOM base
  `sha256:1c75fe9996b79516be26c5193e7623c7f86d7c243b10d90bbe7ae81604918b8f`.
  No save-choose RPC was needed.
- Native completion duration is 2,036 seconds, ending at recovery time, not the
  kernel kill time. This is Core's history output, not benchmark runtime or soak.
- Before the next launch, PID 42167 had been stable for 452 seconds and the empty
  process observation window was 1,824 seconds; the immediate gate passed again.

See [the recovery proof](dynarmic-recovery-proof.json). Its pending-reservation
check uses the shared local-portal caller: current Core `with_pending_launches`
projects any owned pending reservations into `Ok`, even when native status is
blocked. The bare `HostRecoveryBlocked` reply contained no such projection.
The parent-authorized native additive writes are grounded in Core
`host/session_state.rs:816–935` (`store.put_record` and `play_log.record`).

## Checks and limits

- Three real-process operational regression tests passed: reproduce old pgrep
  self-match, retain a workflow-shaped Python contender without retaining argv,
  and exclude the exact owned cgroup before argv inspection.
- Ruff check passed for helper/tests/generated controller; Ruff format check
  passed for helper/tests. Mypy passed for both helper/test source files. One
  combined Nix-shell/check attempt hit its 90-second host timeout; the standalone
  focused mypy retry passed. No target compilation occurred.
- `nce-summary.json` is derived from the retained 132-row raw telemetry.
- YAML semantic comparison, every old snapshot comparison, old play-entry
  preservation, exact one native addition and save-content comparison all passed.
- Prior x86/ARM plugin/bench package and admission checks passed; see the earlier
  preparation/staging evidence. No product Python/TypeScript/Rust was changed by
  this memory evidence slice. No full suite was rerun.

The `operational/*.py.txt` files are inert administrative source captures, not
installed bench code. To rerun the three focused tests, copy the helper/tests to
an isolated directory without the `.txt` suffix and run `python3 -m unittest -v
test_contenders.py`. The controller template requires host injection of the
existing canonical Bonneton tape; it is not a standalone production program.
The generated trial used that same tape (SHA256
`ddb89a3782bfdee6b8fd3ae808861993ab337fbeb70c8878f915caf87d496135`).

The observer now avoids remote argv reads for the owned game and non-candidate
browser processes. This reduces avoidable probe work; it does **not** prove the
original long stalls' cause or provide a reliable guard under global reclaim.
A Python timeout/host SSH connection is not a sufficient cleanup guarantee here.

## User decisions / remaining risk

The available 5,559 MiB (about 5.4 GiB) physical budget did not yield a working SMO
configuration in these tests. Guest shmem alone reached about 3.8 GiB, before
anonymous renderer memory, graphics allocations, portal and kernel. Native
conservative VRAM and native-capable ASTC were already in use; 0.5× did not produce
an accepted result before control access failed. This is not proof that every
possible future emulator patch is impossible.

| Decision | Cost / limit |
|---|---|
| Keep the current no-swap Mini system | No demonstrated SMO gameplay/30 FPS; do not ship a Mini performance default from these results. |
| Authorize system-level memory work, such as zram | Changes the system; compression consumes CPU/power and may hurt frame pacing. Capacity, ratio and gains are unmeasured. No change was made. |
| Reduce normal portal/other service footprint without removing product capability | Requires measured unique-memory work and regression testing. RSS is not reclaimable/PSS; no claimed savings and no services were disabled. |
| Revisit emulator memory/cache behavior or a different artifact | New build and full on-device acceptance needed; no measured gain yet, no new Korri schema/default/profile should be invented. |

The quiet recovery deadline failed. The Mini needs a user-only physical
power-button reset if it remains unresponsive; no other reboot route is approved. After SSH returns, first confirm this exact cgroup is empty,
then restore the protected native INI and check both hashes against
`a2459bd8025e0d50e92f36cae7a38b904639212a98b8a7c6f042f19c20bbcba8`.
An inert [exact-owned stop and hash-checked restore script](ARCHIVE.sha256) is
provided for that recovery, not as proof it has already run. From this folder,
after the user restores access, the command is:

```sh
ssh -o BatchMode=yes -o ConnectTimeout=60 -p 2222 root@10.42.3.1 bash -s < RESTORE.sh.txt
```

Collect the last run's telemetry, kernel/oomd journal and PSI evidence before
another test. Do not delete Core's retained active record; use its native
recovery path with the idle/PID/history/save-content checks above.

Audio was never unmuted or raised. During the diagnosed NCE attempt two active
Eden→speaker links were observed with the sink still `Volume: 0.00 [MUTED]`:
**not verifiable at night, stream verified** for that observation only.
No audible acceptance or current post-failure stream claim is made.
Keys, firmware and game bytes are not in this evidence or the package. No push,
merge, publication, system update, firmware write or device compilation occurred.

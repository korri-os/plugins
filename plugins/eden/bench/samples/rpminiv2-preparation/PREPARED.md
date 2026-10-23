# Mini V2 preparation — 2026-10-23 UTC

**Host preparation only. No Mini installation, staging, launch or FPS result.**
The authorized USB route `root@10.42.3.1:2222` timed out at 11:14 UTC.
A read-only `ssh -o BatchMode=yes -o ConnectTimeout=8 -p 2222
root@10.42.3.1 true` poll runs every ten minutes, bounded at 17:12 UTC
(six hours after the supplied 11:12 observation). No network configuration,
identity, trust, service, volume, firmware or partition was changed.

## Exact prepared artifacts

| Artifact | Host store path |
|---|---|
| Existing personal plugin | `/nix/store/24yf1xbs5213vqx2if3qlqsz1cz6qqfz-korri-plugin` |
| Launcher | `/nix/store/77ndp24virwb0khxal8id2r46pi9w915-eden-korri-0.2.1` |
| Unchanged Eden 0.2.1 | `/nix/store/010847afgzfll903n5dbzqdajmm1m0n7-eden-0.2.1` |
| Bench 0.2.2 | `/nix/store/zd7jxck7icv2hizxr6zlx65ci4n89qnz-korri-eden-bench-0.2.2` |

Direct byte comparison against starting commit `0449484` proves the existing
personal plugin changes exactly one runner literal from `@korri:eden/eden` to
`@<publisher>:eden/eden`. The installed-output candidate's `vulkan_device.py`,
`p1_controls.py` and `p1-controls.ini` match this worktree exactly. No new test
package, alternate wrapper, plugin setting or native default was introduced.
The personal output already has its personal-publisher signature. The union
of the personal-plugin and bench runtime closures has **489 store paths**;
every path was checked for the existing `korri-cache-<build-host>-1` signature after
local recursive signing. This is host preparation, not Mini trust or admission
proof. Re-read Mini's actual publisher bindings before any delivery/install.

The README's old explicit `<retired-builder>` override failed to resolve. The
corrected documented command uses the daemon's configured builders. Its ARM
bench build succeeded through `ssh-ng://<user>@<builder-1>`; no handheld built anything.

## Input availability, not device staging

Read-only SSH to `<user>@<content-host>` verified the supplied SMO source is
**5,611,009,601 bytes**. The supplied firmware source has **214 descendant
directories**, **167 regular files**, and **246,074,368 regular-file bytes**.
Counting the root itself gives 215 directories. No game or firmware was copied
or opened for this preparation.

Host keys remain only at the supplied paths:

| Path | Bytes | Mode |
|---|---:|---:|
| `/home/<user>/.local/state/korri-eden-test-keys/prod.keys` | 14,612 | 600 |
| `/home/<user>/.local/state/korri-eden-test-keys/title.keys` | 1,292 | 600 |

No key contents or key digests were read into reports. The user's save manifest
selects `eden-nand-b520`: complete two-file set, newest progress timestamp
2025-12-25 20:38:32Z. Its SMO directory contains only `Common.bin` (1,036 bytes)
and `File1.bin` (2,097,164 bytes), matching the Odin-stage payload. No Mini
account, saveRoot or profile UUID is assumed from the Odin's values.

## Reuse the Odin path, with these gates

1. Require empty `pgrep -a -f 'cemu|eden|bench'` observations for 15 minutes and
   korrid's PID stable for two minutes before **each** install, launch or
   settings change. Use an SSH stdin script so the probe cannot match itself.
   Record journal evidence for intervening short sessions. Recheck immediately
   before acting. The bench's lock is not an exclusive lease. If Cemu appears,
   exact-stop only this worker's session and yield.
2. Read Mini's signed owner statement at the existing
   `/var/lib/korrid/identity/owner.event.json`; verify its event hash and BIP340
   signature as on Odin. Read publisher bindings and signature policy. Derive
   accountRoot from Core's existing account producer and the verified owner;
   never reuse Odin's public identity or create/re-key an identity.
3. Follow [Odin staging](../../device-facts/odin2portal-content.md): account-local
   native Eden keys (600), firmware NAND and existing Switch library location.
   Grant only the runtime/service access proven necessary on Odin. Copy only
   with the authorized read-only source; do not bundle proprietary inputs.
4. Deliver signed closures with `nix copy`. Populate the existing personal
   cache without replacing records. Use `korri-plugin inspect`, exact approval
   `install`, then `enable`; keep signature and permission checks enabled.
5. Reuse [offline pairing/rescan and semantic proof](../odin2portal-firstlight/report.md),
   with protected snapshots. Permit only additive Switch/SMO records and
   serialization-order changes that preserve parsed existing values. Account
   explicitly for socket activation: Odin's active control socket restarted
   korrid during its offline rescan and left `DiscoveryConflict`. Do not call
   that a clean offline interval or silently clear state.
6. Obtain the admitted game's real saveRoot. Discover the native profile from
   Eden's own `profiles.dat`, current-user setting and fresh game log. The
   folder is the native uppercase high-u64/low-u64 representation, not raw
   UUID byte spelling. Reuse [normal session-end capture](../odin2portal-graphics/SAVE-PROOF.md)
   if Core has already materialized a snapshot; an offline rename alone is not
   a save-history import. Verify Resume and the user's progress before FPS.
7. Snapshot the actual native INI, per-title files, mod directory and original
   launch settings before temporary changes. Hash restoration. Normal wrapper
   path binding, valid Turnip selection and permanent native P1 setup are not
   performance overrides. For scripted input only, discover Seat P2 and map
   guest P1 temporarily as on Odin; restore the exact native file afterward.
8. Use the [frozen tape/reference](../odin2portal-acceptance/REFERENCE.md): A at
   45 s, right-stick -X for 1.5 s at 60 s. Inspect a fresh screenshot for each
   rung. If Mini cannot reach the Odin view with that tape, label the actual
   view; never call a title-screen or unmatched scene an accepted benchmark.
9. Run 100 s post-replay warmup, then 180 one-second game-window Present bins.
   Keep only a measured gain; change one factor at a time. Run a 900-second
   soak of the best candidate; require median ≥30 and p10 ≥27. Retain raw FPS,
   all thermal sensors, peak session RSS, screenshots, renderer/backend evidence
   and exact-cgroup cleanup. RSS sums may double-count shared mappings. Do not
   claim backend instruction execution from the collector's inference.
10. Observe PipeWire links silently and preserve sink volume/mute. Audible
    acceptance remains “not verifiable at night, stream verified” only after
    the stream is actually verified. Restore temporary configuration and launch
    settings with exact/native and resolved-setting proofs. No swap or zram.

`bubblewrap: absent — core gap #184` is the existing Core gap to record on a
real launch, not a claim of new Mini observation or a reason to add a wrapper.

## Native ladder grounding

The following names/values were read from pinned Eden v0.2.1 source
`/nix/store/inmrhbhn9k0lnrcw8v4hi9rc2nwp9k95-source`, not invented Korri fields.
Global renderer categories are read inside `[Renderer]` by
`src/frontend_common/config.cpp:366–375`. Native default and per-title global
flags must be respected. A temporary explicit value needs its native
`\\default=false`; check the fresh effective game log, not merely stored text.

| Rung | Existing native/host setting | Grounding and cost |
|---|---|---|
| 1: handheld NCE / Dynarmic | `[System] use_docked_mode=0`; `[Cpu] cpu_backend=1/0` | `settings_enums.h:138,149`; `settings.h:674–685`. **Linux defaults to docked**, unlike Android. Handheld is an explicit temporary baseline, not the current plugin's shipped default. |
| 2: clocks, one write at a time | `cpu.min`, `gpu.min`, then `cpu.governor` | Existing `LaunchSetting` enum in Core `contracts/generated/korrid.ts:617–631`; use current-revision RPC writes. Game CPU minimum is uclamp, not a direct frequency pin (ADR 0019). Governor support must be checked on Mini. |
| 3: below 1x | `[Renderer] resolution_setup=2/1/0` = 0.75x/0.5x/0.25x | `settings_enums.h:145`; `settings.h:343–344`. Native 1x is enum 3. Fewer pixels cost image quality; compare screenshots. |
| 3: Gamescope upscaling | Existing modifier `nested-width`, `nested-height`, `output-width`, `output-height`, `filter`, `scaler` | `plugins/gamescope/compose.ts:50–57,211–221`, ADRs 0007/0009. No modifier RPC exists in this Core; retain the Odin revision-checked, game-only edit/proof approach if needed. Do not invent an RPC. |
| 4: game patches | Account-native `load/0100000000010000/<mod>/exefs/` | `patch_manager.cpp:365–451` matches NSO build ID and logs applying IPS/IPSwitch patches. Require actual matching/application evidence, source and licence; see [source audit](MOD-SOURCES.md). |
| 5: accuracy | `[Renderer] gpu_accuracy=0` = Low; Linux default 1 = Medium | `settings_enums.h:136`; `settings.h:419–429`. Reduced correctness is a measured trade-off, not an unconditional default. |
| 5: async shader build | `[Renderer] use_asynchronous_shaders=true` | `settings.h:570–571`, native default false. Missing/transient shaders can be visible. |
| 5: ASTC | `[Renderer] accelerate_astc=0/1/2` = CPU/GPU/CPU asynchronous | `settings_enums.h:130`; `settings.h:457–463`. Native default GPU. Compare memory, shader/texture artifacts and FPS. |
| 5: cache | `[Renderer] use_disk_shader_cache=true`, `use_vulkan_driver_pipeline_cache=true` | `settings.h:489–495`; **both already default true**. Record cache warmness; do not mislabel an already-enabled cache as a new optimization. |
| 5: memory | `[Core] memory_layout_mode=0` = 4 GiB | `settings_enums.h:141`; `settings.h:200–206`. **4 GiB is already the smallest native option and default**. Larger layouts cost scarce RAM; they are not a reduction for this 5,559 MiB/no-swap device. |
| 5: old-GPU build | Same version with `YUZU_LEGACY=ON` | Upstream `CMakeLists.txt` explicitly says older GPUs, e.g. Snapdragon 865, at the cost of performance. Build only on the builder after artifact evidence. No build was started speculatively. |
| 6–8 | Owned-renderer-only test `taskset` cores 4–7; artifact-motivated `TU_DEBUG`; emulator/game patches last | No shipping affinity or per-device profile contract. Any gain requiring one is a user decision. Flags and new patches need their own measured/source/licence evidence. |

The supplied research brief's low-end FPS estimates were **not validated** by
its audit. Its “mandatory zram” recommendation conflicts with this task and is
not followed. The April Ryujinx note establishes a 960×540 **docked** patch
candidate, not a handheld patch or a Mini Eden result. Do not combine a docked
mode change with a render patch and call it a one-factor handheld measurement.

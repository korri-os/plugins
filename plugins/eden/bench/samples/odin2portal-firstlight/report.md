# Odin first light — stopped at the graphics gate

2026-10-23 UTC. **No accepted SMO performance result.** No game picture or game-window Present completion was observed. The collector lost the exact renderer identity during warmup and stopped only its own session. The native log selected **llvmpipe 26.2.3**, not Turnip. The workflow's explicit no-picture rule ended launches here; no plugin graphics workaround or Dynarmic retry was attempted.

This does **not** prove an emulator crash. The journal records successful unit deactivation after the collector's exact stop. The reason the renderer identity disappeared remains unknown. The screenshot taken after cleanup showed the Korri library, not SMO.

## Install and source authority

| Item | Verified evidence |
|---|---|
| Source commit | `fc795cdfc782bac0c649fec92f765ac7edc1d416`; shipped Eden source unchanged |
| Official package, not installed | `/nix/store/4g5c49fdz70pkskazgr3b1gpwrqdj55f-korri-plugin` |
| Personal test package, installed | `/nix/store/gqx6l7143bfxvgv9n433jym2l6pinfc1-korri-plugin` |
| Same native launcher | `/nix/store/y1vrxl47w3arr32py7vkga91p69376ys-eden-korri-0.2.1` |
| Native Eden | `/nix/store/010847afgzfll903n5dbzqdajmm1m0n7-eden-0.2.1` |
| Normal admission | [Inspection](inspection.json), [installation](install.json), enable exit 0, [Enabled status](status.json) |
| Cache binding | Existing personal cache `file:///var/lib/korri-private-cache/cache`; no binding/trust changes |

The official publisher key exists only in CI. Supervisor approval allowed the existing personal publisher route. Test-only build composition replaced exactly one literal, `@korri:eden/eden` → `@<publisher>:eden/eden`; [the diff](ARCHIVE.sha256) is the entire source delta. A byte comparison proved no other change against committed source. No second permanent package output was added.

The personal package was signed with the existing personal publisher key. Its closure was also signed with <build-host>'s existing `korri-cache-<build-host>-1` key and delivered with signature-checked `nix copy`. The two custom package cache records were added without replacing existing cache records. Native dependencies remained unchanged. The four tiny test-package metadata/source derivations ran on the daemon's <builder-2> builder; Eden itself was reused unchanged, not compiled. No device compiled anything. No push, merge, publication, trust expansion or system/firmware update occurred. Mini was not contacted.

## Shared-device and discovery operations

Read-only five-minute checks covered Cemu's work. After its last observed activity, checks at 02:54, 02:59, 03:04 and 03:09 found no emulator/bench. Journal checks detected intervening short Cemu launches earlier and reset the idle window. Work began at 03:10 with no pending/active session and korrid PID 14635 stable since 01:23. Every later install, settings change and launch rechecked processes and the stable daemon PID. No Cemu process appeared during this stage.

The supervisor explicitly authorized two otherwise-forbidden offline daemon operations, each with configuration/discovery copies and SHA256 snapshots:

1. `korrid catalog pair /var/lib/korri/games/switch switch`, as service user `korrid`, 03:14:50–03:14:54. It added only the Switch source/storage and ownership entry. It could not read the staged folder.
2. After the narrow content ACL correction, `korrid catalog rescan`, again as `korrid`, bracketed by 03:18:15–03:18:42. It hashed 5,611,009,601 bytes, added exactly one game, removed zero locations and reported zero scan diagnostics. Actual catalogue identity: `super-mario-odyssey-0100000000010000-v0`; route: `@<publisher>:eden/eden`.

**Operational caveat:** the triggering control socket remained active. Read-only journal review confirmed korrid started again at 03:18:19, before the rescan command finished. Discovery later retained `DiscoveryConflict`. The final library and route were usable, but this was not a clean daemon-off scan interval. No further restart, state clearing or socket change was made. Preserve this fact for the next operator; do not call discovery fully healthy. Final PID 45696 stayed stable, and `system.health` answered `korrid-v0`.

Core's serializer moved Cemu's unchanged empty `cpu`/`gpu` keys ahead of its other keys. The supervisor replaced the literal byte-equality requirement with semantic equality for this single serializer-order change. `discovery/reconcile/documents.rs:63–73` serializes the typed library; `config/library.rs:18–31` declares CPU/GPU first; `discovery/reconcile.rs:793–795` writes it with serde_yaml. [The proof](ARCHIVE.sha256) checks every pre-existing record and the exact allowed additions. It also rejected three counterexamples. No timestamp exception was needed. [The proof script](ARCHIVE.sha256) takes the protected before/after snapshots, which remain on the device, not in Git.

### Staging access corrections

The library folder and NSP were root-owned, with access for runtime `korri` but none for service `korrid`. A service-user read probe failed. Added only `u:korrid:r-x` on the Switch folder and `u:korrid:r--` on SMO. Both users then passed the read probe. See [before](ARCHIVE.sha256) and [after](ARCHIVE.sha256).

The staged save had the same service-access omission. Its inherited ACL mask was `---`. The first launch therefore failed **before any game process** with `SavesUnavailable`. Added `u:korrid:rwx`, an `rwx` mask and a default `u:korrid:rwx` on this save's directories; added `u:korrid:rw-` with an `rw-` mask on its files. No execute permission was granted on the save files. See [before](ARCHIVE.sha256) and [after](ARCHIVE.sha256). These are operational staging corrections, not plugin permission bypasses or changes to another game's data.

## Settings and restore proof

| Setting | Before | Test | After |
|---|---|---|---|
| SMO game `cpu.min` | Absent; device default 0 | 100, existing `app.launch-settings.set` RPC | Removed through the same RPC; default 0 |
| SMO game `gpu.min` | Absent; device default 0 | 100, existing RPC | Removed through the same RPC; default 0 |
| SMO Gamescope modifier | Empty game modifier map | `@korri:gamescope/gamescope.enabled: true` | Exact pre-edit bytes restored |
| CPU/GPU max, governor | 100 / 100, schedutil | Unchanged | Unchanged |

CPU/GPU requests used the current game-document revision each time. Exact requests/responses are `cpu.min-set.json`, `gpu.min-set.json`, `cpu.min-restore.json`, `gpu.min-restore.json`.

No RPC writes modifier records. With explicit supervisor approval, one atomic revision-checked catalogue edit used ADR 0009's existing shape. A parsed comparison proved it changed only SMO's modifier. [Actual launch proof](launch-proof.json) confirms korrid resolved Gamescope and supplied the real saveRoot; no restart was needed to apply that edit.

Before restoration, the current hash still matched the edited hash `91b3d56173593bf361c99ac891b2510de2b0a8f4915b589ed2d46f2c9c606ec9`. Restoring the protected backup produced exactly `62261283f83da5e31e7a541f251eb9d87ac52b43d7e71be2e2522986c0c130c5`, matching both backup and destination. Then the modifier backup was deleted. See [restore hashes](modifier-restored.sha256). This restoration preceded the CPU/GPU RPC removals.

[Restored settings](settings-restored.json) have **all layers and all resolved values equal** to [before](settings-before.json). CPU/GPU minima both report `deviceDefault: true`; max remains 100; governor remains schedutil. Native GPU limits were back to **220000000 / 680000000 Hz**. No soak ran; restoration occurred immediately after the graphics stop.

## Launch and graphics evidence

| Attempt | Launch ID | Result |
|---|---|---|
| [Initial gate](firstlight-nce-gate/report.md) | `9558a987340dd810bd438f446b75b15d` | `SavesUnavailable`; no game process; staging ACL corrected |
| [Actual Eden run](firstlight-nce-retry/report.md) | `1cb224bebd3d2f9bc2c28bf9ede29eb7` | Gamescope + Xwayland + native Eden observed; exact renderer lost during warmup; zero FPS bins |

The XRes observer connected to Present 1.4/XRes 1.2 and identified renderer namespace PID 39 and its windows. **Correction:** direct CSV inspection found a header and one window-destruction event, not a header-only file. There are **zero game Present completions**. Device FPS measurement remains unproven. This run did not reach or verify Bonneton and is not an NCE performance number.

[Native graphics log](ARCHIVE.sha256):

- `Cpu.cpu_backend: Nce`; fastmem settings true. No recorded fastmem-required, 39-bit-address-space, incompatible-page-size or private-mapping refusal.
- `Driver: llvmpipe 26.2.3`, `Device: llvmpipe (LLVM 21.1.8, 128 bits)`, Vulkan 1.4.354.
- The active system Freedreno ICD instead names **Mesa/Turnip 26.2.3**; [ICD and kernel prerequisites](ARCHIVE.sha256) confirm 4096-byte pages, `vm.memfd_noexec=0`, map limit 1048576.
- [Full dmesg](ARCHIVE.sha256) has no entries after 02:50:37, before this Eden run. Its earlier boot/IOMMU warnings are not attributed to Eden. [Filtered view](ARCHIVE.sha256).
- [Exact-unit journal](ARCHIVE.sha256) records a missing desktop-portal D-Bus service and successful unit deactivation, not an explicit emulator crash. No runtime maps were captured before failure, so NCE execution remains **unproven**, not confirmed by its selection.

Inference: graphics-device discovery/selection needs investigation outside a plugin workaround. Neither the reason for software rendering nor the renderer identity loss is established. No Mesa variables, driver pin, graphics wrapper, CPU affinity or new Korri setting was added.

**bubblewrap: absent — core gap #184.** This is not sandbox acceptance. No wrapper or bypass was added.

## Backend, audio, save and soak acceptance

| Acceptance item | Status |
|---|---|
| Official `@korri:eden` installation | Not done; publication/official signing remains CI-only |
| Personal test inspect/install/enable | Passed; same source except the one approved runner-ID literal |
| SMO discovery and real library launch route | Passed, with retained discovery conflict caveat above |
| Save moved under actual saveRoot; staging removed | Passed; native `save_directory` and actual launch input agree |
| Source save rebound/loaded in Eden | Not proven; source profile directory retained for a later authorized attempt |
| Gamescope and CPU/GPU test settings | Passed; actual composition and resolved settings retained |
| First picture / device FPS collector | Failed / unproven; zero Present completions |
| NCE median / p10 | Unavailable; [failed report](firstlight-nce-retry/report.md), zero measured bins |
| Dynarmic median / p10 | Unavailable; not launched after mandatory graphics stop |
| Median ≥58 and p10 ≥50 | Not met / not measured |
| Faster stable backend shipped as default | No selection made; shipped ARM upstream NCE default unchanged |
| Audible audio, no drift, Eden PipeWire stream | Not verified; no audio acceptance claim |
| In-game save survives relaunch | Not verified; no in-game save/load claim |
| 15-minute soak without crash/thermal collapse | Not run |
| Restore to device defaults | Passed, including exact modifier-byte restoration and RPC readback |
| Exact cleanup | Passed; both exact cgroups empty, no emulator/observer leftovers, `SessionCompleted` |

The save payload now lives beneath the actual saveRoot's `nand/user/save/0000000000000000/<eden-profile>/0100000000010000/`. No profile rebind was attempted after the graphics stop. [Final state](final-state.json) records that boundary. No key, firmware, game or save payload is included in this evidence. Keys stayed mode 600 and were not changed.

## Checks and follow-up decisions

- Official ARM and x86 Eden package/admission checks passed from existing cached outputs. These include strict TypeScript, callback checks, ShellCheck and real build-host GUI startup; they do not substitute for hardware acceptance.
- Personal source byte comparison and the real Core admission/executor gate passed for two accounts.
- Discovery proof passed; it rejected changed existing values, removed existing games and unrelated new games. Ruff format/lint and mypy with published PyYAML stubs passed. Initial lint found one unused import; initial mypy lacked installed YAML stubs; both were corrected without weakening the check.
- No full repository suite or publication ran.

User decision required: authorize a separate graphics-stack/device-selection diagnosis before another launch. Cost: another exclusive device window; it may reveal an emulator/backend problem rather than fix hardware rendering. Do not claim the FPS target until real hardware rendering and the bench scene are proven.

Core follow-ups for the supervisor, not filed here:

1. No modifier-setting RPC; `LaunchSetting` has only CPU/GPU/governor fields (`contracts/generated/korrid.ts:617–631`).
2. No host/control caller issues folder-selection receipts; online pairing is unavailable on this host (`discovery/coordinator.rs:311–318`, `lib.rs:4920–4932`).
3. `LocalSessions` explicitly excludes discovery mutation but includes launch settings (`portal_access.rs:77–82,132–136`); the real rescan RPC returned HTTP 403.
4. An active control socket can reactivate korrid during the documented offline CLI, producing concurrent discovery and `DiscoveryConflict`. Next operational plan must account for that socket explicitly, not silently stop more services.
5. Staging must grant the service user access to both library content and imported saves, not only the runtime user.

The personal plugin remains enabled. The discovered source and imported save remain. Test launch settings are restored. No process from this stage remains running.

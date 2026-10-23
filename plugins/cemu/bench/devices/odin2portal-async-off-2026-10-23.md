# Odin Cemu — async compile off, 2026-10-23 UTC

**`AsyncCompile=false` runs BotW with the existing Cemu/Turnip pin. The completed
720p baseline is 39 / 38 / 36 FPS (median / p10 / p1), below the 40 FPS median
target. The 15-minute soak meets 40 / 38 FPS but has hitches. Audio passed;
a new in-game save remains unproven.**

This continues [first light](odin2portal-first-light-2026-10-22.md) and the
[Turnip 25.3.2 attempt](odin2portal-turnip2532-2026-10-23.md). Branch
`feat/cemu-odin` started clean at `08e9972`. No product code, pinned commit,
plugin installation, publisher/trust policy, Core, system or firmware changed.
The already installed personal test composition remains the one from `a944c7f`:
Cemu `29f2f1fae4631e2317977debd9eacd55cc28dd7d`, Mesa 25.3.2 only inside Cemu;
Gamescope still maps system Mesa 26.2.3. No build ran on Odin or any other device.
Only USB `root@<device-usb-ip>:2222` was used. Mini V2 was not touched.

## Recovery before launch

The known external `systemctl reboot` request at 04:33:28 completed with boot
`00ca24e7-8663-470c-90d9-339f2ec4bb10` starting at **04:34:35 UTC**. The previous
boot remained `c41b371b-88de-4b62-bcd7-aadc34f61d81` until shutdown. This was not
a second reboot. Read-only status returned `NoActiveSession`; there were no game
units, populated game cgroups, Cemu/bench processes, active host-session record,
or failed units. The earlier unrelated reach failure did not survive reboot.
The three root logins were the normal local console gettys, not competing SSH.
Historical LAN SSH connections at 04:35–04:36 were not used by this worker;
no competing test process was present when work began.

The interrupted async-off run had left the Gamescope modifier, game CPU/GPU
minimums of 100, async-off/crash-dump XML, and P2 controller installed. It had
produced several minutes of raw frames but no completed bench/cleanup report.
Before a new launch, recovery restored:

| State | Found → restored |
|---|---|
| Full library SHA-256 | `5f2f907f7410a389123e805cf6f31e40421f0ab4af9a593ae843a69cf8b2ffb9` → `8aa9f6be1c4a3ad1d5dbf7528365ccfab464a70414b9a00cbd4cf617c0f92806` |
| Native settings SHA-256 | `9a6c6a26d8ed6ccc9e02a55d625afaf53d0db7f2391b85e11ec5ee2e6c62925b` → `aef6d70d3d2e83027e5638f0ea772fe247a67463323bf43644292bf70f4573c8` |
| Controller SHA-256 | P2 `195356532834db07bc63fcf5907d61742ee4079d3afe1efac277eff6e36c5686` → P1 `738dffbb744252cd1a089411cc54640626e7157984fa263db3e7b697610ba25a` |
| Launch settings | Game `cpu.min=100`, `gpu.min=100` → absent; resolved CPU/GPU 0–100, device-default source, `schedutil` |
| Speaker | `Volume: 0.95 [MUTED]`; unchanged during recovery |
| Pipeline / driver caches | Generated files preserved under `resume-20261023/interrupted-cache`; originals restored from the recorded manifest, hashes `1189616bd80d4bc583bbf71d79e3a25cfe3cd6841d9270dc898c152076b3ba74` / `2d9cf17192e6f39b2d945ed90dbdec1757b7905dbc9fa7d0fd1a968a7e7a5b0a` |

The modifier bytes were restored before revision-checked RPC limit unsets.
After those RPC writes, full library bytes matched `async-off/library-before.yaml`,
not the intermediate `library-before-modifier.yaml` that still contained limits.
No unrelated game edit was undone. Recovery preserved the P1 file's current
owner/mode/ACL and restored its exact bytes; its pre-interruption mtime was not
persisted by the interrupted process. No unit reset, recovery-journal edit or
korrid restart was used.

## Ordered diagnosis

1. **Actual 25.3.2 crash log read completely:** no pipeline-creation failure,
   `VK_ERROR_DEVICE_LOST`, or Vulkan Error -4 was logged. It contains unsupported
   optional format/robustness notices and the already-known graphic-pack custom
   shader error, “using an unknown preset variable in shader”. That is not a
   logged Vulkan pipeline-creation failure. Missing error logs do not prove every
   pipeline compiled successfully.
2. **Async off works:** the same installed binary reaches sustained gameplay
   presentations without the previous `activeVertexDS` SIGTRAP. This supports the
   async-race hypothesis, but does not prove Cemu's internal state transition.
3. **Older Cemu `3310f3b8…` not built or launched:** the owner required stopping
   variant selection at the first running game. The committed Cemu pin is intact.

For the resumed tests, restored pipeline/driver originals were preserved again
under `trial/cache-original`; the first new run started without those two files.
Subsequent runs used the newly generated cache. Native settings were 720p,
`GX2DrawdoneSync=false`, `vkAccurateBarriers=false`, `VSync=0`,
`AsyncCompile=false`, FPS++ normal 45 FPS preset plus its retained advanced
40 FPS value. `CrashDumpUnix=1` was diagnostic only. CPU/GPU minima of 100 were
set only at the game layer through the existing revision-checked RPC.

## Every bench run

All paths below are relative to device staging. Values are one-second X Present
completion bins, not panel Hz or reciprocal frame-time percentiles. `—` means
no qualified complete sample, not zero FPS. All resumed launches used the real
library → korrid → Gamescope → Cemu route and Cemu-generated P2 profile; P1 was
restored after each exact stop. No bubblewrap was observed (existing Core gap).

| Run | Variant / purpose | Warmup + sample | median / p10 / p1 FPS | Peak °C |
|---|---|---|---|---:|
| `async-off/baseline` | Previous worker; same binary, async off; external reboot | Planned 100 + 180 s; interrupted | — (partial diagnostic: 38 / 38 / 32) | 95.9 |
| `resume-20261023/trial/baseline` | Async off, fresh pipeline/driver cache; stopped for unexpected volume changes | Planned 100 + 180 s; interrupted | — | 95.1 |
| `…/baseline-02` | Async off; complete 720p baseline | 100 + 180 s | **39 / 38 / 36** | **96.7** |
| `…/save` | First native menu save attempt; no new game-data save | 2 + 3 s after script | 38 / 38 / 38 (not qualified gameplay) | 94.7 |
| `…/save-02` | Second native menu save attempt; no new save | 2 + 3 s after script | 38 / 38 / 38 (not qualified gameplay) | 94.3 |
| `…/save-03` | Final supervisor-supplied menu sequence; no new save | 2 + 3 s after script | 39 / 38 / 38 (not qualified gameplay) | 92.7 |
| `…/soak` | Relaunch staged save; async off | 100 + 900 s | **40 / 38 / 34** | **97.5** |

The old interrupted run's partial values use 166 complete bins and an inferred
measurement start from its first measurement telemetry row. They are not a
completed result. The intentionally interrupted resumed baseline's generated
zero placeholders are not reported as FPS. The owner later confirmed the volume
changes were physical button presses and authorized continuation.

Screenshots were never opened or viewed. SHA-256, dimensions and numeric pixel
statistics were computed with a script. Baseline screenshots at 100/160 seconds
had entropy 0.815/0.806, versus 0.178 during loading at 30 seconds. This does not
independently identify a named location. The route loads the same newest staged
Zora's Domain save without movement; no visual fixed-spot claim is made.

## Audio, save and soak

**Audio passed.** The live Cemu Cubeb output stream was the only output stream,
linked to the Speaker sink. A 3-second, 48 kHz stereo float speaker-monitor
capture had 288000 finite samples, peak **0.12802124**, RMS **0.02043296**.
The owner physically heard BotW and lowered the volume from 0.95 to 0.50 to
0.40. The restore guard correctly rejected that unexpected volume change rather
than overwriting it; the worker re-muted and stopped its exact bench normally.

At **04:44:35 UTC**, the owner's new instruction superseded the initial exact
0.95 restore: keep the speaker muted for all remaining tests and leave the volume
as found. It was then `Volume: 0.40 [MUTED]`. It was not unmuted again.

**New manual save not proven.** The worker tried Plus → one/two right-shoulder
presses → A → A, then the supervisor's bounded final sequence: Plus, ten
right-shoulder presses, A, A, wait, Plus. The bench proves P2 received each native
input. The first two attempts changed only `option.sav`; the final attempt
changed no file. No `game_data.sav` hash changed and no new manual slot appeared.
The known baseline was selected again through `app.saves.restore` before retries.
No further menu guess or save-file fabrication was attempted. This is an input
route gap, not evidence of a storage write failure. Native save contents and
conflict copies were not edited to manufacture a save.

The diagnostic fanotify file-read test worked. Watches placed before launch did
not observe Cemu save I/O. **Inferred limitation:** launch-time save-tree
materialization can invalidate pre-launch inode watches. Do not treat those
empty watch logs as proof that Cemu did not read/write a file. The full native-tree
hash comparison is the evidence that a new game-data save was not made.

**15-minute soak passed the specified crash/thermal checks.** The same binary
completed 100 seconds of warmup and **900 measurement seconds**, through the
real library route, on the staged save. Overall FPS was **40 / 38 / 34**, minimum
**4** in one second. The standard baseline missed median 40; the longer soak
met both FPS targets. This is not a claim that every loaded scene meets them.

All 15 [per-minute summaries](../samples/odin2portal-cemu-async-off/soak/minutes.json)
are retained. Minute medians were 38, 39, 39, 39, 40, 41, 41, 41, 41, 40, 40, 40,
41, 40, 40. Peak temperature was **97.5 °C**, below every exposed critical trip
(110 °C), but above passive trips. The monitor would stop the exact bench if a
critical trip was reached or 31 complete consecutive one-second bins fell below
20 FPS. Neither occurred. Isolated hitches did occur; this is not a hitch-free
qualification. Their cause was not traced.

The staged slot-5 game-data hash remained
`c76a76d07215836f705159b13ea7e9506594cc9fd459c3cfb365976a8eee8d03`
across relaunch and soak. That is persistence of an existing file, **not** proof
of a new in-game save or a traced Cemu read of that file.

## Final restoration and decisions

At **05:18:33 UTC**, guarded restoration and an independent read-only audit
passed. The [restoration proof](../samples/odin2portal-cemu-async-off/restoration.json)
and [audit](../samples/odin2portal-cemu-async-off/final-audit.json) retain:

- Exact full original library bytes (`8aa9f6be…`), with modifier restoration before
  revision-checked CPU/GPU unsets; resolved CPU/GPU 0–100 from device defaults.
- Exact pre-test native XML (`aef6d70d…`), including async **true**, and original
  P1 bytes (`738dffbb…`). No diagnostic crash-dump setting remains.
- Both original cache hashes from recovery, with owner/group **1000:1000**, mode
  **0660**, timestamps and ACLs copied from the preserved originals. Generated
  test caches remain aside, not deleted.
- Speaker **`Volume: 0.40 [MUTED]`**, unchanged in volume during final restoration.
  This deliberately follows the owner's later instruction, not the old 0.95 rule.
- `SessionCompleted`, no game/acquisition/failed unit, empty exact cgroups and
  host-session directory, no Cemu/Gamescope/bench/observer/recording/watch/guard
  process, no bench pad. Only original CompositeDevice0 remains; bench observers
  verify original P1/source ownership and false ManageAllDevices.
- Same boot ID and generation-8 system/bundle. CPU policies use `schedutil` with
  minima 307200/499200/595200 kHz; GPU is 220–680 MHz, `simple_ondemand`.
  No reboot, foreign game unit or unowned configuration edit occurred.

The personal test composition remains installed/enabled as before; removal at
Land remains the parent's responsibility. No installation or permission bypass
was used in this continuation. The owner should finish the manual save route
with physical screen observation before accepting the stage.

The measured workaround belongs in Cemu's own native settings, not a new plugin
schema or a shipped per-device default. Final restoration returns async compile
to **true** and reinstates the original known-poisoned pipeline/driver caches;
the original async-on state is not qualified for play. The owner must decide
whether to use async off for play. Its cost is synchronous compilation stalls;
the baseline misses the median FPS target, and isolated soak hitches reached
4 FPS in a one-second bin. No affinity feature, typed Cemu setting or device
profile was built. The older Turnip closure and Adreno-only Vulkan limitation remain;
a patched 26.2.x replacement is still a separate decision. Temperatures above
both the 90/95 °C passive trips matter even if FPS remains stable; the checked
cpu7-middle critical trip is 110 °C. No cooling policy was changed.

| Acceptance | Result |
|---|---|
| BotW library launch through real korrid, Vulkan | **Passed**, async off; actual process mappings retain Cemu-only Mesa 25.3.2 |
| Median ≥40; p10 ≥35 | **Soak passes 40 / 38; standard baseline misses at 39 / 38** |
| Audio audible; Cemu PipeWire stream | **Passed**, non-silent capture and owner heard the speaker |
| New in-game save survives relaunch under saveRoot | **Not proven**; manual menu route did not create a new game-data save |
| 15-minute soak, no crash or thermal collapse | **Passed**, 900 s; peak 97.5 °C; isolated hitches, no sustained collapse |
| Launch settings restored to device defaults | **Passed**, revision-checked RPC and physical-clock audit |

## Checks and evidence

Focused bench checks passed: **12 unit tests**, mypy `--check-untyped-defs`
(9 files), Ruff check, and Ruff format check (9 files). A real fanotify
notification test observed a native file read without process injection.
Raw-metrics reproduction passed for all **180 baseline and 900 soak bins** and
all stored percentiles. `git diff --check` passed. No full repository
suite, package rebuild, publication, push or merge was run.

Private evidence remains on zao under `/tmp/cemu-odin-evidence/` (0700), with
new `resume-*` files and `resume-snapshot/`; on Odin under
`/var/lib/korri/cemu-bench-staging/resume-20261023/`. Screenshots, save data and
existing private cores are not committed. [Committed samples](../samples/odin2portal-cemu-async-off/README.md)
retain raw gzip Present/telemetry, reports, settings, exact-stop/input/profile
proofs, per-minute soak summaries and final restoration/audit. No new save or
physical-screen claim was substituted for missing evidence.

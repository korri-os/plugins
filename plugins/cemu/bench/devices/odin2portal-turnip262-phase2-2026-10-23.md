# Odin Cemu — gameplay-gated patched Turnip phase 2, 2026-10-23

**Recommendation: keep 25.3.2 for now, with `AsyncCompile=false`.** Patched
26.2.5 is a reproducible short-run improvement: three async-off gameplay runs
have median **40 FPS**, against **37 FPS** in the same-session shipped reference.
Two async-on runs have median **39 FPS**, with no draw-state assertion observed.
The owner stopped the campaign after async-on run 2. The 15-minute soak is
**not run (owner decision)**, so long-duration qualification remains open.

**Verified:** the shipped 25.3.2 personal test plugin, device-default launch
settings, exact library/native/P1 bytes, all original cache files and muted
speaker are restored. The original complete 54-file payload is selected under
a new continuation. No further game launch was made after the owner's stop.

## Scope and build isolation

The port starts at `ae8f767` and preserves main's Cemu source, file-cache shutdown
fix, build evidence, licence collection, Gamescope packaging and gameplay bench.
It brings the Turnip-only derivation, fixed-point late-algebraic patch, upstream
draft, ICD substitution and exact-patch package check from `e417888`. The
[earlier report](odin2portal-turnip262-patched-2026-10-23.md) is retained with its
USB address redacted. Its ungated performance results are **not** comparison
inputs for this decision.

Main actually keeps Cemu and the bench on `nixpkgs-held` (`a6531044…`); the
2026-10-20 pin applies to the other migrated packages. An initial attempt to
move all Cemu dependencies to the new pin failed because its inherited fmt
patch does not apply to the forced fmt 12.1.0 source. That move was abandoned.
The supervisor approved keeping Cemu and its dependencies unchanged and passing
the separate Turnip derivation as one composition argument. The measured driver
uses the held set and has the **same store path as the earlier patched driver**.
Mesa licence notices now use the selected Turnip's actual release source,
unpacked before collection; the first notice-collection check caught an archive
being passed where a source directory was required.

| Component | Exact path / result |
|---|---|
| Measured patched Turnip | `/nix/store/g33aq3b8mljbiay5ls6nin7kkwxi3xbq-mesa-turnip-cemu-fmadz-26.2.5` |
| Driver runtime libc | `/nix/store/89n0gcl1yjp37ycca45rn50h7lms5p6f-glibc-2.40-66` |
| Driver runtime libdrm | `/nix/store/53bbslxqirqx59ic6762nm2449jc2s60-libdrm-2.4.128` |
| Separate 2026-10-20-pin compatibility build, **not measured** | `/nix/store/h98r1nmfh5921vlmr6kb53yph6bgsbpk-mesa-turnip-cemu-fmadz-26.2.5` |
| Compatibility-driver runtime | glibc 2.44-57; libdrm 2.4.134 |
| Compatibility-driver tests | `ir3_disasm` and `ir3_delay_test`: 2 passed on fuji |
| Cemu, current main source plus driver swap | `/nix/store/1skk344pqh26i0k4d8ndllaa78nb883x-cemu-0-unstable-2026-10-22-29f2f1f` |
| Production-namespace plugin, built only | `/nix/store/sqqca0alnf3gsklv7rrmsvwn025z0yrr-korri-plugin` |
| Personal test plugin, measured | `/nix/store/si3mvb24vnw6hmlcia0wa4ll7wyma6li-korri-plugin` |
| ARM package check | `/nix/store/j8j8prxsx72q8qdm49fa0n3xmc6n73a0-korri-cemu-package-check` |
| Gameplay bench, unchanged | `/nix/store/092bcnlgn7w4vbbp5cknp30j72cv2h32-korri-cemu-bench-0.1.0` |
| Shipped personal test plugin, found and restored | `/nix/store/g7adybv05pxjyi1klapk19xrjbm7b0ql-korri-plugin` |

The separate compatibility build proves Mesa 26.2.5 still builds with the new
nixpkgs pin. It does not qualify that different closure on hardware. No target
build ran. No Core, Mini V2, system generation, bootloader or firmware changed.
No push, merge or publication occurred.

## Measurement contract

Each short run uses 100 seconds of warmup **after** verified gameplay, then
180 one-second X Present bins. The soak requests 900 bins after the same warmup.
The gate must observe title, loading and gameplay in order, then gameplay again
at sample end. Failed gates are not measured; no title-screen FPS is accepted.
The existing private helper was reviewed before use. Every bench runs as a
managed SSH process, with `keepAfterChild: true`. Before each launch, the helper
and bench check for foreign units and renderers. Speaker stays muted.

Settings: 1280×720 May native settings, FPS++ normal 45 with retained advanced
40, VSync 0, draw-done sync false, accurate barriers false. Only AsyncCompile
changes between the patched cases. CPU/GPU minima are set to 100 at the game
layer through revision-checked RPC, with exact original settings retained for
restoration. This is explicit: the phase-1 report describes device-default
minima; this phase's same-session shipped run controls the requested 100/100
comparison directly. No affinity, cooling or system-driver change is made.
No named scene or visual HUD correctness is claimed.

## Every launched run

| Run | Mesa / async | Gate title / loading / gameplay / end (s) | median / p10 / p1 / min FPS | Peak °C | Result |
|---|---|---|---|---:|---|
| Shipped 01 | 25.3.2 / off | 8.56 / 26.25 / 44.69 / 326.85 | 37 / 37 / 36 / 36 | 95.9 | PASS |
| Patched off 01 | 26.2.5 mapped / off | none observed | — | — | **not measured**; stale-log helper refusal |
| Patched off 02 | 26.2.5 / off | 9.27 / 45.06 / 65.07 / 347.14 | 40 / 40 / 39 / 39 | 97.1 | PASS |
| Patched off 03 | 26.2.5 / off | 9.48 / 47.30 / 66.46 / 348.63 | 40 / 40 / 39 / 39 | 96.3 | PASS |
| Patched off 04 | 26.2.5 / off | 9.66 / 48.23 / 70.08 / 352.32 | 40 / 39 / 39 / 39 | 95.9 | PASS |
| Patched on 01 | 26.2.5 / on | 9.03 / 48.62 / 69.38 / 351.63 | 39 / 39 / 38 / 37 | 96.7 | PASS |
| Patched on 02 | 26.2.5 / on | 9.71 / 48.99 / 69.45 / 351.80 | 39 / 39 / 38 / 38 | 95.9 | PASS |
| Patched on 03 | planned 26.2.5 / on | — | — | — | **not run (owner decision)** |
| 15-minute soak | preferred 26.2.5 / off | — | — | — | **not run (owner decision)** |

There are **six valid samples**, each with all 180 bins: one shipped, three
patched async-off and two patched async-on. One additional launch is not
measured. No third async-on run or soak was started. All short-run thermal
peaks are below the monitored critical trips, but up to 97.1 °C exceeds the
passive thresholds. No thermal policy changed.

Async-off's three medians are 3 FPS (**8.1%**) above the same-session reference;
p10 is 39–40 rather than 37, p1 is 39 rather than 36. Async-on is 2 FPS above
the reference, but 1 FPS below async-off, with lower tails. These are sequential
stationary-scene samples on one device, not a randomized A/B or a claim about
all BotW scenes. The earlier ungated 39/38/36 and 40/38/34 results are excluded.

**Async-on assertion result:** neither of the two valid async-on launches hit
`VulkanRenderer::draw_execute`, SIGTRAP, or null `activeVertexDS`. Both passed
loading and completed gameplay. This is real bounded gameplay evidence, unlike
the previous title-only attempts; it does not prove the Cemu race is fixed.
No accepted patched-run Cemu log contains `Unhandled ALU op` or device loss.
An independent `coredumpctl` query for Cemu over this campaign found no dumps.

[Public reports, raw Present/telemetry, driver proofs and restoration audit](../samples/odin2portal-turnip262-phase2/README.md)
retain the evidence. The privacy guard reproduces every FPS bin from raw events.

The first patched attempt was stopped before title because the private helper
read the previous run's unchanged 25.3.2 Cemu log immediately after seeing the
new 26.2.5 library map. The game unit ran for about two seconds. It is **not
measured**; a fresh driver log was never observed. Exact stop and 54-file restore
passed. The helper now ignores log files older than its launch timestamp and
checks a fresh driver version throughout the run, independently of first map
capture. Three direct checks prove stale-log rejection, fresh expected-version
acceptance and fresh wrong-version detection. The immutable bench and numeric
gate thresholds are unchanged. This identified cause was fixed before another
launch; no blind gate retry was used.

Signed delivery: zao signed the closure with its transport key and personal
publisher key. Normal `nix copy` delivered the closure over USB. The private
file cache received two new narinfos and their NARs without replacing existing
files. `korri-plugin inspect`, exact-approval `update`, and `enable` passed;
approval `5230c425546e5d6f783e35dca45bf3f6d8a6533b9b3ed76273c0353cf49a690d`.
No trust setting changed and no key was printed. An incompatible pair of tar
options refused the first cache-delta transfer before extraction; the corrected
explicit file list transferred only new files.

Cemu's fresh log identifies `Mesa 26.2.5`, `Turnip Adreno (TM) 740`, and the
requested native async value in completed patched runs. Their process maps show
the `g33aq3b8…` ICD library, libc 2.40-66 and libdrm 2.4.128 together. No symbol
or ABI loading error is observed. The shipped comparison maps the 25.3.2 driver.
Actual Gamescope is the unchanged installed system 3.16.18, not the newer 3.16.31
package merely present on main. Its system Mesa is separate. No bubblewrap is
observed; this does not qualify Core ADR 0015.

## Save safety and restoration

The campaign starts at current head
`sha256:989fc95bcaf0d9aae12b549f50b3fafdefd394640724f6448032ca7e06eb3d21`.
All 54 payload files are verified before every launch. A complete separate host
backup contains 54 blobs, each independently verified against its SHA-256 name.
The bench uses the supported restore RPC after exact stop; it selects the same
complete payload under a new continuation and proves ancestry. It never writes
objects or fabricates a save. The actual slot-3 read is required before warmup.

These launches append session and restore records to the owner's real history.
Payload restoration is not history isolation and does not resolve #208/#212.
No further manual-save attempt is part of this campaign.

### Whole-campaign restoration proof

The supported restores added **14 history records**: seven session snapshots
and seven restore continuations, including the early helper refusal. No
foreign play was stopped. WL4's complete history remained unchanged. Every
valid run read slot 3's actual `game_data.sav`, SHA-256
`34726184bf791cea4714e7847b111e56a5475cf1d4103c4e576c7a5fc475abea`, before warmup.

| Check | Verified final state |
|---|---|
| Final selected head | `sha256:659722c172a10b0069dd01e802fff0190d54a964e2697f9759d7577dee0e5508` |
| Save payload | Exact original locations/files; **54/54** size/hash complete; original head in ancestry |
| Plugin | `g7adybv0…`, Enabled; approval `99fa60a3…`; wrapper selects `jqr5bd0q…-mesa-25.3.2` |
| Registry `previous` | Now the measured patched `si3mvb24…` build; supported update necessarily records it |
| Full library, including exact BotW item | SHA-256 `8aa9f6be1c4a3ad1d5dbf7528365ccfab464a70414b9a00cbd4cf617c0f92806` |
| Launch settings | Original layers/profile selection; CPU/GPU 0–100 from device defaults, schedutil; RPC revision guards used |
| Cemu native settings | Exact original `a1d81eaf…`; shipped `AsyncCompile=false` |
| P1 | Exact original `738dffbb…`; per-run native profile metadata restoration passed |
| Caches | All **3772** original file names/hashes match; generated cache directories moved aside, never deleted |
| Speaker | `Volume: 0.55 [MUTED]`, as found; never unmuted |
| Idle | No game unit, Cemu/Gamescope/Eden, observer/helper/test process or bench pad |
| Boot/system | Unchanged boot `28218e4c-6645-4cbd-bae8-119b91fe2f1c` and system `xqbqdwrn…` |
| Device Nix policy | `require-sigs=true`, `max-jobs=0`, empty builders, `fallback=false` |

The original cache-manifest SHA-256 before and after is
`fb6692806889d2bccbb20c9f43a71029f5c24f06b5a1f0c5f3e1c709ff1e0ab1`.
The full private manifest includes the account path, so only its hash and count
are published. The current payload is the existing complete May continuation;
this campaign does not recover the unavailable older owner-session payload.
No unit reset, recovery-journal edit, korrid restart, system update, firmware
write, bootloader operation or Mini V2 access occurred.

## Plugin decision

**Keep the shipped 25.3.2 and `AsyncCompile=false` until a later approved soak.**
This is a qualification judgement, not a claim that the candidate failed. The
short-run evidence favors patched 26.2.5 **with async off** and justifies finishing
its qualification. Keep its code on this experimental branch; do not switch the
published plugin yet. The owner explicitly skipped the soak and third async-on
run, so #211's original hardware acceptance remains incomplete.

Cost of this recommendation: keeping 25.3.2 leaves the measured 3 FPS median
improvement unused. Cost of switching now: sustained thermal/stability behavior
has not been measured, and a five-minute scene cannot substitute for 15 minutes.
Even after a soak, another scene/device and rendering correctness would remain
outside this campaign. There is no evidence here to change the shipped native
async default to true; async-on is slower in both measured runs.

## Upstream Mesa work (#211)

The upstream work should proceed: first a minimal NIR/ir3 regression test, then
an MR. This hardware campaign cannot replace the unit test. The draft remains
unsubmitted. Still missing: a synthetic NaN/Inf-preserving reproducer that
exercises the final context cleanup and fails without the patch, relevant Mesa
CI, and maintainer review of fixed-point convergence and traversal cost. No
conformance result is claimed. The separate compiler-error cleanup crash remains
outside this patch.

Private evidence: zao `/tmp/cemu-phase2-20261023/`; Odin
`/var/lib/korri/cemu-bench-staging/phase2-*`. Save payloads, private account paths,
keys and screenshots stay outside Git. No image viewer is used.

## Commits and focused checks

Code: `92b9d70` ports the driver and redacted history; `0e30464` selects matching
licence sources; `3b99449` unpacks the release source for notice collection. The
final evidence commit records the owner-bounded campaign and restored state.
The personal composition is pinned to full source SHA
`3b994491f7e3dcfa5674da4c8b9de65bd6249ab7`; only its source namespace changes to
`@simonwjackson`. The production-namespace plugin was built but not installed.

- ARM package check passed: strict TypeScript, real plugin launch contract,
  generated-wrapper ShellCheck, selected ICD/library/exact patch, 28 required
  licence notices, build evidence, graphic-pack defaults, and real Xvfb CLI,
  native configuration and seed preservation.
- Separate current-pin Mesa build passed its two real IR3 tests on fuji.
- `turnip-check.py`: mypy, Ruff check and Ruff format passed. Nixfmt passed for
  every changed Nix file. Source/document whitespace checks passed; conventional
  blank context lines in the imported unified patch are excluded.
- Public sample privacy (**312 files**), checksums (**285 entries**) and raw FPS
  reproduction (**16 arrays**, including all 1080 new accepted bins) passed. History
  scans for account IDs, device IPs, personal paths and key material are zero.
- The actual path was exercised through signed install, real korrid RPC,
  Gamescope, Vulkan Cemu and the immutable gameplay gate. Five patched and one
  shipped samples completed. No full repository suite was run.

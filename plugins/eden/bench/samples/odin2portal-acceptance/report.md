# Odin SMO resume-platform acceptance — 2026-10-23

**NCE and Dynarmic pass the 58 median / 50 p10 FPS target at the approved static reference. The 15-minute NCE soak passes. Settings are restored and SMO is stopped. This does not prove open-town performance.**

**Bonneton resume platform, camera turned to face the Odyssey; not the open town area; FPS may be optimistic versus open-area play.**

Temporary native guest P1 → Korri Seat P2 is used for scripted input. The shipped default remains Seat P1. Mario does not move. [Reference, three launch checks and frozen tape](REFERENCE.md).

## Results

| Run | Measured seconds | Median FPS | p10 | p1 | Status |
|---|---:|---:|---:|---:|---|
| [Native-default NCE](nce/report.md) | 180 | 60 | 60 | 60 | Pass |
| [Explicit Dynarmic](dynarmic/report.md) | 180 | 60 | 60 | 59 | Pass |
| [NCE soak](soak-nce/report.md) | 900 | 60 | 60 | 59 | Pass |

The soak retained the exact renderer and window for all 900 FPS bins. Its [midpoint image](ARCHIVE.sha256) shows normal idle sleeping at the same location, camera, 1242 coins and 3 health. One 0.5-second Present probe and XGetImage capture ran during the soak; all affected bins remain included. [Telemetry](telemetry-summary.json) records a peak CPU sensor of **83.2 °C**, RSS **5,998,652 → 5,999,420 kB** during measurement, and **zero swap**. The sample count for telemetry is not the exact FPS-bin count.

Both backends reach the presentation cap. NCE wins the tie without changing Eden's native default. These are game-window X11 Present CompleteNotify/Pixmap counts, not compositor Hz, an emulator counter, simulation speed or independent physical-panel scanout. The collector discards 100 seconds after the identical evemu replay, includes zero one-second bins, and uses nearest-rank p10/p1. Navigation screenshots were inspected before measurement; the collector's automatic PASS alone does not accept the scene.

The existing game-layer controls temporarily requested `cpu.min=100`, `gpu.min=100`, and Gamescope enabled. Actual clocks are retained rather than assumed pinned. Normal restored-limit performance is not measured here. No CPU affinity or per-device performance profile was introduced.

All completed runs use the real library path: normal reserve/start → korrid plugin executor → admitted personal runner → Gamescope/Xwayland → Eden. The observer selects Eden-owned windows through XRes. Exact launch identities, runtime maps, clocks, temperatures, RSS/swap, raw Present CSV, screenshots and empty-cgroup cleanup are in the run directories.

## Renderer, backend and save

Fresh effective logs identify **Turnip Adreno (TM) 740**, **turnip Mesa driver 26.2.3**, Vulkan **1.4.354**. No ICD was removed, Mesa override injected, driver pinned, or plugin bubblewrap workaround added.

NCE is **inferred** from its fresh native-default effective log, executable HostMemory and no large Dynarmic-like RWX cache. Dynarmic is **inferred** from explicit native selection, no refusal and an anonymous RWX code-cache-sized mapping. Neither is direct instruction-execution proof. See each `backend.json`.

The user's save, manual save and normal relaunch persistence were already proven in [SAVE-PROOF.md](../odin2portal-graphics/SAVE-PROOF.md). These runs again show **1242 coins / 3 health**, not a new save. Normal Core session-end capture remains the save path. No history records, identities or Core save-import schema were created by hand.

The apparent three Dynarmic launch failures were diagnosed before another attempt: [one-paragraph diagnosis](DIAGNOSIS.md), [journal/status/CLI evidence](dynarmic-diagnosis-evidence.json). The latest error referred to an older launch stopped by the supervisor, not a new Dynarmic crash. After replacing the supervisor's separate retained-status poll with observation of its new renderer cgroup, the controlled Dynarmic run completed. No interrupted attempt contributes FPS.

## Silent audio

**not verifiable at night, stream verified**. The default speaker sink remained **Volume: 0.50 [MUTED]** before and after observation. Eden's running PipeWire output had two active links to the running built-in speaker sink. See each `audio-graph.json` and the soak's midpoint/late snapshots. The same two active links remained at **889 seconds** of measured soak time, with volume still unchanged and muted. No volume was set, raised or unmuted; no tone was played. Sink-monitor samples and audible drift were not tested because the sink was muted; the approved night branch is graph-only verification.

## Tested source and deployment

| Item | Exact tested output |
|---|---|
| Plugin source | `945e9d4` |
| Personal package | `/nix/store/24yf1xbs5213vqx2if3qlqsz1cz6qqfz-korri-plugin` |
| Launcher | `/nix/store/77ndp24virwb0khxal8id2r46pi9w915-eden-korri-0.2.1` |
| Unchanged cached Eden | `/nix/store/010847afgzfll903n5dbzqdajmm1m0n7-eden-0.2.1` |
| Signed collector 0.2.2 | `/nix/store/zd7jxck7icv2hizxr6zlx65ci4n89qnz-korri-eden-bench-0.2.2` |

The personal test source changes exactly one publisher literal, `@korri:eden/eden` → `@<publisher>:eden/eden`; it otherwise matches `945e9d4`. [A fresh comparison of the actual installed source and native helper artifacts](deployed-source-proof.json) verifies that delta. This is not an official-publisher release or a second shipped package. Normal inspect/install/enable, permissions and signature checks remain in force. Builds ran on <builder-1>; <build-host> signed cached outputs before signature-checked delivery. Nothing compiled on Odin. Mini, firmware and boot-chain partitions were untouched. The official publisher binding and Nix trusted-key policy were not changed; the approved personal test publisher used normal admission. Nothing was pushed, merged or published.

[Fresh closure comparison](closure-growth-final.json): **373 → 374 paths**, **+2,306,528 NAR bytes (2.20 MiB)** against the original launcher. This supersedes the earlier pre-P1-helper closure total. [Current native preflight bounds](preflight-bounds.json), from 5 ms host-monotonic process sampling:

| Launch | Both native helpers, lower–upper bound |
|---|---:|
| NCE | 140.50–151.52 ms |
| Dynarmic | 165.08–176.02 ms |
| NCE soak | 267.39–278.51 ms |

These envelopes include the gap between the Vulkan and P1 helpers, not the whole emulator startup. The bounds are sampled lifetimes, not a precise trace. A transient fork can inherit a helper's argv; overlapping rows are not added twice. They test an already configured account (valid explicit Adreno and preserved P1 choices), not first-time untouched-account seeding.

## Restoration and checks

[Final direct restoration proof](final-restoration-proof.json):

- Exact pre-override native INI restored: SHA256 `85567c3ec16deff77cac4fa831c37130dab6b48f281cbc50beaf289f323d6a3c` matches the recorded baseline. The temporary backup copy is deleted.
- The baseline keeps the account's permanent native-UI **Seat P1** mapping, valid Adreno selection and native-default NCE. The obsolete keyboard-only/llvmpipe configuration was not restored. [A direct final native read](final-native-selection.json) confirms SDL port 0/button 1, explicit Vulkan index 1, and native-default NCE; RPC idle was also verified.
- CPU/GPU minimum overrides were removed through fresh-revision RPC writes; the Gamescope change was restored with a checked merge. The entire library file matches its original SHA256 `8aa9f6be1c4a3ad1d5dbf7528365ccfab464a70414b9a00cbd4cf617c0f92806`. [Resolved settings](settings-restored.json) show device-default minimums of 0 and `schedutil`.
- All three measured exact cgroups are empty; no Eden process remains. No session was left running for the user.
- Final speaker volume is still **0.50 [MUTED]**.

The full 15-minute run completed autonomously after navigation acceptance; its supervisor restored the INI first, then launch settings. Interrupted preparations also restored the exact file before resuming.

| Focused check | Result |
|---|---|
| P1 native-config tests | 9 passed |
| Vulkan native-config tests | 12 passed |
| Ruff, both helpers and their tests | Passed |
| Strict mypy, both helpers | Passed |
| Earlier ARM/x86 package/admission and real GUI gates | Passed at the tested source; see prior evidence |
| Raw Present CSV recomputation | All 180/180/900 FPS bins and summary values match |
| Copied run-file integrity | 54 files match SHA256 computed on Odin |
| JSON evidence parsing / local documentation links | Passed |
| Git whitespace / secret hook | Passed |
| Full repository suite | Not run by this child |

Cemu retained priority. A persistent read-only five-minute watch and per-step checks stayed in place; the bounded supervisor yields by stopping only its collector's exact launch. No discovery, session or history state was cleared. The already completed NCE measurement was preserved across provider interruptions.

`bubblewrap: absent — core gap #184`

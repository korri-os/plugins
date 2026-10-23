# Odin Cemu bench gameplay gate — phase 1, 2026-10-23

**Verified:** the normal run measured real gameplay at **37 / 37 / 36 FPS**.
The deliberate no-input run reported **not measured**, with no FPS file/table.
The original complete 54-file save payload is selected again, under a new
continuation with the original in its ancestry. The manual-save route remains
**unproven after two attempts**.

Branch: `fix/cemu-bench-gameplay-gate`, base `34e75dc` (which contains the
published Cemu source at `ccb3310` plus two main build-wiring commits). Only
`bench/` changed, including its own Nix derivation. No shipped plugin code,
installation, Core, publisher/trust policy, system or firmware changed. Nothing
was pushed, merged or published.

## Gate and save safety

- Require two consecutive per-game numeric title appearances. The first title
  image can be non-interactive; it is not a claim that Continue already accepts
  input. BotW's native A pulse repeats every two seconds until a loading
  reference matches, bounded at 60 seconds. No fixed launch delay chooses state.
- Require loading, then two gameplay matches before warmup. Check gameplay again
  immediately before warmup and at sample end. Any failure is not measured,
  exits non-zero and publishes no performance result.
- Reference captures are numeric 31×27 RGB descriptors plus sparse title
  foreground data, per game/output size/aspect. No image viewer was used.
  Numeric capture/calibration commands and limits are in the bench README.
- Core ADR 0014, generated saves/session RPC types, `SCRIPTING.md`,
  `host/saves.rs` and `saves/store.rs` expose no supported guest/test launch or
  snapshot opt-out. Sync cannot be disabled for a runner that declares saves.
- Before launch, check peers/current head, then verify every original blob's
  size and SHA-256. Keep a private complete backup. After exact stop, including
  failures, select the original with `app.saves.restore` and verify content,
  completeness and ancestry. Restore appends; it cannot preserve the head ID.
  It selects the next launch's content; the bench never hand-copies live saves.

## Device proof

Prebuilt ARM tool, built on yari, signed on zao, copied over USB:
`/nix/store/092bcnlgn7w4vbbp5cknp30j72cv2h32-korri-cemu-bench-0.1.0`.
Earlier iterations built on fuji. No handheld build ran.

Actual Cemu binary:
`/nix/store/3qks80jgqy1p6i01914n9pnjnhj8kygk-cemu-0-unstable-2026-10-22-29f2f1f/bin/Cemu`.
Its log/maps show Mesa 25.3.2; Gamescope remains the system 3.16.18/26.2.3
composition. This report identifies the observed closure, not an unverified
claim about which later Cemu source patch it contains. The installed personal
test runner was used as found; no plugin was installed or replaced.

Native settings: 16:9, 1280×720, FPS++ normal 45 with retained advanced 40,
`AsyncCompile=false`, VSync 0, draw-done sync false, accurate barriers false.
Resolved CPU/GPU 0–100 and schedutil stayed at device defaults. The old 39/38/36
baseline temporarily used game clock minima of 100; these are not controlled
thermal/settings A/Bs. No affinity, clock, GPU debug or cooling change was made.

| Case | Title at | Loading at | Gameplay at | End check | Result |
|---|---:|---:|---:|---:|---|
| Normal, 100 + 180 s | 11.04 s | 36.60 s | 68.80 s | 350.87 s | **37 / 37 / 36 FPS**, minimum 36; peak 95.9 °C |
| Broken, no input | 9.87 s | not observed | not observed | not sampled | **not measured**, exit 1, loading deadline, no FPS output |
| Save route 1 | 9.02 s | 27.01 s | 47.60 s | not sampled | **unproven**, no changed game-data hash/mtime within 30 s |
| Save route 2 | 10.99 s | 28.73 s | 50.10 s | not sampled | **unproven**, same bounded failure |

Normal Cemu read the actual slot-3 game_data.sav after materialization, before
warmup: SHA-256 `34726184bf791cea4714e7847b111e56a5475cf1d4103c4e576c7a5fc475abea`.
All 180 Present bins reproduce from retained events. The median is two FPS
below the earlier 39/38/36 result, not a performance win. No named location or
visual HUD correctness is claimed. No phase-1 soak or patched-driver test ran.

[Public proofs, raw compressed events and reports](../samples/odin2portal-gameplay-gate/README.md).

### Earlier diagnostic attempts, not hidden successes

One initial preflight refused its split/in-use check before launch. A later
supported check returned no warning/in-use device and one current head; no save
choice or force flag bypassed the guard. The first three-press normal attempt
matched title at 9.75 s but never matched loading. It timed out, emitted no FPS
and restored the original payload. This motivated bounded A-until-loading.
An earlier deliberate no-input diagnostic also timed out safely.

The owner then physically advanced and played during an intended title-label
run. It observed the real title → loading → gameplay sequence, but is **invalid
as an automated normal or broken proof**. Its one-second performance result is
not accepted or published. Its numeric fingerprints are labelled
`owner-driven-sequence`; they are not independently labelled interactive-menu
references. No additional screen labels were guessed.

### Whole-campaign save and restoration proof

| Fact | Verified result |
|---|---|
| Original head before any launched test | `sha256:466882dd8033a57f3454e1c7dffa4804d3ace969ce77bda4fc0e7025a43c3b1e` |
| Final selected continuation | `sha256:989fc95bcaf0d9aae12b549f50b3fafdefd394640724f6448032ca7e06eb3d21` |
| Payload/location equality and ancestry | Exact original payload; all **54/54** files complete by size/hash; original in ancestry |
| Final four proof/route attempts | Four session records + four restore records: **8** additional history records |
| Whole campaign, including earlier launched diagnostics | Seven sessions + seven restores: **14** additional records; preflight refusal added none |
| Owner's WL4 quit | Snapshot `c1cf7c18…`, ended 20:15:12 UTC, duration 2417 s, not interrupted |
| WL4 after bench | Same current head and all 69 records; Synced, not Split; no write/choice/restore issued |
| Full library bytes | Original SHA-256 `8aa9f6be1c4a3ad1d5dbf7528365ccfab464a70414b9a00cbd4cf617c0f92806` |
| Cemu native settings | Exact original SHA-256 `a1d81eaf2d81e0a51a06268ea038661b008eb1c73adf77d64218983046efe5ae`; async false |
| P1 | Exact original SHA-256 `738dffbb744252cd1a089411cc54640626e7157984fa263db3e7b697610ba25a`; per-run metadata/ACL restoration |
| Launch settings | Original selection/resolved limits restored; no settings RPC write was needed |
| Caches | Preserved full directory copies restored; generated Cemu/Mesa caches moved aside, not deleted; final manifest retained |
| Audio | Speaker left at 0.55, **MUTED** throughout |
| Idle | No game/acquisition unit, Cemu/Gamescope/Eden/observer/test process or bench pad; cgroups idle |
| Boot/system | Unchanged boot `28218e4c-6645-4cbd-bae8-119b91fe2f1c`, same generation-8 system |

The current payload is the already selected, complete May fallback from the
previous campaign, **not** recovery of the unavailable owner-session `5f3c80b8…`.
No unavailable old payload was selected. A separate host backup of the original
54 files was verified complete by hash. No claim is made that all older history
payloads remain complete.

**Note for #212:** content protection is implemented, but history isolation is
not available. Bench and restore records still sync and count toward retention.
This does not fix #208. A supported guest/snapshot-free diagnostic session needs
Core work; no new Korri account/launch schema was invented here. The new manual
save/relaunch branch remains unproven: neither of its two attempts made a new
`game_data.sav`, so neither proceeded to a reload proof. No save was fabricated.

## Checks

- **33 bench unit tests passed**, including all original 16, recorded numeric
  classification, ordered gates/deadlines/end checks, no-measurement reports,
  bounded advance, complete/corrupt/missing saves and supported restoration.
- **mypy**, **Ruff check/format** passed for all 21 bench Python files.
- **Nixfmt** and `git diff --check` passed for the scoped change.
- ARM and x86 bench package checks passed: 29 packaged unit tests each, C
  `-Wall -Wextra -Werror`, and the real Xvfb Present/XRes fixture. The original
  three-second fixture wait first failed on a loaded x86 host; it now waits for
  actual events with a 30-second bound, without weakening the event assertion.
- Public sample privacy, checksums and every FPS array reproduce. No full
  repository suite or full verification was run.

Private evidence on zao: `/tmp/cemu-bench-gate-evidence/` (0700). It contains the
complete save backup, original reports, native/config/cache restoration audits,
source fingerprints, build logs and phase-2 commands. Device evidence is under
`/var/lib/korri/cemu-bench-staging/gameplay-gate-20261023-*`. No PNG or save payload
was committed, and no image viewer was used.

## Phase 2 handoff

Patched-driver installation is **not included**. Use normal signed plugin
installation/approval, and record actual Cemu/Mesa/Gamescope closures. The tool
above is already copied; use it directly, never `nix build` on the device.

The private administrative helper is already at
`/var/lib/korri/cemu-bench-staging/run-phase2-gated.py`. It is a command wrapper,
not a second bench: it invokes the immutable bench above with
`--repeat-input-until-loading` and actual slot-3 read proof. It snapshots/restores
the existing BotW item, native async value, P1 and caches, leaves Speaker muted,
and uses the normal RPC lifecycle. It refuses foreign games before launch and
bounds the run; its soak monitor stops its own bench at an exposed critical
thermal trip. This phase-2 wrapper was syntax-checked, not run against a patched
driver in phase 1. Review it before use.

After the approved patched Mesa **26.2.5** installation, exact device commands:

```sh
PYTHON=/nix/store/1974x81r734g6rs38snfhkdkj28n77vc-python3-3.13.9-env/bin/python3
HELPER=/var/lib/korri/cemu-bench-staging/run-phase2-gated.py
"$PYTHON" "$HELPER" patched-async-off off run 26.2.5
"$PYTHON" "$HELPER" patched-async-on on run 26.2.5
"$PYTHON" "$HELPER" patched-soak off soak 26.2.5
```

Use the actual approved version for the last argument if it differs. The helper
records the exact bench argv in `bench-command.json`. Normal runs are 100 s
warmup + 180 s gameplay; soak is 100 s + 15 minutes. The bench CLI equivalents
and reference-capture commands are in the README. Keep physical input hands-off
for normal and broken proofs. Async-on may still hit Cemu's separate draw-state
assertion; any crash/gate/safety failure is not measured. No new save-route
attempt is authorized by this handoff; its two-attempt budget is exhausted.

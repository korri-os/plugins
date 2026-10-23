# Odin final scoped verification — 2026-10-23 UTC

The [resume-platform report](samples/odin2portal-acceptance/report.md) records
real NCE/Dynarmic 180-second measurements and a 900-second NCE soak, all with
median/p10 60/60 FPS. NCE p1 is 60; Dynarmic and the soak p1 are 59. Raw game-window
Present CSV recomputation agrees with all 180/180/900 bins. Fifty-four copied
run files match hashes computed on Odin. All exact cgroups are empty.

Bonneton resume platform, camera turned to face the Odyssey; not the open town area; FPS may be optimistic versus open-area play.

Fresh focused checks: nine P1 tests and twelve Vulkan tests pass; Ruff passes
for both helpers and their tests; strict mypy passes for both helpers. The
prior ARM/x86 package/admission and real GUI checks remain at the tested source
`945e9d4`. No full repository suite ran in this child.

Actual installed plugin/helper bytes match the source, apart from the approved
single personal-publisher literal. The exact pre-override native INI SHA256
matches after restoration, its temporary backup is deleted, and the library
SHA256 matches the original. The account keeps its permanent native Seat P1
mapping; scripted tests temporarily mapped guest P1 to Seat P2.

Audio remains muted at unchanged 0.50; two active Eden-to-speaker links were
verified through the late soak. **not verifiable at night, stream verified**.
No audible/waveform drift claim is made. Backend execution remains inferred.
`bubblewrap: absent — core gap #184`.

This supersedes the device status below. Earlier stages remain historical.

---

# Odin first light verification update — 2026-10-23 UTC

The later [device report](samples/odin2portal-firstlight/report.md) supersedes
only the device status below. Personal inspect/install/enable, SMO discovery,
actual Gamescope composition, and settings restoration passed. First picture
and device FPS proof did not: zero Present completions, llvmpipe selected, exact
renderer lost during warmup. The workflow's no-picture stop rule applied.
No Dynarmic run or soak followed. All performance/audio/save acceptance remains
pending. No production plugin or collector code changed.

The four existing Eden package/admission outputs passed (cached ARM and x86),
and a real personal-source admission/executor check passed for two accounts.
The new discovery proof passed and rejected three invalid changes. Its Ruff and
mypy checks passed. See the report for the evidence and operational caveats.

---

# Verification — 2026-10-23 UTC

Code commit: `9f7151d` on `feat/eden-bench`. No Eden plugin installation or
SMO launch occurred. Mini was left untouched in this stage.

## Focused checks

| Check | Result |
|---|---|
| Python tests on local build host | 21 passed |
| Native x86_64 Nix package check | 21 passed; real Xvfb Present integration passed |
| Native aarch64 <builder-1> Nix package check | 21 passed; real Xvfb Present integration passed |
| Observer/producer C compilation | `-std=c11 -Wall -Wextra -Werror` passed on both architectures |
| Ruff lint and format | Passed, 12 Python files |
| mypy, including untyped function bodies | Passed, 12 Python files |
| nixfmt | Both bench Nix files passed |
| Git whitespace / secret hook | Passed on source and evidence commits; no bypass |
| Documentation/evidence checks | 3 shell blocks parsed without execution; 17 local links resolved; 11 JSON files parsed; 9 journal lines counted |
| Exact signed bench closure delivery to Odin | Passed with signature checks enabled |
| Actual Odin session reserve/start | Proven for wl4, launch `f927719fbb1e98399c1ebb5f31b9ef86` |
| Exact stop / process cleanup | Unit stopped; exact cgroup and owned processes empty; RPC acknowledgment returned `HostRecoveryBlocked` |
| Device FPS gate | **Failed: actual route had no Gamescope modifier; zero samples** |
| Device observer/FPS proof, SMO navigation, soak | Not proven; moved to Odin stage |
| Mini staging and gate | Deferred to Mini stage after Cemu; not attempted here |

The integration fixture creates two real X clients without `_NET_WM_PID`.
The observer identifies only the requested process through XRes, counts its
Present completions and records destruction. Unit cases cover 100-second
discard, 180 bins, zero bins, Skip exclusion, missing/replaced windows, real
loopback RPC, exact-stop failure handling, native CPU-backend evidence, and
retained terminal failures with empty/populated/unreadable cgroups and our own
failed launch. No full repository suite ran.

Initial checks found a missing Xrandr header dependency and XRes's zero-valued
`Success` convention. Both were corrected before passing native checks. Device
preconditions then exposed the retained-terminal-status case; its six new
safety tests passed before version 0.2.1 delivery. Public fingerprint labels
triggered a secret-scan false positive in an early documentation attempt; the
unnecessary full standalone public identifiers were shortened. No secret rule
or hook was bypassed, and no actual key contents entered the repository.

## Exact deliverable

Built through the local daemon on explicit builder
`ssh-ng://<user>@<retired-builder>`, not a handheld. The queued build completed;
no builder configuration or other worker's job was changed.

```text
/nix/store/2xcl1ll4y3v47jdrbxmkz1hqrk4iaasq-korri-eden-bench-0.2.1
```

- Deriver: `/nix/store/gkd8qfwzxwanynxziz89kjdnkwhwikip-korri-eden-bench-0.2.1.drv`.
- NAR hash: `sha256-Pejl47j58x3/Jh5TewCjgGHIOn2+clCrKNsWCsuQuUw=`.
- NAR bytes: **129,912**. Runtime closure: **375.2 MiB**.
- Native x86 check output: `/nix/store/kyav00dpj4xr2z9hi8x9nri22v44clgi-korri-eden-bench-0.2.1`.
- Automatic `<builder-1>-1` signature is not the delivery authority. The closure was
  recursively signed on <build-host> with its existing `korri-cache-<build-host>-1` key, then
  copied with `nix copy`. Odin already trusts that key. No secret was printed,
  no trust was added, and no signature bypass was used.

## Preserved device attempts

| Attempt | Device directory beneath `/var/lib/korri/eden-bench-staging/` | Outcome |
|---|---|---|
| 0.2.0 initial | `trivial-present-20261023` | Connection refused before reserve; daemon PID changed outside this workflow, 1974 → 14635 |
| 0.2.0 retry | `trivial-present-20261023-retry1` | Prior terminal `HostLaunchFailed` before reserve; 120-second same-PID watch and plugin admission query passed |
| 0.2.1 gate | `trivial-present-20261023-v021` | Real wl4 session, but authoritative composition was `modifiers: []`; exact stop followed; no device FPS sampled |

Committed evidence:

- [First report](samples/odin2portal-attempt1/report.md).
- [Precondition retry](samples/odin2portal-attempt2/report.md).
- [Final device gate](samples/odin2portal-v021/report.md),
  [process/cleanup proof](samples/odin2portal-v021/cleanup.json),
  [nine unit-journal lines](samples/odin2portal-v021/ARCHIVE.sha256), and
  [read-only diagnosis](samples/odin2portal-v021/findings.md).

The final read-only settings inspection found no Gamescope record at device,
runner, system or game scope. No layer explicitly sets false: there is no
opt-in, so the modifier is absent. No wl4 setting was changed.

At **02:08:39 UTC**, status reported `SessionCompleted` for later launch
`9e0ad09294554e745129f0685dbecaaa`, not `HostRecoveryBlocked`. The stop-time
recovery refusal is not currently present. No manual clearing or restart was
performed, and no further launch was attempted. The exact earlier recovery
predicate is unknown; see findings.md for source-grounded recovery boundaries.

## Remaining cost / acceptance boundary

The tool is proven on a device through reserve, start, exact stop and
empty-cgroup cleanup, **not device FPS measurement**. Its only admitted test
game ran without Gamescope. The stop RPC's recovery error remains part of the
failed report; kernel cleanup is not a claim of fully successful reconciliation.

Device FPS proof moves to the Odin stage using SMO's own game-layer settings.
Mini content staging moves to its stage after the Cemu run. Bubblewrap remains
Core gap `korri-os/korri#184`; it is not concealed by an extra wrapper. Neither
the native Xvfb tests nor backend source inference substitutes for SMO gameplay,
Bonneton input admission or a hardware soak.

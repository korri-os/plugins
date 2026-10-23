# Eden final status

## Final device results — 2026-10-23 UTC

**NCE ships as the ARM default.** Odin passed at the labelled static view:
**Bonneton resume platform, camera turned to face the Odyssey; not the open town
area; FPS may be optimistic versus open-area play.** Backend execution is inferred.

| Device / run | Seconds | Median / p10 / p1 FPS | Result |
|---|---:|---|---|
| Odin NCE | 180 | 60 / 60 / 60 | Passed labelled view |
| Odin Dynarmic | 180 | 60 / 60 / 59 | Passed labelled view |
| Odin NCE soak | 900 | 60 / 60 / 59 | Passed; peak 83.2 °C |
| Retroid Pocket Mini V2 | — | No FPS numbers | Out of memory within 5,559 MiB; temporary INI restore unverified until physical reset and hash check |

Odin's original native INI, library settings and permanent Seat P1 controls are
restored. Mini's last temporary 0.5×/Seat P2 INI must be treated as unrestored.
Do not launch Eden on Mini before the user restores physical access and checks
the protected baseline hash. No Mini performance default is shipped.

Bubblewrap was absent: **Core gap #184**, not sandbox acceptance. Audio was
verified silently only: active graph links, unchanged muted sink. **Not
verifiable at night, stream verified**; no audible-audio acceptance is claimed.
No official-publisher release occurred.

See [Odin report](samples/odin2portal-acceptance/report.md),
[Odin reference](samples/odin2portal-acceptance/REFERENCE.md), and
[Mini memory/recovery report](samples/rpminiv2-memory/REPORT.md).

---

## Historical checkpoints below

These dated checkpoints are not the current authorization or device state.

# Odin resume-platform result — 2026-10-23 UTC

**NCE and Dynarmic passed the approved static-view target. The 15-minute NCE
soak passed. The exact native INI and original library settings are restored;
the temporary INI backup is deleted and SMO is stopped.**

Bonneton resume platform, camera turned to face the Odyssey; not the open town area; FPS may be optimistic versus open-area play.

| Run | Seconds | Median / p10 / p1 FPS |
|---|---:|---|
| NCE | 180 | 60 / 60 / 60 |
| Dynarmic | 180 | 60 / 60 / 59 |
| NCE soak | 900 | 60 / 60 / 59 |

See [the final scoped report](samples/odin2portal-acceptance/report.md),
[reference](samples/odin2portal-acceptance/REFERENCE.md), and
[Dynarmic interruption diagnosis](samples/odin2portal-acceptance/DIAGNOSIS.md).
The real save and manual-save persistence passed. Silent audio is graph-only:
unchanged 0.50 and muted, with two active Eden-to-speaker links. Audible audio
is **not verifiable at night, stream verified**. Backend execution is inferred.

Temporary guest P1 → Korri Seat P2 was used only for the bench/soak; the shipped
default and restored account use Seat P1. The approved personal package matches
`945e9d4` with one publisher-literal change. No official release occurred. Mini
was untouched at this historical Odin checkpoint. `bubblewrap: absent — core gap #184`.

This result supersedes the device status below, not its historical evidence.

---

# Odin first light update — 2026-10-23 UTC

**Stopped at the required graphics gate.** The personal test build passed
inspect/install/enable and SMO discovery. A real library launch reached
Gamescope/Xwayland, but produced zero observed game Present completions and no
observed picture. Eden selected llvmpipe 26.2.3 rather than Turnip. Its exact
renderer identity disappeared during warmup; the collector stopped its own unit.
No emulator crash, accepted NCE/Dynarmic FPS, audio, save persistence or soak is
claimed. SMO's test launch settings were restored and verified.

See [the stage report](samples/odin2portal-firstlight/report.md). This update
supersedes the preparation-stage authorization/status below. Official publisher
admission remains separate from the approved personal test build. Mini was not
contacted. Bubblewrap: absent — core gap #184.

---

# Eden preparation status — 2026-10-23 UTC

Keys and USB connectivity are resolved. This stage authorizes content staging
and a real **non-Eden** launch through korrid. It does **not** authorize Eden
installation, SMO gameplay, firmware downloads, system updates or identity changes.

| Device | Content | Trivial launch |
|---|---|---|
| Odin, `10.42.4.1:2222` | Verified complete staging; see [content record](device-facts/odin2portal-content.md) | 0.2.1 delivered; reserve/start/stop proven, FPS gate failed because Gamescope was absent |
| Mini, `10.42.3.1:2222` | Left untouched; deferred to Mini stage | Deferred until that stage, after Cemu finishes |

Every device step checks emulator/bench processes first and waits when busy.
Odin's initial Cemu run was busy, so this worker waited for completion. It did
not stop or modify another worker's bench. The device-facts snapshots remain
dated observations, not current reservations of either device.

## Verified-owner account and staging boundary

The signed owner statement, not the local signer's current public half, defines
the account. Odin's statement hash and BIP340 signature were verified on <build-host>.
Core's existing `saves::account_root` and launcher producers define account and
save roots; see the content record for source citations and exact paths.

Odin has no admitted SMO playable or Switch source pairing yet. Therefore its
real SMO saveRoot cannot be obtained without the next-stage admission. The
supervisor explicitly approved save staging under the verified account's
native Eden data. No `users/<owner>/saves/<guessed-id>` was created. After
admission, obtain the actual saveRoot, move/rebind the staged save, validate it,
and delete the staging copy. No catalog, device.yaml or identity was edited.

SMO is physically staged in the existing `games/<system>` convention, grounded
in Core's migration producer and actual storage configuration. The next stage
must use normal discovery pairing/rescan as needed; plugin installation alone
does not prove an unpaired folder is scanned.

## Inputs and one-off save preparation

User-supplied host keys are at
`/home/<user>/.local/state/korri-eden-test-keys/prod.keys` (14,612 bytes)
and `title.keys` beside it (1,292 bytes). Source mode is 600; source directory
mode is 700. Copies go only to the verified account's Eden keys directory,
mode 600. No key bytes or key digests are logged or committed.

SMO and firmware come only from the requested read-only `<user>@<content-host>` tree.
The firmware source has 214 directories and 167 regular files, with 246,074,368
regular-file bytes; that layout is preserved, not converted into 214 files.
No firmware is downloaded and decryption is not yet tested.

The April operational note converts **to Ryujinx**, not to Eden. The prepared
SMO payload excludes `ExtraData0`, `ExtraData1`, `.lock`, working directories
and Syncthing conflict copies. Host scratch is outside repositories at
`/tmp/eden-smo-save-20261022/`. Source profile
`<eden-profile>` is the newer source chosen in that note.

| Payload | Size | SHA256 |
|---|---:|---|
| Common.bin | 1036 | `def8bd226daedd2b08808e277e68ed3224be8f606609acaa44ecf99169101fac` |
| File1.bin | 2097164 | `f3b0a2f4e5af014ccc0da95198161904a0ae7073cff2ea88a8936ea091c240f5` |

Eden 0.2.1 `src/core/file_sys/savedata_factory.cpp:130–138` defines its native
`user/save/<zero>/<profile>/<title>` account-save layout. Checked the actual
pinned `/nix/store/inmrhbhn9k0lnrcw8v4hi9rc2nwp9k95-source`, not an assumed
legacy layout. Forge's actual plugin keeps keys/firmware account-local and
maps game saves beneath `saveRoot/nand/user/save`. The staged source profile
has **not** been rebound to an actual Eden profile, and no save load or
Bonneton position is claimed.

## Bench acceptance boundaries

Versions 0.2.x replace the unavailable MangoHud route. Its independent Xlib
observer measures real game-window X11 Present completions inside Gamescope's
Xwayland. Missing events/window replacement still fail. Bubblewrap's absence
is recorded as **Core gap korri-os/korri#184**, not hidden by an extra wrapper
and not treated as a plugin FPS failure. See README.md for the method and
backend-inference limits.

Bench closure signing uses the existing <build-host> key (`korri-cache-<build-host>-1`) and normal
signature-checked `nix copy`. This is not plugin-publisher authorization. No
trusted key, plugin permission, system generation or sysfs policy is changed.

## Final device gate and diagnosis

The signed 0.2.1 closure is present on Odin at
`/nix/store/2xcl1ll4y3v47jdrbxmkz1hqrk4iaasq-korri-eden-bench-0.2.1`.
The real wl4 launch `f927719fbb1e98399c1ebb5f31b9ef86` had a direct
RetroArch plan and `modifiers: []`. The collector stopped its exact session
rather than silently substituting another pipeline. No observer or FPS samples
were produced. The cgroup and owned processes were empty; cleanup RPC reported
`HostRecoveryBlocked`. The full failed report and nine unit-journal lines are
[preserved](samples/odin2portal-v021/report.md).

Read-only follow-up found no Gamescope record at any modifier layer, not an
explicit false override. It changed nothing. Current status at 02:08:39 UTC
was `SessionCompleted` for a later launch, so a recovery refusal was no longer
present. No manual recovery or daemon restart occurred. See the
[findings](samples/odin2portal-v021/findings.md) for exact evidence and source.

The supervisor ended this stage here. Device FPS proof moves to the Odin
stage, using SMO's own game-layer launch settings rather than changing wl4.
Mini content staging moves to its own stage after Cemu. No further launches
were attempted.

## Next stage remains separate

- Install Eden only through inspect/install/enable with normal approval.
- Admit the real Switch source/playable; obtain real game saveRoot and Eden profile.
- Move and rebind the staged save, validate loading, delete staging.
- Verify input admission, record Bonneton navigation and prove the scene.
- Only then measure SMO, confirm Vulkan/backend evidence, and run the soak.

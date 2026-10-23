# Turnip and the user's SMO save — verified 2026-10-23

**The user's existing progress loads through the real library route on Turnip, and an in-game save survives a normal stop and relaunch.** FPS targets, audio and soak remain pending in this evidence checkpoint.

## What is on screen

[After relaunch](ARCHIVE.sha256) shows Mario in Bonneton with **1242 coins and 3 health**, in the same position as [before the manual save](ARCHIVE.sha256). The [Resume menu](ARCHIVE.sha256) replaced the new-game-only menu after the proper save binding. This is the user's progress, not a newly started game.

| Proof | Observed value |
|---|---|
| First Turnip launch | `b1ff9942e6d3a1192c681cdd4f0c9674` |
| Normal session that captured the relocated files | `cd787b52254148388fb2297bd0b36c93` |
| Real progress and manual in-game save | `596f5ac108935fcb8887d35b1caff02d` |
| Relaunch with the saved progress | `e1fc09fd6c12fbc8123470d49b3a51c6` |
| Native renderer | `Driver: turnip Mesa driver 26.2.3`; `Device: Turnip Adreno (TM) 740` |
| Native effective CPU setting | `Cpu.cpu_backend: Nce` — setting evidence, not direct execution proof |
| Latest checked history snapshot | `sha256:1d078bb7a4de2e8e1e86e44fecf1e5bde1fc7253cc3b6f004a1679fd5d02dd84` |
| Checked after supervisor restart | 08:10–08:11 UTC; no game processes or active units; korrid PID 1964 unchanged |

All game launches used `app.session.reserve` → `app.session.start`, the same path as the library, with the admitted personal runner. No game ran directly from an administrator shell. Game-layer Gamescope and CPU/GPU minima 100 remain set for the unfinished performance stage. No affinity, driver pin, Mesa selector override or new Korri setting was introduced.

The personal test package is `/nix/store/57mhcg8sb7ma9128ajp9kqjil3h370dy-korri-plugin`, from source **`dd6d0e7`**. Its TypeScript source differs by exactly one approved runner literal, `@korri:eden/eden` → `@<publisher>:eden/eden`; the byte comparison passed. Its launcher is `/nix/store/sb5n610yvbk59qg66sfk8pyj9w3hc163-eden-korri-0.2.1`. Eden's underlying cached binary is unchanged. Normal publisher signatures, inspect approval and host admission were used. The official publisher binding was not changed.

## Native identity, not a created profile

The existing profile save is the account's `.local/share/eden/nand/system/save/8000000000000010/su/avators/profiles.dat`, 1616 bytes. Native `System/current_user=0`, `current_user\default=true`, and no boot-time user chooser select its first valid profile. [Extracted metadata](turnip-stage/active-profile.json) records raw UUID `<eden-profile-2-raw>`. The game's own `EnsureSaveData` log confirmed `<eden-profile-2-raw>`.

The native legacy folder is **`<eden-profile-2>`**, not the raw UUID's byte-order spelling. Grounding is the actual pinned Eden 0.2.1 source:

- `src/core/hle/service/acc/profile_manager.cpp:26–43,49–69,396–433`: 16-byte prefix, eight 0xC8-byte user records, valid-user selection and existing profile loading.
- `src/common/settings.h:672`: current-user default 0.
- `src/common/uuid.cpp:175–178`: UUID bytes copied to the native u128.
- `src/core/file_sys/savedata_factory.cpp:134–138`: legacy account folder uses uppercase high u64 then low u64.

No identity was created, replaced or re-keyed. The two imported files remained byte-identical through copying. Runtime owner `korri` and named/default ACLs for service user `korrid` were applied. Service read and runtime write checks passed. The protected backup remains on the device; it is not in this repository. The original B520 copy was retained as explicitly authorized.

## Why the first relocation did not load

Two independent boundaries had to be corrected:

1. **Native INI group encoding.** The old wrapper wrote `[Data Storage]`, but Eden reads `[Data%20Storage]`. `Config::BeginGroup` at `src/frontend_common/config.cpp:962–966` calls `AdjustKey` at 999–1003, which replaces spaces with `%20`. The old runtime test incorrectly checked the wrapper's discarded input group. Updating the test to inspect Eden's actual consumed/rewritten group reproduced failure: the native GUI wrote an empty save path. Fix **`dd6d0e7`** writes only the encoded native group. The real GUI now rewrites the requested saveRoot path, with `save_directory\default=false`, and preserves unrelated resolution settings across two accounts and two games.
2. **Core materializes its selected snapshot before launch.** An offline worktree rename is not a history import. `saves/mod.rs:62–70` skips initial capture when that device already has history; `host/session_state.rs:1413–1422` materializes the existing base. The initial between-runs move was therefore replaced by the known B520 tree.

No Core code, history, record, identity or recovery state was edited. The supervisor authorized using the normal end-of-session capture: launch normally, leave SMO waiting at its title screen, copy the two user's files to the 29A5 folder, retain the source and backup, then exact-stop the session.

Core's `host/session_state.rs:816–885` calls `NativeSaveStore::capture` on the declared locations at proven completion. `saves/store.rs:316–397` walks those current filesystem locations, reads each regular file, hashes its bytes and records the relative path. It does not reuse the old materialized file list. [Copy proof](turnip-stage/save-bind-capture/copy-proof.json) and [capture proof](turnip-stage/save-bind-capture/capture-proof.json) confirm the new selected snapshot contains both 29A5 files with the user's original hashes. The subsequent normal launch displayed Resume and the user's Bonneton progress.

## Manual save and relaunch

In the running game, Plus opened the pause menu; three Down presses selected Save. [Saving](ARCHIVE.sha256) and [return to the pause menu](ARCHIVE.sha256) were captured. Both `File1.bin` and `Common.bin` changed hashes and increased modification times under SMO's actual saveRoot.

[The normal completion snapshot](turnip-stage/real-save-proof/manual-save-capture-proof.json), `sha256:df984a1db88a534667a364e1a27d2a586a8e1282e3bf19639e52f1c14f2f4d59`, contains both changed files with their recorded hashes. The next normal launch resumed the same 1242-coin progress. [Post-restart verification](turnip-stage/save-relaunch-proof.json) confirmed that snapshot still matches both manual-save hashes, and that the latest history still contains both 29A5 files. Both hashes advanced again after the later play session; this is recorded rather than incorrectly requiring played saves to remain byte-identical.

Every retained session cleanup shows an empty exact cgroup. The last managed supervisor was lost during a Forgerie restart, but its on-device bounded controller completed cleanup; the later native process/unit observations also found nothing running. No state was cleared to obtain that result.

## Checks and remaining work

The native group regression failed before the fix and passed afterward. ARM (<builder-1>) and x86 package/admission checks passed, including the real CLI/GUI, two-account/two-game path retargeting, TypeScript contract/type checks, shellcheck, Ruff, strict helper mypy and 12 Vulkan-selection tests. Focused runtime-check Ruff and mypy also passed. Bench 0.2.2 passed its 26 tests, type/lint checks and real two-window X Present test on both architectures; it is not yet an FPS result.

The closure/time figures in this paragraph are the pre-P1-helper stage. The
[later acceptance report](../odin2portal-acceptance/report.md) supersedes them
with the final `945e9d4` package and fresh per-launch bounds.

[Final closure comparison](closure-growth.json): **373 → 374 paths**, **+2,296,168 NAR bytes**. The first production preflight's 5 ms process sampling bounds its lifetime to **218.70–230.12 ms**; this is wall-time sampling, not a precise trace. [Raw sampling](turnip-stage/first-picture/preflight-timing.json) is retained. Later runs preserved the existing valid Adreno index. A later renderer mapping confirms `libVkLayer_MESA_device_select.so` was loaded normally; this did not require any environment override.

The host Wayland grim attempt timed out without bytes and was terminated by exact owned PID. Evidence images instead came from XGetImage on the actual presenting Eden game window, in its mount namespace and runtime UID. This proves the rendered application image, not independent physical-panel scanout. No FPS claim comes from title-screen Present events.

Next: native P1 seat defaults and real gamepad admission, verified Bonneton replay, NCE/Dynarmic measurements, silent PipeWire validation, 15-minute soak, then revision-checked settings restoration. The user is asleep; volume must not be changed.

**bubblewrap: absent — core gap #184.** This is not sandbox acceptance.

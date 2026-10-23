# Odin Cemu — temporary Turnip 25.3.2 pin, 2026-10-23 UTC

**The Cemu-only pin works and leaves Gamescope on system Mesa 26.2.3.
BotW still crashes: SIGTRAP in Cemu's draw path while loading the staged save.
The stage stopped after that first launch, as the owner required.**

This resumes the [first-light campaign](odin2portal-first-light-2026-10-22.md).
It does not replace that report's original Mesa 26.2.3 `fmadz` diagnosis or
turn the earlier one-second title-screen FPS into gameplay evidence.

## Change, build and signed delivery

Branch `feat/cemu-odin`; code commit **`a944c7f`**.

| File | Change |
|---|---|
| `plugins/cemu/package.nix` | On aarch64 only, substitute the locked nixpkgs Mesa 25.3.2 freedreno ICD into the wrapper. Assert version 25.3.2 so a lock update cannot silently change this temporary choice. |
| `plugins/cemu/wrapper.sh` | Export `VK_DRIVER_FILES` and `VK_ICD_FILENAMES` inside the Cemu wrapper, before exec. No parent/global environment change. |
| `plugins/cemu/turnip-check.py` | Require a 25.3.x freedreno ICD with its actual library present on aarch64; require no override on other architectures. |
| `nix/cemu-check.nix` | Wire that check into the existing Cemu package check. |
| `plugins/cemu/README.md` | Explain the temporary pin, original backtrace/hash, Vulkan-only scope, and required replacement with patched 26.2.x Turnip. |

The implementation follows legacy `9c2d9e2b6`'s process-scoped ICD selection,
not its unrelated Ryubing driver choice. It does not alter Cemu source, system
Mesa, the image, Gamescope, other plugins, OpenGL selection or CPU affinity.
It retains all three earlier first-light fixes.

| Artifact | Exact value |
|---|---|
| Mesa | `/nix/store/jqr5bd0qqwq14pzi6jf0c1y9ljbkqgj7-mesa-25.3.2` |
| ICD | `.../share/vulkan/icd.d/freedreno_icd.aarch64.json` |
| Cemu | `/nix/store/3qks80jgqy1p6i01914n9pnjnhj8kygk-cemu-0-unstable-2026-10-22-29f2f1f` |
| Cemu source | `29f2f1fae4631e2317977debd9eacd55cc28dd7d` |
| Production-namespace package, built only | `/nix/store/0dffcnlb62ndsa05d8m3j666bn56zglz-korri-plugin` |
| Installed personal test package | `/nix/store/g7adybv05pxjyi1klapk19xrjbm7b0ql-korri-plugin` |
| Installed identity | `@<publisher>:cemu`, runner `@<publisher>:cemu/cemu` |
| Exact approval | `99fa60a3a1ed11cec9e68b522cb5b8ffa3727cf83b3cdc0a99d88ac2d46f8ac7` |

Mesa's official `cache.nixos.org/jqr5bd0qqwq14pzi6jf0c1y9ljbkqgj7.narinfo`
returned its signed metadata. `nix copy --from https://cache.nixos.org` confirmed
the store path was already available locally (`copying 0 paths`). Neither Mesa
nor its driver was compiled. The ARM build plan contained Cemu, declarations,
and focused checks only. Cemu rebuilt on **yari**, never Odin. x86 checks rebuilt
on zao. The same `/tmp/cemu-odin-test` personal-source composition was refreshed;
only its source namespace substitution differs from production.

Zao recursively signed the closure with its existing transport key. Its private
file cache used the existing personal publisher key. No key was printed or
copied. Signed `nix copy` and the cache transfer completed; supported
`korri-plugin inspect`, exact-approval `update`, and `enable` passed. No manifest
was rewritten and no trust/permission check was disabled. Publisher configuration
retained SHA-256 `c4fb42826ffdd99c93c96c7df8818890bc6fc6cfd075af65c6a889754df4acb3`.
No push, publication, merge, system update or firmware operation occurred.

Operational build notes: the first scratch-flake target omitted its aarch64
attribute and was corrected before building. After Cemu/admission completed,
the shared builder scheduler stalled; only this agent's client was cancelled,
and remaining checks/composition finished with yari explicitly selected.
The first default-xz cache export exceeded the attached command timeout;
the managed export resumed with zstd and completed before installation.

## Real path and driver isolation

The game is the existing library item
`the-legend-of-zelda-breath-of-the-wild-usa-dlc-v208`.
The actual path remained korrid `plugin-launch` → Gamescope → gamescopereaper →
Cemu, with `-f -g <WUA> --mlc <saveRoot>/mlc01` in its exact game unit.
**Bubblewrap not observed; core does not implement ADR 0015.**

Cemu's actual log:

```text
[04:12:31.540] ------- Init Vulkan graphics backend -------
[04:12:31.549] Using GPU: Turnip Adreno (TM) 740
[04:12:31.549] Driver version: Mesa 25.3.2
[04:12:35.020] CPU-Mode: Multi-core recompiler
[04:12:35.020] Full sync at GX2DrawDone: false
[04:12:35.020] Async compile: true
[04:12:35.020] Accurate barriers are disabled!
```

Captured **actual process mappings**, not just planned environment:

| Process | Driver mapped | ICD override |
|---|---|---|
| Cemu, PID 54179 | `jqr5bd0qqwq14pzi6jf0c1y9ljbkqgj7-mesa-25.3.2/lib/libvulkan_freedreno.so` | Both variables point to that package's freedreno ICD |
| Gamescope, PID 54150 | `nc0xr281k1wwf7g5f06vkj4l5xcyhs0s-mesa-26.2.3/lib/libvulkan_freedreno.so` | Both variables absent |

`/run/opengl-driver/lib/libvulkan_freedreno.so` still resolves to the latter
26.2.3 output. The device image and boot ID remained unchanged.

## One attempted benchmark, then stop

The poisoned pipeline/driver files were moved, not removed, into
`/var/lib/korri/cemu-bench-staging/turnip2532/poisoned-cache/{0,1}`.
Their manifest records original paths, sizes and SHA-256; restoration checked
those backups were intact. The old poisoned files were **not put back**.
Any newly generated cache remains the output of this failed 25.3.2 run, not a
qualified healthy cache.

The staged baseline save was restored with the supported `app.saves.restore`
using `sha256:0f0d9c7032899fefee5d8915d359b12d35401c7b86b99642509e2c6e04abfb5a`.
Only BotW temporarily received Gamescope under the existing approved modifier.
Game-layer `cpu.min=100` and `gpu.min=100` were set with revision-checked RPC.
Native May settings remained 1280×720, VSync 0, GX2DrawDone sync false, async
compile true, accurate barriers false. FPS++ actually selected its normal
45 FPS preset while retaining the advanced 40 FPS value, as before.
Native `Debug/CrashDumpUnix=1` was temporary core instrumentation, then restored.

| Bench folder | Planned warmup/sample | Result | median / p10 / p1 | Peak sampled temperature |
|---|---|---|---|---|
| `turnip2532/baseline/bench` | 100 s / 180 s, after the 40 s input script | Failed before warmup: `X Present observer exited` | **No qualified sample** | **No telemetry sample** |

The bench orchestration exited 1 after 52.06 seconds. The native game unit
reported 34.532 seconds lifetime including termination/core handling.
The visible title/save-menu route worked; `screen-30.png` shows BotW's loading
screen and 114 compiled pipelines. It does **not** show Link at the fixed spot.
The unit's shell reported `Trace/breakpoint trap!`; systemd-coredump recorded
Cemu **SIGTRAP**, signal 5. Gamescope then exited successfully, so the unit's
successful deactivation is not evidence that its Cemu child succeeded.
No Error -4 or `VK_ERROR_DEVICE_LOST` appeared. No new test-time GPU fault
appeared in dmesg; the old boot-time ARM-SMMU messages remain present.

No additional launch, audio-unmute probe, save attempt, async-off experiment or
soak followed this crash. The owner explicitly required stopping here.

## New crash evidence, distinct from the old Mesa fault

Host GDB examined the actual new core with the exact Cemu binary and ARM
sysroot. Its stack is **not** the earlier Mesa `fmadz`/ralloc stack:

```text
__pthread_kill_implementation
raise
VulkanRenderer::draw_execute(...) + 2596
LatteCP_processCommandBuffer_continuousDrawPass
LatteCP_ProcessRingbuffer
Latte_ThreadEntry
```

At the call site, disassembly loads a pointer from `this + 1320`, finds it null
(`x22=0`), sets signal 5, and calls `raise`. Immediately after that branch it
calls `draw_setRenderPass`. This matches Cemu source
`VulkanRendererCore.cpp:1638–1658`: a valid pipeline is followed by
`if (m_state.activeVertexDS) ... else cemu_assert(false)` in the continued draw
path. The comment says “should never happen unless draw_prepareDescriptorSets
can fail?”. The current pipeline handle was non-null in the captured branch.

**Verified trigger:** Cemu's own draw path raises SIGTRAP on this null-pointer
condition. **Inferred cause:** an asynchronous pipeline can become ready between
the first draw's invalid-pipeline early return (which clears `activeVertexDS`)
and a continued draw, leaving descriptors unprepared. That state transition
was not proven by a trace, and no fix or workaround was attempted. This is a
separate Cemu follow-up, not proof that Mesa 25.3.2 itself trapped or lost the GPU.
No Mesa debug download/build was needed for this Cemu-side stack.

The new core is preserved on Odin:

```text
/var/lib/systemd/coredump/core.cemu.1000.c41b371b88de4b62bcd7aadc34f61d81.54179.1792728776000000.zst
```

It is also retained privately on zao as `core-turnip2532{,.zst}`. It is not
committed or published.

## Restoration and acceptance

`turnip2532/restoration.json` and `settings-restored.json` prove:

- Exact pre-modifier library bytes restored **before** RPC CPU/GPU unsets.
  Other games, including the already-present Super Mario Odyssey item, remain.
- CPU/GPU resolved settings match the initial snapshot: **0–100**, device-default
  source, governor `schedutil`.
- Native diagnostic XML restored byte-for-byte; original P1 profile restored,
  SHA-256 `738dffbb744252cd1a089411cc54640626e7157984fa263db3e7b697610ba25a`.
- Speaker remains exactly **`Volume: 0.95 [MUTED]`**. It was not unmuted in this
  resumed attempt because the crash occurred first.
- Exact game cgroup empty; no new game/wrapper process, no bench pad, no active
  game/acquisition unit, no active host-session record. Input observer reports
  the original P1, source ownership, composites and management policy restored.
- No unit reset, recovery-journal edit or korrid restart occurred.
- An unrelated failed `korri-reach-cli.service` was visible in the final audit;
  its command is `reach-spike-webrtc --help`. It was not modified or reset.

The deliberate personal pin remains installed/enabled. The parent still owns
removing the test composition at Land. The old poisoned caches remain preserved
aside, as requested; there is no claim that the new cache is safe for gameplay.

| Acceptance item | Status |
|---|---|
| Real library launch with Vulkan / Turnip 25.3.2 | **Verified**, through title and save-loading screen, then Cemu SIGTRAP |
| Gamescope remains on system Mesa 26.2.3 | **Verified** by actual driver mappings and absent ICD overrides |
| Median ≥40, p10 ≥35 | **Not achieved**; crash before warmup |
| Audio audible, Cemu stream verified | **Not re-tested**; prior stream proof exists, prior capture silent |
| New in-game save survives relaunch under saveRoot | **Blocked**, no new save attempted |
| 15-minute crash-free/thermally stable soak | **Not run**, required crash stop |
| Launch settings, modifier bytes, speaker, P1 restored; no test process remains | **Verified** |

## Focused checks and evidence

The new ARM-only check first failed against the previous actual ARM package
with `aarch64 Cemu must pin its Turnip ICD`, then passed against the new package.
Both architectures' final focused checks passed:

```sh
nix build --no-link .#checks.aarch64-linux.korri-cemu-package \
  .#checks.aarch64-linux.korri-cemu-admission /tmp/cemu-odin-test#packages.aarch64-linux.default \
  --max-jobs 0 --builders 'ssh-ng://<builder-login> aarch64-linux /etc/ssh/ssh_host_ed25519_key 2 1 big-parallel,benchmark - -'
nix build --no-link .#checks.x86_64-linux.korri-cemu-package \
  .#checks.x86_64-linux.korri-cemu-admission --builders '' --max-jobs 1
```

These include strict TypeScript/callback tests, ShellCheck, the new driver
selection check, real Cemu CLI/Xvfb/native-seed preservation, and actual Core
admission/execution tests. Python syntax and `git diff --check` passed. The
commit hook's secret scan passed. No full repository suite/verification ran.
Setup scripts stopped safely on library-field-order and missing optional Debug
node assumptions; those scripts were corrected operationally, not turned into
product fallback/schema changes. Only the single game launch above occurred.

Private zao evidence: **`/tmp/cemu-odin-evidence/`**, 0700, now about 9.1 GiB
including the earlier and new cores. New files use prefix `turnip2532-`;
`turnip2532/` contains copied device artifacts, process environments/mappings,
raw bench report/Present files, screenshots, and restoration proofs.
Most useful: `turnip2532-backtrace.txt`, `turnip2532-detail.txt`,
`turnip2532-coredump-info.txt`, `turnip2532-final-audit.txt`,
`turnip2532/baseline/{cemu.log,env-*.json,result.json,bench/cleanup.json}`,
`turnip2532-finish.log`, `turnip2532-x86-checks.log`, and `turnip2532.narinfo`.
Device evidence: `/var/lib/korri/cemu-bench-staging/turnip2532/`.

Follow-up for the parent: investigate Cemu's continued-draw descriptor-state
assertion before authorizing more launches. The pin adds an older driver closure
and requires Adreno for this aarch64 Vulkan path, since it exposes only freedreno.
It does not solve this new crash, audio, save persistence, thermal safety or
performance acceptance. The promised patched 26.2.x replacement remains separate.

# Odin Cemu first light — 2026-10-22 campaign

**BotW reaches its title and save-selection screens through korrid with Vulkan.
Gameplay qualification is blocked by a reproducible Mesa 26.2.3 IR3 compiler
crash on `nir_op_fmadz`. No gameplay FPS target or soak passed.**

Logs cross midnight into 2026-10-23 UTC. No core, system, firmware, bootloader,
InputPlumber policy or Mini V2 change was made. The supervisor approved the
catalog admission, temporary BotW-only modifier, temporary audio unmute, and
six bounded graphics diagnostic launches described below.

## Source, installation and trust

Branch: `feat/cemu-odin`, starting at `4bfd286c752e3971200bade474e0923913fede88`.

| Fix commit | Change | Real failure/proof |
|---|---|---|
| `c8a3c91` | Clear inherited setgid on private pack staging before copying; preserve writable native data without requesting setid permissions | Original game unit: `cp: setting permissions .../downloadedGraphicPacks: Operation not permitted`. Fresh seeding subsequently succeeded under the real hardened unit. |
| `62f3d36` | Native seed selects Cubeb (`Audio/api=3`) and `TVDevice=default` | Empty TV device means disabled output in Cemu, not default output. A Cemu PipeWire stream subsequently appeared; non-silent playback is still unproved. |
| `95188bc` | Select `GDK_BACKEND=x11` only when Gamescope sets `GAMESCOPE_WAYLAND_DISPLAY` | Nested native Wayland crashed in `wl_proxy_marshal_flags` / `VulkanCanvas`. The rebuilt nested X11 path renders and produces Present events. Direct Wayland selection remains unchanged. |

The production source remains `@korri:cemu`. The supervisor explicitly required
the established **test-only personal publisher route**, because the
`korri-plugins-1` CI secret is unavailable locally. No official publisher key
was sought or used. Scratch flake `/tmp/cemu-odin-test/flake.nix` consumes this
publisher flake, uses its locked Core builder and Cemu package, copies
`plugins/cemu/plugin.ts` with exactly `s/@korri:/@<publisher>:/g`, and calls
`mkPlugin` with `publisher.namespace = "@<publisher>"`. The manifest is built
normally, never rewritten. Final tested source: `95188bc`.
Installed source bytes were compared against that exact substitution.

| Installed artifact | Value |
|---|---|
| Test plugin / runner | `@<publisher>:cemu` / `@<publisher>:cemu/cemu` |
| Final plugin | `/nix/store/w9dpchdmdpx3c0yfns2hd0hb5ypd4n6i-korri-plugin` |
| Final Cemu | `/nix/store/ygfpc2z5in3p7ljfz8xdsxbfknbyxpxm-cemu-0-unstable-2026-10-22-29f2f1f` |
| Cemu source | `29f2f1fae4631e2317977debd9eacd55cc28dd7d` |
| Unchanged target bundle | `/nix/store/983r04y6kbmmygj6gwqi3f9hbniqzyaz-korri-bundle-0.0.0` |
| Read-only Core reference | `4e34b8a9e` |
| Exact approval | `a36035b351df871a1b380ff9c6230d2cbc13fb2839ab5e0aa16225e5a9fa3764` |
| Bound test cache | `file:///var/lib/korri-private-cache/cache` |
| Initial plugin, before fixes | `/nix/store/69604m1iyxhhjdracmhhnh6w6zym3xia-korri-plugin` |
| Pack-seeding-only fix test | `/nix/store/39vrnnq9g5b7h1qmf8d61n45nq6prsx9-korri-plugin` |

ARM builds ran on yari/fuji through zao's Nix daemon, never on Odin. Closures
were recursively signed on zao with its existing transport key and copied
with `nix copy`. The private file cache was signed with the existing personal
publisher key. Secrets stayed on zao and were never printed or transferred.
Normal `korri-plugin inspect`, exact-approval `install`/`update`, and `enable`
passed. Publisher configuration retained SHA-256
`c4fb42826ffdd99c93c96c7df8818890bc6fc6cfd075af65c6a889754df4acb3`.
Final device policy still has `require-sigs=true`, `max-jobs=0`, empty builders,
and `fallback=false`. Nothing was pushed, merged or published. The test plugin
is left enabled; the parent plans to remove the test installation at Land.

## Library, launch chain and native data

The enabled declaration supplied Wii U identification. Supported admission was:

```sh
systemctl stop korrid-control.socket korrid.service
runuser -u korrid -- env KORRID_STORAGE_ROOT=/var/lib/korri \
  KORRID_PRIVATE_STATE_ROOT=/var/lib/korrid \
  /nix/store/nvs92ijqg09cranbzg1d0f2whybvvr32-korrid-0.0.0/bin/korrid \
  catalog pair /var/lib/korri/games/wiiu wiiu
systemctl start korrid-control.socket korrid.service
```

Operational deviation: the initial stop named only `korrid`; the active control
socket reactivated it while the offline pair hashed the WUA. Both socket and
service were then stopped. The pair completed with one added game, zero
diagnostics, and `13660330872` hashed bytes. Both units were restored normally;
no recovery reset or journal edit occurred. This socket-activation race needs a
Core follow-up. The actual game ID is
`the-legend-of-zelda-breath-of-the-wild-usa-dlc-v208`.

The initial device and library carried no Gamescope modifier despite
`KORRID_INITIAL_MODIFIERS` and ADR 0008. Unwrapped Cemu visibly reached BotW's
Vulkan title screen. Its native Wayland rendering is outside the bench's X11
Present observer, so those observer failures are **not Cemu launch failures**.
With explicit supervisor approval, only BotW's existing library item temporarily
received `@korri:gamescope/gamescope: { enabled: true }`. Original bytes and the
temporary hash guarded restoration. This default-wrapping discrepancy also needs
a Core follow-up; the plugin does not hardcode a compositor.

Actual wrapped chain: korrid `plugin-launch` → Gamescope → gamescopereaper →
Cemu, in the exact `korri-game-<launchId>.service`. Cemu receives
`-f -g <WUA> --mlc <saveRoot>/mlc01`; the final process has
`GDK_BACKEND=x11`, `WAYLAND_DISPLAY=gamescope-0`, and Gamescope's `DISPLAY`.
**Bubblewrap not observed; core does not implement ADR 0015.**
No ordinary launch showed the suspected 25-second portal stall after startup
worked; no portal service configuration or Gamescope package was changed.

Cemu log excerpts from the real library route:

```text
Init Cemu 29f2f1f
------- Init Vulkan graphics backend -------
Using GPU: Turnip Adreno (TM) 740
Driver version: Mesa 26.2.3
gameprofile path: gameProfiles/default/00050000101c9400.ini
CPU-Mode: Multi-core recompiler
Full sync at GX2DrawDone: false
Async compile: true
Accurate barriers are disabled!
Set vsync frequency to 45 (graphic pack .../Mods/FPS++)
Activate graphic pack: .../Mods/FPS++ [Presets: Normal Settings,45FPS Limit,40FPS (ideal for 240/120/60Hz displays),...]
Activate graphic pack: .../Graphics [Presets: 16:9 (Default),1280x720 (HD, Default),...]
Cubeb: available
```

The FPS++ normal preset actually selects **45**, not 40, despite retaining the
requested advanced Framerate Limit value. The log makes this distinction
explicit. Native test settings also had `VSync=0`, `GX2DrawdoneSync=false`,
`vkAccurateBarriers=false`, and `AsyncCompile=true`. No game tuning was shipped
as a plugin default. A bundled Graphics pack also logged an unknown preset
variable in a custom shader; it was not silently patched.

The staged 54 save files were copied under the actual account's
`<saveRoot>/mlc01/usr/save/00050000/101c9400`. Imported-subtree ACLs were corrected
to the existing korrid/korri sharing policy after preserving source ACLs caused
the first permission failure. All 54 file hashes matched the staging manifest.
Core's existing first-sync capture admitted these native folders into history;
subsequent diagnostic resets used `app.saves.restore`, not fabricated records.
Baseline snapshot:
`sha256:0f0d9c7032899fefee5d8915d359b12d35401c7b86b99642509e2c6e04abfb5a`.

**Save correction:** uppercase `101C9400 (not present)` in Cemu's diagnostic
log is not its actual lowercase save lookup. No case rename was made.
The earlier staged slot-0 preview showed a shrine, but the actual Continue menu
selects the newest **Zora's Domain, 02/03/2024 19:04** save. The final screenshots
prove save recognition and its load confirmation, not arrival at a shrine or
successful gameplay. A new in-game save/relaunch proof was blocked by the crash.

Cemu's own input UI generated both controller XML files in the test account.
The bench installs the P2 template and restores the P1 file, including metadata.
P1 UUID: `0_030082db5e0400008e02000014010000`.
P2 UUID: `0_0300c2da5e0400008e02000014010000`.
Both display as `Xbox 360 Controller` through `SDLController`; emulated type is
`Wii U GamePad`. The scripted BTN_EAST input visibly advances Continue → save
selection → load confirmation. P2 device access and profile loading therefore
work. No profile was added to the shipped plugin. Initial setup delays came
from X11 dialog focus/close automation, not inaccessible controller devices.

## Every bench attempt

All launches used the prebuilt bench
`/nix/store/ycx1s593595i2c2hyax3l5i58d6iqcw8-korri-cemu-bench-0.1.0`.
Only `controller-setup-02` produced a nonzero raw FPS summary: **one second of
wrapped title/UI presentations**, not a qualified gameplay sample. Zero-valued
failure placeholders in other `fps.json` files are not reported as real FPS.
Temperatures below are from the bench's telemetry only; `—` means no collected
sample. Telemetry starts after the input script, so long setup/input periods
are not thermally covered.

Unless noted: 720p, FPS++ normal 45, advanced limit 40, async on, accurate barriers
off. Game-layer `cpu.min=100` and `gpu.min=100` were authored through the
revision-checked launch-settings RPC from `unwrapped-03` onward. Launches reported
no limit warnings; device facts enumerate the real GPU frequency steps.

| Output folder (under device staging) | Purpose / outcome | median / p10 / p1 FPS | Peak sampled °C |
|---|---|---:|---:|
| `botw-unwrapped-01` | Defaults; imported ACL permission failure | — | — |
| `botw-unwrapped-02` | Defaults; pack copy setgid permission failure | — | — |
| `botw-unwrapped-03` | Title rendered; native Wayland observer unsupported, 1+5 s | — | 76.0 |
| `botw-unwrapped-04` | Visible title; same observer limit, 45+5 s | — | 86.4 |
| `botw-wrapped-setup-01` | Native Wayland VulkanCanvas signal 11 | — | — |
| `botw-unwrapped-audio-05` | Fresh seeding fix works; audio stream exists; Wayland observer unsupported, 35+5 s | — | 92.7 |
| `botw-controller-setup-02` | 600 s UI setup, then 1+1 s; failed P2 event check (script had only SYN) | 45 / 45 / 45 **UI only** | 74.4 |
| `botw-controller-setup-03` | UI automation ended Cemu; exact bench interruption/cleanup | — | — |
| `botw-controller-setup-04` | Native P1/P2 files successfully saved; intentionally interrupted and P1 restored | — | — |
| `botw-720p-baseline` | Planned 100+180 s; IR3 crash before warmup | — | — |
| `diagnose-repeat/bench` | Same save/settings; cached pipeline compilation crash | — | — |
| `diagnose-async-off/bench` | Only AsyncCompile=false; same crash | — | — |
| `diagnose-accurate-on/bench` | Only accurate barriers=true; same crash | — | — |
| `diagnose-540p/bench` | Only Resolution=960x540; same crash | — | — |
| `diagnose-fresh-repeat/bench` | Native pipeline + driver caches preserved/moved; live compilation crash | — | — |
| `diagnose-fresh-async-off/bench` | Fresh caches and AsyncCompile=false; same crash | — | — |

The six diagnostic launches planned 25+10 s after the same input script. All
failed before that measurement. `Debug/CrashDumpUnix=1` was common crash
instrumentation, then restored. The original cache set was restored byte-for-byte;
newly generated sets remain preserved under the two fresh-run folders. The
restored pipeline cache is **known to reproduce the crash during startup**.
`TU_DEBUG` was unset in every captured renderer environment. Mesa's
`parse_debug_string` returns zero flags for both unset and empty strings, so
there was no nonempty debug override to clear and no extra launch for that case.

No IPO/PIE A/B, CPU affinity change, barrier workaround or package variant was
attempted around the compiler failure. The 92.7 °C title-run sensor peak matters:
there is no thermal qualification, and no claim that a 15-minute run would avoid
collapse. No cooling/device configuration was changed.

## Graphics diagnosis and upstream source check

**Verified:** fresh live compilation and cached startup compilation fail on the
same Mesa pipeline BLAKE3:

```text
026211ce39d10e5e02021680ebff7da347ac4ee27a5064daeacd045d15efb127
```

Both host-GDB core examinations resolve the failing ALU instruction to
`nir_op_fmadz`, bit size 32, `MESA_SHADER_VERTEX`. The useful stack is:

```text
unlink_block / ralloc_free                 src/util/ralloc.c:297
ir3_context_error("Unhandled ALU op: %s")   src/freedreno/ir3/ir3_context.c:349
emit_alu                                  src/freedreno/ir3/ir3_compiler_nir.c:1143
ir3_compile_shader_nir
compile_variant / create_variant
tu_shader_create / tu_compile_shaders
tu_pipeline_builder_compile_shaders
tu_CreateGraphicsPipelines
PipelineCompiler::Compile
compilePipeline_thread                    fresh cache
# or VulkanPipelineStableCache::CompilerThread with the retained pipeline cache
```

Exact Mesa output:
`/nix/store/nc0xr281k1wwf7g5f06vkj4l5xcyhs0s-mesa-26.2.3`.
Matching prebuilt debug output, fetched **on zao only**:
`/nix/store/ackk3ly8i3y96x81rp7rxm8h6gm17ggr-mesa-26.2.3-debug`.
No driver was installed or rebuilt. Core dumps were enabled through Cemu's
native test-account setting, not a system/unit policy change. GDB warns about
libthread_db, but reads AArch64 registers, stack, Mesa DWARF, ALU and pipeline
state from the actual core. An ARM Mesa sysroot avoids host GLX library confusion.

This is **not a match for the observed mechanism in
[Cemu #2029](https://github.com/cemu-project/Cemu/issues/2029)**. That issue is
an unmatched fragment input on Qualcomm's Windows driver with Error -13.
Here the compiler rejects a vertex ALU operation. In the captured failing
pipeline, fragment input mask `0x1ff00000000` is a subset of vertex output mask
`0x1ff00000001`; no missing producer slot is visible in that NIR interface.
This does not establish that every other BotW shader is free of #2029.
No `VK_ERROR_DEVICE_LOST` or command-buffer Error -4 appeared. Dmesg contains
pre-existing ARM-SMMU context faults at about 0.75 seconds after boot, not new
GPU faults at the test times. No diagnostic avoided the compiler crash.

GitLab raw/API requests returned an Anubis HTML challenge, not source. The
source-only check therefore used the public `chaotic-cx/mesa-mirror` and pinned
full commit IDs; canonical upstream links below come from its commit messages.
The three 26.2.3 files were byte-compared against the actual Nix Mesa source and
all matched.

| Requested source | Exact checked commit | IR3 result |
|---|---|---|
| `mesa-26.2.3` | `31e9a6b2e95e30d84bf3177d1f497d063e59b6b2` | `has_fmulz=true`, `lower_fmulz_with_abs_min=true`; fmad handler, no fmadz handler |
| 26.2 stable branch (actual branch name `26.2`, not `mesa-26.2.x`) | `f25a43cbecf89787409c83bfb96c6b465353155e` | Same relevant result |
| `main` | `dbf73b1dca74b6f692675f1c234070db2441854c` | Same relevant result |

Checked `ir3_compiler.c`, `ir3_nir.c`, and `ir3_compiler_nir.c` at each ref, plus
file histories. There is no explicit `lower_fmadz` option/handler in these IR3
files. This NIR generation uses `float_mul_add{16,32,64}` options; IR3 advertises
`nir_float_muladd_support_has_fmad | nir_float_muladd_support_fuse`.

Relevant history, **not a claimed fix for this crash**:

- [9c6183604f5a](https://gitlab.freedesktop.org/mesa/mesa/-/commit/9c6183604f5ab67b1917473dd59fe98d4943fdef),
  [MR 31479](https://gitlab.freedesktop.org/mesa/mesa/-/merge_requests/31479):
  adds `lower_fmulz_with_abs_min` and IR3's `has_fmulz` setting. The message
  describes fmulz/ffmaz lowering. Present in checked **25.3.0**; absent in
  checked **25.2.8**.
- [acad18d97e83](https://gitlab.freedesktop.org/mesa/mesa/-/commit/acad18d97e83901002d755715fdfe202a80e0115),
  [MR 41165](https://gitlab.freedesktop.org/mesa/mesa/-/merge_requests/41165):
  ports IR3 to `nir_op_fmad`, adds the float-mul-add capability flags, and
  changes late algebraic handling. Present in checked **26.2.0**; those flags
  are absent in checked **26.1.0**. The patch adds `fmad`, not `fmadz`.

**No fmadz support/lowering fix or release carrying such a fix was found in
the checked heads.** 26.2.4 and 26.2.5 retain the same relevant IR3 options.
This is not proof that no unmerged MR exists, nor a hardware test of newer Mesa.
Do not recommend an upgrade as a verified fix. A separate Mesa investigation
must establish correct lowering and safe compiler-error handling before further
performance qualification; no such change belongs in this plugin stage.

## Audio, restoration and acceptance

A live `Cemu Cubeb` PipeWire output stream was linked to the Speaker playback
sink. That sink initially reported `Volume: 0.95 [MUTED]`. The supervisor
approved temporary unmute; volume was not changed or quantized. A 144000-frame,
48 kHz stereo float monitor capture contained **288000 samples, peak 0.0,
RMS 0.0**. This proves neither audible sound nor non-silent Cemu output.
The capture tool returned 1 with its complete sample count and empty stderr;
that fact is retained, not hidden. Mute/volume were restored and the final
`wpctl get-volume` output exactly matches the original. Audio needs follow-up.

Restoration proof (`restoration.json`, `botw-settings-restored.json`):

- BotW modifier bytes restored to the saved pre-modifier bytes under the hash
  guard, before CPU/GPU RPC unsets.
- Game `cpu.min` / `gpu.min` removed through the revision-checked RPC; resolved
  values match the pre-test snapshot: CPU/GPU **0–100**, device-default source,
  governor `schedutil`.
- Native diagnostic XML restored; P1 controller SHA-256
  `738dffbb744252cd1a089411cc54640626e7157984fa263db3e7b697610ba25a` restored.
- Both original native cache files restored by hash; generated diagnostic
  caches kept separately. No workaround remains enabled.
- Empty exact game cgroups, no game/acquisition units, no failed units, no
  Cemu/Gamescope/bench/observer/recording process, no bench pad, empty active
  host-session directory. Original CompositeDevice0, built-in sources and P1
  state restored; ManageAllDevices stayed false.
- Same boot ID `c41b371b-88de-4b62-bcd7-aadc34f61d81`, same generation-8 system
  and bundle. No recovery journal edit, unit reset, recovery restart, system
  update, boot/firmware write or other USB-device operation occurred.

| Acceptance | Result |
|---|---|
| BotW launches from library through real korrid with Vulkan | **Yes**, title/save menu; approved personal test composition of the production source |
| Median ≥40 FPS; p10 ≥35 | **No** qualified gameplay sample |
| Audio audible and Cemu stream in PipeWire | **No**; stream verified, capture silent, not independently heard |
| New in-game save survives relaunch under saveRoot | **No**; imported save visible, new-save test blocked |
| 15-minute soak without crash/thermal collapse | **Not run** |
| Launch settings restored to device defaults | **Yes**, RPC and exact-state proofs |

## Checks and evidence

Focused final checks passed:

```sh
nix build --no-link .#checks.x86_64-linux.korri-cemu-package \
  .#checks.x86_64-linux.korri-cemu-admission --builders '' --max-jobs 1
```

These include strict TypeScript checking, callback tests, installed-wrapper
ShellCheck, real Cemu/Xvfb pack loading/seed preservation, and actual Core
admission/execution tests. Final installed-package runtime check also passed
outside Nix with `--setgid-account`; it exercises inherited setgid and the
Gamescope/X11 environment branch. Python compilation and `git diff --check`
passed. ShellCheck passed with the template shebang rendered. The original
setgid regression failed on real chmod syscalls before the fix. An initial
attempt to set setgid inside the Nix check failed because Nix itself forbids
it; the explicit outside-sandbox mode addresses that test limitation. No full
repository verification or full test suite was run.

Private evidence on zao: **`/tmp/cemu-odin-evidence/`** (0700). It contains the
scratch flake/lock, exact inspections/install receipts, build/check logs, native
save hashes, source captures, GDB commands and both cores, symbolicated traces,
raw bench reports/Present/telemetry, settings and restoration proofs. It uses
about 5.7 GiB, mostly private cores; none of those cores or game assets is
committed or published. Device evidence remains under
`/var/lib/korri/cemu-bench-staging/`.

Useful screenshots:

- `unwrapped-04.png`: actual unwrapped Vulkan title.
- `controller04-after-auto.png`: Cemu-generated native mapping UI.
- `device/diagnose-fresh-repeat/screen-20.png`: staged Zora's Domain save selected.
- `device/diagnose-fresh-repeat/screen-22.png`: load confirmation through bench P2.

Best crash proofs: `core-fresh-detail.txt`, `core-repeat-detail.txt`,
`botw-720p-baseline-cemu-crash.log`, `botw-720p-baseline-dmesg.txt`,
`device/diagnose-*/{cemu.log,result.json,renderer-env.json,bench/cleanup.json}`.
Source comparison and upstream history: `mesa-upstream/`.

Follow-ups for the parent, not filed here: high priority Mesa fmadz/compiler
error-path failure; Core default Gamescope admission and offline catalog socket
activation; silent audio. CPU affinity/schema decisions remain unmeasured and
were not built. Fixing the graphics stack costs a separately approved stage;
it does not itself establish audio, saves, thermal safety or the FPS target.

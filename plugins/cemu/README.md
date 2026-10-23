# Cemu

`@korri:cemu` supplies runner `@korri:cemu/cemu` for Wii U content (`wua`,
`wud`, `wux`, `rpx`, `wuhb`). It contains no games, console keys or firmware.
Build only on build hosts. Devices receive prebuilt Nix closures.

## Source and build choices (2026-10-22)

Cemu main is pinned to `29f2f1fae4631e2317977debd9eacd55cc28dd7d`.
[Build check 39858960377](https://github.com/cemu-project/Cemu/actions/runs/39858960377)
passed both `build-ubuntu-arm` (job `120104375818`) and
`build-appimage-arm` (job `120113069053`). This was the newest
main commit with passing ARM jobs when selected. The previous successful
`934329f` was replaced when this run completed during packaging.

The direct clang derivation fetches submodules. It does not override nixpkgs
Cemu or use `wrapGAppsHook3`. It keeps upstream's bundled imgui and Cubeb.
Removing `find_package(cubeb)` forces the bundled audio implementation.
The install gate requires nonempty compiled `cubeb_pulse.c.o` and
`cubeb_alsa.c.o` files, and rejects dynamic `libcubeb` linkage.

| Dependency | Version |
|---|---|
| SDL3 | **3.4.18**, pinned locally; the lock has 3.2.26 |
| fmt | **12.1.0**, pinned locally because the publisher lock has 12.0.0 |
| wxWidgets (`wxwidgets_3_3`) | 3.3.1 |
| glslang | 16.0.0 |
| SPIRV-Tools | 1.4.328.0 |
| clang / LLVM / lld | 21.1.2 |

Recipes reviewed: PockNix `packages/shared/cemu/PKGBUILD` at `aa20e2f`,
Batocera `package/batocera/emulators/cemu/cemu.mk` at `3310f3b8`, and the May
nix-on-rocks package and performance audit. No ROCKNIX patches are carried.
No glm target rename or `FMT_HEADER_ONLY` removal was needed to configure.
Release IPO stays **ON**, as upstream sets it. LLVM archiver and ranlib are
explicit: the first build failed with `CMAKE_CXX_COMPILER_AR-NOTFOUND`.
The unpatched x86 build then failed at `SDL_HINT_JOYSTICK_HIDAPI_SWITCH2`,
which SDL documents as available since 3.4.0. The local SDL 3.4.18 pin fixes
the dependency instead of deleting controller support or adding a source patch.
That SDL update retains nixpkgs' Zenity path substitutions at the new native
source location and adds its new XTEST dependency (`libXtst`).
The executable links with **Nix-wrapped lld** (`llvmPackages.bintools`).
A raw lld build linked but failed real `cemu --help` with missing Boost;
the wrapped linker retains the Nix runtime search paths. A separate Boost
link-and-execute probe confirmed this fix before rebuilding Cemu. There is no `-no-pie` override or hardening
removal. No CPU affinity, device profile or game-specific performance setting
is introduced. The Cemu-scoped aarch64 Turnip build is described below.

## Cemu-scoped patched Turnip

On aarch64 only, `bin/cemu` sets `VK_DRIVER_FILES` and the older loader alias
`VK_ICD_FILENAMES` to the freedreno ICD from the plugin's **Mesa 26.2.5** build
in `turnip.nix`. This replaces the earlier temporary 25.3.2 pin. Cemu and the
selected driver retain the held package set to isolate the driver change. A separate current-pin build checks build compatibility only.
The build enables only
Turnip with the Linux MSM kernel driver and X11/Wayland presentation. It disables
Gallium, OpenGL, EGL, GBM, LLVM, OpenCL, video codecs, layers and optional tools.
Other architectures keep normal ICD selection. No system Mesa overlay,
Gamescope change, OpenGL selection change, or other plugin change is involved.
The aarch64 Vulkan path still requires an Adreno GPU with the MSM driver.

[The patch](patches/mesa-26.2-ir3-fmadz.patch) makes the final late-algebraic
cleanup in `ir3_context_init` run to a fixed point. That cleanup follows
`ir3_nir_lower_imul` and normal algebraic, which can recover `fmulz` from its
abs-min lowering. One late pass can re-fuse it to `fmadz`; a further pass must
lower that replacement before instruction selection. The main variant loop
already iterates, but this later call did not.

Odin's unpatched Mesa 26.2.3 rejects a 32-bit vertex `fmadz`, then faults in
`ir3_context_error` → `ralloc_free`. Fresh and cached failures share pipeline
BLAKE3 `026211ce39d10e5e02021680ebff7da347ac4ee27a5064daeacd045d15efb127`.
The patch reuses the existing NIR abs-min select; it does not fix the separate
compiler-error cleanup crash. It is **not submitted upstream**. See
[the upstream draft](patches/mesa-26.2-ir3-fmadz.upstream.md) and
[the gameplay-gated phase-2 campaign](bench/devices/odin2portal-turnip262-phase2-2026-10-23.md)
for validation and limits. Existing IR3 disassembly/delay tests run on the builder.
The Cemu package check verifies the exact patched ICD, its actual library, and
byte-identical installed patch evidence, not merely a Mesa version string.

The gameplay-gated 25.3.2 [baseline](bench/devices/odin2portal-gameplay-gate-2026-10-23.md)
measured 37 / 37 / 36 FPS with native `AsyncCompile=false`. The older ungated
baseline and soak are not comparable to gameplay-gated measurements.
Async on hit Cemu's separate `activeVertexDS` assertion. Fresh accounts now seed
`Graphic/AsyncCompile=false` in Cemu's own settings file; existing settings remain
untouched. Its cost is synchronous compilation stalls. This driver patch alone
is not proof of performance, audio, new-save persistence or thermal safety.

Phase 2 completed three gated async-off samples at median 40 FPS versus 37 FPS
for the same-session shipped build. Two async-on samples reached 39 FPS with no
draw-state assertion. The owner stopped before the third async-on sample and
the soak. **Owner decision (2026-10-23): ship the patched 26.2.5 Turnip with
async off as the default, without a soak.** Long-session stability with this
driver is therefore not qualified. Async on remains a per-account choice in
Cemu's own settings. The upstream regression unit test and MR remain pending
(korri-os/korri#211).

## Native files, not another configuration schema

Cemu `src/gui/wxgui/CemuApp.cpp:164-169` uses XDG data/config/cache paths;
`src/config/LaunchSettings.cpp:68` provides `--mlc`, not a user-data option.
The declaration sets HOME and the native `.config`, `.local/share`, `.cache`
XDG directories under korrid's `accountRoot`. It launches:

```text
cemu -f -g <contentPath> --mlc <saveRoot>/mlc01
```

Cemu's native `mlc01/usr/save` folder is declared as the `saves` save location.
This retains console account metadata as well as title saves. The MLC is
per-game, because korrid supplies a per-game save root. Installed updates/DLC
inside that MLC are not save-synced. Native user data and shader caches stay
under the account root. There is no migration of existing desktop/ROCKNIX data.
Console dumps, when needed, use upstream's native account data paths
(`keys.txt`, `otp.bin`, `seeprom.bin` directly in `.local/share/Cemu`). The
ROCKNIX `keys/` and `online/` path patch is not used.
Paths are literal argv entries, not shell expressions. Provider references,
emulator cores and unsupported Korri overrides fail rather than being ignored.
CPU/GPU launch limits remain Core's responsibility (ADRs 0018–0020).

The wrapper seeds the shipped native `settings.xml` only when absent, with
Vulkan (`Graphic/api=1`), fullscreen and update checks disabled. It also seeds
`Graphic/AsyncCompile=false` as a temporary workaround for Cemu 29f2f1f's
`VulkanRenderer::draw_execute` null `activeVertexDS` assertion during BotW
save loading with async compilation enabled. The Odin async-off campaign above
verified gameplay with this workaround. Its cost is synchronous shader/pipeline
compilation stalls; isolated soak hitches reached 4 FPS. Remove the workaround
when the draw-state race is fixed and verified. It never rewrites existing
settings, including an existing person's async-compilation choice. `-f` remains the requested launch behavior even
if a person changes the native fullscreen preference. The wrapper exposes
Vulkan, Pulse and ALSA libraries through `LD_LIBRARY_PATH`, then execs Cemu.
The fresh native seed selects Cubeb (`Audio/api=3`) and its `default` TV
output. Omitting the TV device means disabled audio in Cemu, not the default
output: the first Odin title launch had no PipeWire audio stream despite
`Cubeb: available`. Existing native settings remain untouched.

When Gamescope sets its native `GAMESCOPE_WAYLAND_DISPLAY`, the wrapper selects
`GDK_BACKEND=x11`. Cemu's `VulkanCanvas` crashed in `wl_proxy_marshal_flags`
before renderer initialization against Gamescope 3.16.18's exposed Wayland
server on Odin. The nested path must use Gamescope's Xwayland; a direct launch
keeps Cemu's normal backend selection. This is not a Vulkan device-loss fix.

Upstream's Linux data path is wxWidgets `GetDataDir()`. wxWidgets 3.3.1's
`src/unix/stdpaths.cpp` derives the prefix from `/proc/self/exe`'s `/bin/`
component and appends `/share/Cemu`. The real executable stays in `$out/bin`.
The wrapper also sets wxWidgets' supported `WX_CEMU_DATA_DIR` override to
`$out/share/Cemu`, so inherited desktop overrides cannot hide packaged data.
Installation fails without default `.ini` game profiles or `CafeCn.ttf`.

## Offline graphic packs

The package bundles `Github989/graphicPacks989.zip` (CC0-1.0), release commit
`975f3759d7837da5a374150347d3202360b13ca3`, including BotW packs. The license
is installed separately because the release ZIP omits it. No pack is enabled
or tuned on the person's behalf.

`graphic-packs-native-aspect.patch` adds the optional Aspect Ratio preset
**31:27 (1240x1080 handheld)** and matching 1240x1080, 1028x896, 827x720,
620x540 and 413x360 Resolution presets to BotW's native `Graphics/rules.txt`.
The build applies the patch without fuzz. The pattern comes from that file's
4:3 and 5:4 aspect presets and aspect-gated Resolution presets in
[Github989 source](https://github.com/cemu-project/cemu_graphic_packs/blob/975f3759d7837da5a374150347d3202360b13ca3/src/BreathOfTheWild/Graphics/rules.txt).
Like those presets, it retains `$gameWidth=1280` / `$gameHeight=720` (the
original game texture dimensions) and exposes Square HUD Mode through
`$showSquareHUDOption=1`. It does not select the experimental square-HUD
fix or change any default. The pack stays 16:9 by default; the player selects
aspect, resolution and HUD mode through Cemu's own graphic-pack preset entries
in `settings.xml`. The patched data retains upstream's CC0-1.0 license.
A package check verifies all five resolutions, their aspect conditions, and
unchanged defaults. Existing account-local pack trees are still never
silently replaced: an operator must explicitly update a previously seeded
copy before these additional choices appear. Cemu's manual pack updater can
replace this patched file with upstream data and remove these local choices;
retain the packaged revision or explicitly reapply the patch after an update.

`GraphicPack2.cpp:96-111` scans `GetUserDataPath("graphicPacks")` recursively.
On first launch the wrapper copies the bundle to that native directory,
including `downloadedGraphicPacks/version.txt`. It does not symlink into the
store: Cemu's explicit updater replaces `downloadedGraphicPacks`. Existing
pack trees are left unchanged, including on future package upgrades. This
costs one writable copy per account and requires an explicit update to move
an already-seeded account to a newer pack release.

Core's account directories inherit setgid. Before seeding packs, the wrapper
clears that bit on its private staging directory and copies without preserving
store modes. Otherwise GNU cp requests setgid permissions and the game unit's
`RestrictSUIDSGID` rejects startup with `cp: setting permissions: Operation not
permitted`. Access ACLs inherited from the account remain intact. The runtime
check also accepts `--setgid-account` outside Nix's build sandbox (which itself
forbids setting that bit); it checks actual chmod syscalls and native pack reads.

**Correction to the May assumption:** `gp_download=false` does not prevent
manual downloads. At this pin `wxCemuConfig.h:102` says this field is unused;
it formerly tracked the Getting Started dialog. We ship the harmless false
value as requested, not as a network policy. `main.cpp:133` loads local packs.
The only updater entry points are button callbacks in
`GettingStartedDialog.cpp:270-278` and `GraphicPacksWindow2.cpp:641-660`;
`DownloadGraphicPacksWindow::ShowModal` starts its download thread. There is
no automatic pack download/check at launch. Explicit user-initiated downloads
remain available, as agreed with the supervisor. No updater patch is needed.

## File-cache shutdown fix

`filecache-shutdown.patch` fixes an upstream lost wakeup in the file-cache
writer. A fast `--help` exit could send the shutdown notification before the
worker waited, then block forever joining that worker. The patch changes the
shutdown flag under the queue mutex and uses a shutdown-aware wait predicate.
The build compiles the actual writer with a gated worker to force that ordering;
the package check also runs 20 real `--help` exits with the existing 15-second
limit. This source fix has no device qualification; earlier hardware results
predate it. The local source delta is the patch file beside `package.nix`.

## Checks and installation boundary

```sh
nix build --no-link .#packages.aarch64-linux.cemu .#packages.aarch64-linux.korri-plugin-cemu
nix build --no-link .#checks.aarch64-linux.korri-cemu-package .#checks.aarch64-linux.korri-cemu-admission
nix build --no-link .#checks.x86_64-linux.korri-cemu-package .#checks.x86_64-linux.korri-cemu-admission
```

The configured Nix daemon dispatches ARM builds to Fuji; no device builds.
The package check typechecks against Core's generated treaty, tests literal
paths and refusals, lints the installed wrapper, and runs real Cemu under Xvfb
with strace to prove offline pack loading and preservation of native edits.
The admission check uses Core's actual declaration evaluator and sandbox
executor with two supplied account roots. Its `seed` call is a sandboxed
admission test, not a device installation route.

Short build proofs remain under `$out/nix-support/cemu-build/`: compiled audio
objects, ELF linkage/type, asset counts, resource assertions and compiler version.
Full asset lists, `compile_commands.json` and `ipo.txt` live under
`$evidence/nix-support/cemu-build/` in the separate optional `evidence` output.
The default runtime output does not retain that output or the bulky diagnostics.
Retrieve diagnostics on the build host, not on a device:

```sh
# Use aarch64-linux instead for ARM build evidence.
evidence=$(nix build --no-link --print-out-paths \
  .#packages.x86_64-linux.cemu.evidence)
ls "$evidence/nix-support/cemu-build/"
```

Store hashes in those diagnostics are redacted to avoid a build-toolchain closure;
the build log retains exact commands. Source is available as `.#cemu.src`.
Cemu carries MPL-2.0; graphic packs carry CC0-1.0. Bundled upstream dependencies
retain their own licenses, installed under `share/licenses/cemu/`.

These tests do not prove gameplay, Vulkan on Adreno, audible sound, controller
mapping or device performance. No signature trust, permissions or installation
are changed. Install only with the existing approved cache and exact plugin
output through `korri-plugin inspect`, `install`, then `enable @korri:cemu`.
Keep signature checks on. Use `nix copy` to move prebuilt closures, never build
on a target. This plugin needs no system/firmware/partition update.

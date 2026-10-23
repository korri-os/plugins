# Eden

`@korri:eden` runs Nintendo Switch `.nsp` and `.xci` files through
`@korri:eden/eden`: `eden -f -g <content>`. It bundles no keys, firmware,
games, mods or device configuration. The TypeScript declaration performs no I/O
and does not check whether keys or firmware exist.

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

See [Odin evidence](bench/samples/odin2portal-acceptance/report.md) and
[Mini evidence/recovery state](bench/samples/rpminiv2-memory/REPORT.md).

## Package and pin

Eden is nixpkgs **0.2.1**, unchanged from nixos-unstable revision
`02c087f3fe673c9e317f206a627cb6b910336dbe` (2026-10-20), through the
plugin-only `nixpkgs-eden` input. The publisher's main pin stays at
`a6531044f6d0bef691ea18d4d4ce44d0daa6e816`. A primary-pin update was tested:
Sunshine evaluation refused it with `sunshine-korri base version changed;
review the approved patch set before building`. An isolated input avoids
changing those approvals and every existing plugin's native dependencies.
The cost is a second dependency set and its disk use.

`package.nix` adds only a launcher. It does not override or rebuild Eden.
Both upstream architecture outputs were downloaded from cache.nixos.org on
2026-10-22. ARM wrapper and checks build on the daemon's aarch64 builders,
not on a handheld. The upstream ARM closure is about 2.0 GiB.

### NCE and graphics evidence

All source citations below refer to the pinned
[Eden v0.2.1 source](https://git.eden-emu.dev/eden-emu/eden/src/tag/v0.2.1),
whose nixpkgs source hash is
`sha256-79/JmIRWysoc3psJqMFyiNc2gjTY4VhJfdNaiTvisMk=`.

- `CMakeLists.txt:296–299` sets `HAS_NCE=1` for ARM64 Android **or Linux**.
  `src/core/CMakeLists.txt:1230–1246` adds `arm/nce/arm_nce.cpp` and the NCE patcher
  when `HAS_NCE` is true.
- The ARM package check reads the real frontend ELF, not its Nix wrappers.
  It requires compiled `Core::ArmNce::RunThread` and
  `Core::NCE::Patcher::PatchText` symbols. Its output retains the ELF header,
  NCE symbol addresses, upstream CMake source and derivation flags.
- The pinned nixpkgs recipe has **no patches**. The check asserts that fact.
  There is no `aarch64-disable-fastmem.patch`, and no build flag disables
  fastmem. `src/common/settings.cpp:180–193` retains the fastmem logic;
  `198–209` requires fastmem and a 39-bit guest address space for NCE.
- `src/common/host_memory.cpp:498–501,518,571–574` requires 4K host pages
  and backs guest memory with `memfd_create("HostMemory", 0)` and executable
  mappings on ARM64. A host's memory-execution policy can still prevent it.
  No wrapper changes host sysctls or sandbox permissions.
- The ARM closure uses Vulkan loader **1.4.363.0** at
  `/nix/store/ad4wmabbwz08rnm6db1n0bff7x63c24h-vulkan-loader-1.4.363.0`.
  The nixpkgs Qt wrapper supplies that loader through `LD_LIBRARY_PATH`.
  The closure includes **mesa-libgbm 26.1.3**, not a bundled Turnip ICD.
  Vulkan drivers come from the system's ICD discovery and sandbox bindings.
  The wrapper sets neither `VK_DRIVER_FILES` nor `VK_ICD_FILENAMES`.
  The package-build stage did not inspect the Odin's Mesa. The later device
  attempt below inspected its existing 26.2.3 ICD without changing it.

Compiled-in NCE is **not** evidence of working NCE gameplay. Upstream calls
Linux NCE experimental (`docs/user/Architectures.md`). Neither device was
contacted during package validation. The initial Odin attempt below is historical; the final labelled-view result
above supersedes it. Do not infer Android performance or
RAM requirements from a build-host startup check.

## Account data and saves

The callback uses only korrid's supplied `accountRoot` and `saveRoot`:

| Data | Location |
|---|---|
| Home | `<accountRoot>` |
| Native configuration | `<accountRoot>/.config/eden/qt-config.ini` |
| User data | `<accountRoot>/.local/share/eden/` |
| Native cache | `<accountRoot>/.cache/eden/` |
| Keys | `<accountRoot>/.local/share/eden/keys/` |
| Firmware/content NAND | `<accountRoot>/.local/share/eden/nand/` |
| Session save NAND root | `<saveRoot>/nand/` |
| Declared `saveLocations.saves` | `<saveRoot>/nand/user/save/` |

Grounding in Eden's native formats, not a new Korri configuration schema:

- `src/common/fs/path_util.cpp:134–163` selects XDG data, cache and config
  roots, adds `eden`, and derives `keys` and `nand`. `362–377` implements
  the XDG/HOME lookup. It first probes `cwd/user` for portable mode; the
  wrapper runs Eden from its immutable package directory to avoid that mode
  overriding account isolation.
- `src/qt_common/config/qt_config.h:15` names `qt-config`;
  `src/frontend_common/config.cpp:30–39` adds `.ini` under the config root.
- `src/frontend_common/config.cpp:278–298` reads the logical `Data Storage`
  group keys `nand_directory` and `save_directory`. **The INI section is
  `[Data%20Storage]`**, not `[Data Storage]`: `BeginGroup` at 962–966 calls
  `AdjustKey` at 999–1003, which encodes spaces as `%20`. The wrapper and real
  GUI test use that exact native section. An empty save path uses NAND;
  a separate save path is explicitly supported. `src/common/fs/path_util.cpp:
  297–303` accepts these overrides only when the directories already exist.
- `src/yuzu/main_window.cpp:630–684` parses `-f`, `-g` and profile arguments;
  the GUI has no NAND/save/config-path command-line option. The separate
  `eden-cli` frontend has different options and is not the registered runner.
- `src/core/hle/service/filesystem/filesystem.cpp:351–361` gives `SaveDir`
  to `SaveDataFactory`; `src/core/file_sys/savedata_factory.cpp:93–99,130–138`
  derives `user/save/...` within it. Thus firmware stays account-local while
  korrid can restore and collect the game's save folder under `saveRoot`.

`nand_directory` and `save_directory` are the **launch contract**, not user
defaults. On every launch, the wrapper creates the native directories and uses
`crudini` to carry korrid's supplied `accountRoot`/`saveRoot` into those two keys
in `qt-config.ini`, like Cemu's `--mlc` argument. A person's own values for these
two keys are replaced on purpose to keep account NAND and game saves isolated.
A seed-once value would point a later launch at a previous game's saves.

Eden 0.2.1's registered GUI runner has no command-line or environment option for
these separate paths: `src/yuzu/main_window.cpp:630–703` parses its arguments;
`src/common/fs/path_util.cpp:147–173,342–370` uses HOME/XDG for the common base,
not separate NAND/save roots. The native INI overrides cited above are therefore
required. No wrapper behavior changes as part of this documentation decision.
ARM game launches also select/check the native Vulkan device as described below.
Input and other graphics preferences remain user-owned. Do not run two Eden
instances against one account configuration at the same time. Account/save paths with controls or double quotes are refused because
Eden's INI reader strips quotes and line breaks can introduce records.
Content is passed as an argv element, never through a shell.

A person supplies their own legally obtained `prod.keys` and, if needed,
`title.keys` in the keys directory above, with mode **600**. Import legally
obtained firmware with Eden's own firmware installer into the account NAND
(`nand/system/Contents/registered`,
`src/core/file_sys/bis_factory.cpp:17–24`). Do not copy a Ryujinx NAND
or save tree wholesale: native save layouts and emulator user IDs can differ.
The declaration and wrapper never open or copy key files. Eden itself reads
the keys when needed; no keys are logged, committed or shipped here.

## Wrapper environment

| Variable | Reason |
|---|---|
| `QT_QPA_PLATFORM=xcb` by default | Use gamescope's Xwayland without requiring `--expose-wayland`. An explicit platform, such as `offscreen` for diagnostics, is retained. |
| Unset `QT_QPA_PLATFORMTHEME` | Do not load an inherited `xdgdesktopportal`/GTK platform theme inside the isolated game session. This removes that source of portal waits; it is not a claim that Eden makes no D-Bus calls. |
| `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` | Account isolation through Eden's own XDG lookup above. Set by `launch.prepare`, not the wrapper. |
| `EDEN_SAVE_ROOT` | Private launcher environment carrying korrid's existing save root to the native INI edit. Not a new setting, permission or host schema. |

There are no CPU-affinity, Mesa, audio, DPI, QtWebEngine sandbox-disabling or
D-Bus-disabling variables. The upstream nixpkgs Qt/GApps wrappers still supply
their normal library, plugin and resource search paths. The game session host
must expose its display, graphics driver and audio sockets normally; this
plugin grants no extra permissions.

## ARM Vulkan device selection

Eden 0.2.1 does not use the Vulkan loader's device order unchanged. In the pinned
`src/video_core/vulkan_common/vulkan_wrapper.cpp:23–69,470–475`, it sorts names in
descending byte order, then prefers discrete GPUs and Nvidia/AMD/Intel vendors,
and finally demotes Microsoft Dozen. It does not rank CPU devices last.
Consequently `llvmpipe` sorts ahead of the integrated `Turnip Adreno (TM) 740`.
The same-unit Vulkan probe lists Turnip as raw GPU0 and llvmpipe as raw GPU1;
Eden reverses those two. This is an application device-selection bug, not evidence
of a broken Turnip driver.

`src/common/settings.h:339` defaults `vulkan_device` to integer **0**.
`src/frontend_common/config.cpp:366–375,912–935` reads it from `[Renderer]`,
including native `\\default` and per-title `\\use_global` flags.
`src/video_core/renderer_vulkan/renderer_vulkan.cpp:93–103` indexes Eden's sorted
list directly. There is no device-name selection setting in this path.

On **aarch64 Korri game launches only** (`EDEN_SAVE_ROOT` and `-g`), the launcher
uses the prebuilt `vulkaninfo --summary`, applies the pinned Eden ordering, and
checks for an Adreno device with the Mesa Turnip driver. It writes only the
native `[Renderer]` keys `vulkan_device` and `vulkan_device\\default=false`, in
one atomic crudini merge, and only while the setting is still native-default.
An explicit non-default valid Adreno choice is kept without rewriting it.
Missing hardware, incomplete device properties, an out-of-range index or a
non-Adreno choice fails clearly; it never silently launches with llvmpipe.
There is no provenance sidecar, Korri setting, per-device profile, Mesa variable,
driver pin or removed ICD. x86 launches and no-game GUI probes are unchanged.
Per-title device overrides remain native Eden configuration; hardware acceptance
must still check the actual renderer log, not infer it from this global setting.

**Native limitation:** Eden records whether a value equals its default, not
whether a person chose it. A person who explicitly picks index 0 gets
`\\default=true`, just like an untouched default. This helper moves that choice
to Adreno. On the observed Odin ordering, index 0 is llvmpipe and would otherwise
fail this hardware check anyway. A non-default selection stays fixed; if a
changed device list makes it invalid, choose Adreno again in Eden's UI.

The existing version gate remains at 0.2.1. The package check also pins the whole
`vulkan_wrapper.cpp` source hash, so an upstream edit requires ordering review.
This conservatively requires review even for unrelated edits in that file.
Twelve tests cover native ordering, Turnip alone, software-only refusal, explicit
choices, the index-0 limitation, invalid properties/indices, preserved native
settings and diagnostics that do not echo malformed configuration contents. The unchanged Eden binary is still reused from cache. The ARM closure
now includes a prebuilt Vulkan probe; closure growth and on-device preflight time
will be recorded with device acceptance, not guessed from a build-host check.

### Draft upstream Eden issue — not filed

**Title:** Linux ARM: device sorting ranks llvmpipe ahead of an integrated Adreno GPU

On Odin 2 Portal with Mesa/Turnip 26.2.3, the Vulkan loader enumerates Turnip
Adreno 740 before llvmpipe. Eden 0.2.1's `SortPhysicalDevices` instead sorts
`llvmpipe` ahead of `Turnip`, because both are non-discrete and neither vendor is
in the preferred Nvidia/AMD/Intel list. Default native device index 0 therefore
selects a CPU renderer despite accessible hardware. An administrator's same-unit,
same-UID/environment probe opened the render node and enumerated both devices.

Please rank `VK_PHYSICAL_DEVICE_TYPE_CPU` after hardware devices in the native
sort. The source locations are `vulkan_wrapper.cpp:50–69,470–475` and
`renderer_vulkan.cpp:93–103`. Changing the order can also change what an existing
stored integer index names; that is an upstream compatibility concern, not a
reason to keep preferring a CPU renderer. Filing this draft is the user's choice.

## ARM P1 controller defaults

ARM game launches seed untouched P1 bindings for InputPlumber's **Korri Seat P1**
in Eden's own `[Controls]` INI group. Keyboard-only P1 cannot play a handheld's
built-in gamepad. There is no new Korri setting, input profile or device policy.
x86 and no-game GUI launches keep native behavior.

The native `p1-controls.ini` artifact comes from selecting **Xbox 360 Controller
0** in Eden 0.2.1's Controls UI on the Odin, then diffing the INI. SDL calls all
four InputPlumber outputs Xbox 360 Controller. Its native device path links that
entry to `/sys/class/input/event6/device/name = Korri Seat P1`; the recorded
normalized GUID is `030000005e0400008e02000014010000`, native port 0. Discovery
matches that exact kernel seat name, not the first gamepad or the displayed Xbox
name. It derives GUID and port from SDL each time defaults need seeding.

- Any P1 `\\default=false` field keeps P1 unchanged. Missing fields count as
  native defaults, so a new account is configured before Eden's first load.
  Other players and settings remain untouched. No provenance sidecar is used.
- Missing, ambiguous or unavailable seat discovery keeps Eden's defaults and
  logs one clear line; it does not fail the launch or choose another seat.
- Eden's UI can normalize keyboard bindings and serialize them with
  `\\default=false`. Such existing accounts are deliberately not migrated or
  guessed untouched; select the seat in Eden's Controls UI. The test account
  received that native UI assignment and keeps it after the performance stage.
- The mapping keeps the UI's Nintendo layout: Switch A is SDL button 1
  (right/East), B is button 0 (bottom/South). Motion and screenshot bindings are
  unbound where that native UI did not provide them. The helper does not add a
  gyro, grab an input device, change InputPlumber admission or emit rumble.
- The artifact does not copy the UI's incidental color serialization or one
  physical stick's measured calibration. Analog offsets are neutral zero;
  the captured native 15% deadzone is retained. Native calibration remains
  available in Eden's UI. Existing person-set calibrations are preserved.

Native source grounding, pinned by the package check:

- `src/qt_common/config/qt_config.cpp:81–135,376–395` reads/writes P1 button,
  analog and motion parameter strings and their native default flags.
- `src/yuzu/configuration/configure_input_player.cpp:1451` gets the automatic
  button mapping when a device is selected.
- `src/input_common/drivers/sdl_driver.cpp:17–23` clears the controller-name CRC
  in GUID bytes 2–3; 193–197 defines port as the count of earlier devices with
  the same normalized GUID; 718–789 builds native SDL parameter packages;
  845–868 maps Nintendo buttons; 948–1001 builds analogs and offsets.
- `src/frontend_common/config.cpp:1006–1030` preserves the native quoted string
  representation. The mapping artifact, not a duplicate Python mapping table,
  owns the values. GUID and port are substituted from the discovered seat.

Nine focused tests cover default assignment, untouched new accounts, person-set
preservation, missing/ambiguous seats, unavailable probe launch behavior,
unrelated settings and sanitized invalid flags. The real UI diff and normal
uinput/Bonneton route are separate hardware evidence; unit tests do not prove
input admission or the game's player slot.

## Build-host checks

```sh
nix build --no-link .#packages.aarch64-linux.korri-plugin-eden \
  .#checks.aarch64-linux.korri-eden-package \
  .#checks.aarch64-linux.korri-eden-admission
nix build --no-link .#checks.x86_64-linux.korri-eden-package \
  .#checks.x86_64-linux.korri-eden-admission
```

The package gate runs strict TypeScript checking, callback tests, ShellCheck,
ELF/NCE evidence and real GUI startup under Xvfb. It checks two accounts and
two save roots, retained native graphics settings and avoidance of portable
mode, with an inherited portal theme. The real bundled CLI's `--version`
proves bounded native startup without games. That cached binary prints
`Eden 1.0.0 stable-1.0.0`: Eden's archive-build fallback in
`externals/cmake-modules/GetSCMRev.cmake:55–72`, not the nixpkgs package
version. Version identity here is the pinned `v0.2.1` source hash and
unchanged nixpkgs derivation, not that fallback string. The GUI does **not** implement
`--help` or `--version`; these are not used as GUI probes.
The admission gate uses Core's actual evaluator and `korrid plugin-run`,
checks manifest authority, and tests accepted and refused launches. It does
not install or enable anything.

Publication, signatures and device acceptance remain separate gates. After an
approved signed publication, install only through `korri-plugin inspect`,
`install` with the exact inspection approval, then `enable @korri:eden`.
Keep signature and permission checks enabled. No publication or device access
is part of this change. Any future per-device profile, CPU affinity or typed
Eden setting needs a user decision backed by measurements, not a new field here.


## Verified 2026-10-22

| aarch64 output | Exact store path |
|---|---|
| Unchanged nixpkgs Eden 0.2.1 | `/nix/store/010847afgzfll903n5dbzqdajmm1m0n7-eden-0.2.1` |
| Launcher | `/nix/store/y1vrxl47w3arr32py7vkga91p69376ys-eden-korri-0.2.1` |
| Plugin | `/nix/store/4g5c49fdz70pkskazgr3b1gpwrqdj55f-korri-plugin` |
| ELF, NCE and startup evidence | `/nix/store/jm57f095iv9awbp8ihq8cmadi9azsvk5-korri-eden-package-check` |

The package and admission gates passed on both architectures. Native ARM
GUI checks ran on <builder-2>; an additional `eden-cli --version` invocation passed
on <builder-1> after `nix copy`. Neither is a device/gameplay result.

One full local pass used the explicit lists from `plugin-repository.yml`,
`solarus.yml` and `zquest-classic.yml`, plus the two Eden gates. The 64-check
batch, x86 Sunshine input-seat gate and both x86 lifecycle gates passed
(**67 check outputs**). The ARM Sunshine input-seat gate was blocked because
no aarch64 builder advertises `nixos-test`. A separate catalogue probe confirmed
the known unsupported ARM BlastEm output. Neither gap was changed.
Source-auth integration (4 tests), cache configuration (2), RetroArch (3),
eight churn cases on each architecture, catalogue-name evaluation on both
architectures and the signed-cache export regression also passed. Nixfmt,
ShellCheck, strict TypeScript checking, Python syntax and Ruff checks passed.
No publication, installation, enablement or device access was performed in
that package-build stage.

## Focused checks (from the repository root)

```sh
nix build .#checks.x86_64-linux.korri-eden-package --no-link -L
nix build .#checks.x86_64-linux.korri-eden-admission --no-link -L
nix build .#checks.x86_64-linux.korri-eden-bench --no-link -L
```

The package check runs both native helper scripts with the actual `crudini`
executable as their first argument, plus strict mypy, Ruff, declaration tests
and the real GUI check. Do not run the helper files as multiple unittest module
names: their script interface consumes argv[1] as a crudini path. The bench check
supplies Python with `evdev` and runs its tests, static checks and Xvfb integration;
a plain system Python may not have that dependency. These are the working Nix
check entry points; no device access is needed.

## Historical: initial Odin graphics checkpoint — 2026-10-23

This checkpoint is superseded by the final results at the top of this document.

**Stopped at the graphics gate; FPS target not met or measured.** A real SMO
library launch reached Gamescope/Xwayland, but produced no observed picture or
X11 Present completions. Eden logged `llvmpipe 26.2.3`, not the device's existing
Mesa/Turnip 26.2.3. The collector lost its exact renderer identity during warmup
and stopped its own session. This does not establish an emulator crash or its
cause. The required no-picture rule stopped further launches; no plugin driver
pin, environment override or wrapper was added.

Device evidence uses the **personal test publisher**, not an official release:
`@<publisher>:eden`, source commit
`fc795cdfc782bac0c649fec92f765ac7edc1d416`. Test-only composition changed exactly
one source literal: `@korri:eden/eden` → `@<publisher>:eden/eden`.
[The diff](bench/samples/odin2portal-firstlight/ARCHIVE.sha256) proves the sole
delta. The native Eden and launcher outputs were unchanged. Existing publisher
bindings, signatures and inspect/install/enable checks stayed in force. Official
`@korri:eden` signing remains a later CI publication step.

| Backend | Median FPS | p10 FPS | Evidence |
|---|---|---|---|
| NCE selected | Unavailable | Unavailable | [Warmup failure, zero bins](bench/samples/odin2portal-firstlight/firstlight-nce-retry/report.md) |
| Dynarmic | Unavailable | Unavailable | Not launched after the graphics stop |

NCE execution is unproven: selection and fastmem log lines are not runtime-map
proof. No faster stable backend was selected. The shipped upstream ARM NCE
default remains unchanged, not endorsed by a benchmark.

The source and SMO were admitted through Core's existing offline discovery tool
with explicit supervisor permission. Staging ACLs needed service-user access in
addition to runtime-user access. The converted save was moved under korrid's
actual saveRoot and staging was removed, but its profile was not rebound or
loaded in-game. Audio, save persistence, Bonneton navigation and the 15-minute
soak remain unverified. SMO's Gamescope and CPU/GPU test settings were restored
and verified. **bubblewrap: absent — core gap #184.**

See the [full report](bench/samples/odin2portal-firstlight/report.md), including
install evidence, exact settings/restoration, native log/dmesg, discovery's
retained conflict and the required graphics-stack decision. No keys, firmware,
game or save payload is included in that evidence.

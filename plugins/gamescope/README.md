# Gamescope launch modifier

`@korri:gamescope` contributes only `@korri:gamescope/gamescope` and the
`launch.compose` handler. It changes an existing runner plan. It declares no
runner, system, service, or runtime effects. The first hardware acceptance
target is Retroid Pocket Mini V2, nested inside Sway.

## Composition

The handler receives the brief's camelCase `PluginComposeInput` and returns
`PluginLaunchOutput`. The request type is local in `plugin.ts` until the pinned
Korri contract exports it. The existing launch output and scalar types still
come from the pinned generated contract. Do not advance Core to an unlanded
branch to obtain the new request type.

The command is the manifest's named `files.gamescope`. Arguments are, in
this fixed order:

1. `--backend wayland --fullscreen --expose-wayland`.
2. Typed settings, in the order of the table below. A setting appears only if
   it has a value. `--force-composition` appears by default.
3. Words from `config.append`.
4. `--`, then the runner command and its arguments.

### Typed settings

Each key is the exact Gamescope 3.16.31 long option name in
`gamescope_options` (`src/main.cpp:60`). The korrid cascade merges `settings`
key by key from device to runner to system to library item, so a later layer
overrides one key and keeps the others. `config.append` does not merge: the
last layer that sets it replaces all lower append text.

Kinds:

- **integer**: a JSON integer inside the limits. Korri emits `--key N`.
- **float**: a finite JSON number inside the limits. Korri emits `--key X`
  with JavaScript's shortest decimal form, for example `1.5` or `1e-7`.
- **choice**: one of the listed strings, with the exact spelling.
- **boolean**: `true` adds the flag `--key`. `false` leaves it out. Any other
  value refuses composition.
- **path**: a string that starts with `/` and has no NUL byte.
- **string**: a string with the syntax in the table.

Integer limits come from `parse_integer` (`main.cpp:455`, `std::from_chars`
into `int`, so at most 2147483647). Float limits for `parse_float`
(`main.cpp:469`) are `FLT_MIN` 1.1754943508222875e-38 to `FLT_MAX`
3.4028234663852886e38; the built binary refuses `1e-50` and `3.5e38`.
Options that Gamescope reads with `atoi`/`atof` (the
`steamcompmgr_main` loop, `src/steamcompmgr.cpp:9814`) never fail to parse.
For those, Korri sets the limit given in the table. "Line" names the option's
entry in `main.cpp` and the code that reads its value.

| Key | Kind | Accepted values | When absent | Line |
| --- | --- | --- | --- | --- |
| `output-width` | integer | 1..2147483647, with `output-height` | Width of the `display` fact | 69; `parse_integer` 748 |
| `output-height` | integer | 1..2147483647, with `output-width` | Height of the `display` fact | 70; `parse_integer` 751 |
| `nested-width` | integer | 1..2147483647, with `nested-height` | Gamescope default | 63; `parse_integer` 734 |
| `nested-height` | integer | 1..2147483647, with `nested-width` | Gamescope default | 64; `parse_integer` 737 |
| `nested-refresh` | integer | 1..2147483 (Gamescope multiplies by 1000 in an `int`, `src/refresh_rate.h:7`) | Gamescope default | 65; `parse_integer` 740 |
| `scaler` | choice | `auto`, `integer`, `fit`, `fill`, `stretch` | Gamescope default (`auto`) | 67; `parse_upscaler_scaler` 390 |
| `filter` | choice | `linear`, `nearest`, `fsr`, `nis`, `pixel` (Gamescope 3.16.31 also accepts `sgsr`, `src/main.hpp:111`; Korri does not type it yet) | Gamescope default (`linear`) | 68; `parse_upscaler_filter` 408 |
| `sharpness` | integer | 0..20 (`--help`: 0 is max, 20 is min) | Gamescope default (2) | 71; `parse_integer` 820 |
| `framerate-limit` | integer | 0..2147483647; 0 disables | Gamescope default (0) | 97; `atoi`, steamcompmgr 9873 |
| `max-scale` | float | `FLT_MIN`..`FLT_MAX` | Gamescope default (no limit) | 66; `parse_float` 757 |
| `force-composition` | boolean | `true`, `false` | **`true`**: Korri adds `--force-composition` | 136; steamcompmgr 9835 |
| `adaptive-sync` | boolean | `true`, `false` | Off | 78; 837 |
| `rt` | boolean | `true`, `false`; acts only with `CAP_SYS_NICE` (881) | Off | 73; 823 |
| `fade-out-duration` | integer | 0..2147483647 (milliseconds) | Gamescope default (0) | 139; `atoi`, steamcompmgr 9853 |
| `force-windows-fullscreen` | boolean | `true`, `false` | Off | 142; steamcompmgr 9855 |
| `hdr-enabled` | boolean | `true`, `false` | Off | 146; steamcompmgr 9857 |
| `hdr-sdr-content-nits` | float | 1..10000 (the atom path treats below 1 as unset, steamcompmgr 693; 10000 nits is the PQ ceiling) | Gamescope default | 147; `atof`, steamcompmgr 9867 |
| `hdr-itm-enabled` | boolean | `true`, `false` | Off | 148; steamcompmgr 9863 |
| `hdr-itm-sdr-nits` | float | 1..1000 (the atom path clamps the same, steamcompmgr 7440) | Gamescope default (100) | 149; `atof`, steamcompmgr 9869 |
| `hdr-itm-target-nits` | float | 1..10000 (atom clamp, steamcompmgr 7449) | Gamescope default (1000) | 150; `atof`, steamcompmgr 9871 |
| `sdr-gamut-wideness` | float | 0..1 (`--help`) | Gamescope default | 145; `atof`, steamcompmgr 9865 |
| `disable-color-management` | boolean | `true`, `false` | Off | 144; 797 |
| `force-grab-cursor` | boolean | `true`, `false` | Off | 87; 833 |
| `mouse-sensitivity` | float | `FLT_MIN`..`FLT_MAX` (multiplier; 0 and negative values are refused) | Gamescope default (1.0) | 76; `parse_float` 778 |
| `default-touch-mode` | integer | 0..6: hover, left, right, middle, passthrough, disabled, trackpad (`src/backend.h:102`) | Gamescope default (1, left) | 94; `parse_integer` 812 |
| `cursor` | path | Absolute path to an image file | Host cursor | 124; steamcompmgr 9849 |
| `cursor-hotspot` | string | `X,Y`, each an integer 0..2147483647, no spaces (`sscanf "%d,%d"`) | 0,0 | 125; steamcompmgr 9851 |
| `cursor-scale-height` | integer | 1..2147483647 | Off | 126; `parse_integer` 843 |
| `hide-cursor-delay` | integer | 0..2147483647 (milliseconds) | Gamescope default (10000) | 130; `atoi`, steamcompmgr 9829 |
| `prefer-vk-device` | string | `VENDOR:DEVICE`, 1..8 hex digits each, no `0x` (`sscanf "%X:%X"`) | First qualifying GPU | 74; 825 |
| `reshade-effect` | string | A relative file name; no empty, `.` or `..` segment, no NUL | None | 155; steamcompmgr 9875 |
| `reshade-technique-idx` | integer | 0..2147483647 | Gamescope default (0) | 156; `atoi`, steamcompmgr 9877 |
| `xwayland-count` | integer | 1..2147483647 | Gamescope default (1) | 120; `parse_integer` 799 |
| `steam` | boolean | `true`, `false` | Off | 135; 781 |
| `virtual-connector-strategy` | choice | `SingleApplication`, `SteamControlled`, `PerAppId`, `PerWindow` | `SingleApplication`; `SteamControlled` with `steam` | 127; 851 |
| `borderless` | boolean | `true`, `false` | Off | 84; 766 |
| `disable-xres` | boolean | `true`, `false` | Off | 138; steamcompmgr 9838 |
| `allow-deferred-backend` | boolean | `true`, `false` | Off | 161; 847 |

`steam` comes before `virtual-connector-strategy` in the order. `--steam`
changes a `SingleApplication` strategy to `SteamControlled` (`main.cpp:781`),
so an explicit strategy must come after it. Gamescope ignores an unknown
strategy name (`main.cpp:851`); Korri refuses it.

Gamescope looks for `reshade-effect` in
`$HOME/.local/share/gamescope/reshade/Shaders/` and then
`/usr/share/gamescope/reshade/Shaders/` (`src/reshade_effect_manager.cpp:941`).
This package ships no shaders. Gamescope reads `cursor` with `stbi_load`
(`steamcompmgr.cpp:8774`). Gamescope is the main process of the game's session
unit (Core ADR 0007), so it reads files with the same access as the game.

Unknown settings, bad types, invalid values, and unpaired dimensions refuse
composition with the code `gamescope-setting` or `gamescope-setting-pair`. If
output dimensions are absent, both come from the logical `display` hardware
fact. Without either source, composition refuses the launch.

### Composition is on by default

Korri adds `--force-composition` unless the merged settings set
`force-composition` to `false`. The default is the constant
`forceCompositionDefault` in `compose.ts`.

On the RG353M (Mali-G52, Mesa panvk), passthrough scan-out keeps buffers from
vsynced X11 clients, and the clients do not get their 3 buffers back in time.
Without the flag, RetroArch ran at about 43 FPS against 60 native, and Mega
Man (Godot 2) at about 53 FPS. With `--force-composition` both held about 60
FPS: RetroArch median 59.9, minimum 59.1; Mega Man median 59.7, minimum 58.1.
Gamescope then used 12.5 to 17% of one core. The cost on other devices is not
measured yet. To turn composition off for one device, runner, system or game,
set `force-composition` to `false` in that layer.

### Options that are not typed

These Gamescope 3.16.31 options have no typed setting. `config.append` still
passes them to Gamescope. All 84 options are accounted for: 38 typed, 3 fixed,
43 here.

| Options | Reason |
| --- | --- |
| `backend`, `fullscreen`, `expose-wayland` | Korri always passes them. |
| `help`, `version` | Gamescope exits before it starts the game. |
| `ready-fd`, `stats-path` | Gamescope opens or writes the named path (`steamcompmgr.cpp:9818`, 9821). Korri owns readiness and diagnostics. |
| `prefer-output`, `force-orientation`, `generate-drm-mode`, `force-composition-rotation` | Inert under `--backend wayland`; read only in `Backends/DRMBackend.cpp` (1583, 2486, 3723, 3686). |
| `display-index`, `nested-unfocused-refresh` | Inert under `--backend wayland`; read only in `Backends/SDLBackend.cpp` (259, 856). SDL runs only if the Wayland backend cannot start (`main.cpp:1002`). |
| `immediate-flips` | Inert under `--backend wayland`; tearing needs `SupportsTearing()` (`steamcompmgr.cpp:10577`), which is `false` for Wayland (`WaylandBackend.cpp:2311`). |
| `grab` | Inert under `--backend wayland`; it only adds " (grabbed)" to the window title (`WaylandBackend.cpp:1262`). The keyboard grab is SDL-only (`SDLBackend.cpp:254`). |
| `fsr-sharpness` | The same variable as `sharpness` (`main.cpp:820`). Two keys for one value would let argv order, not the cascade layer, choose the value. Use `sharpness`. |
| `keep-alive` | Gamescope stays alive after the game exits (`main.cpp:849`). Gamescope is the session unit's main process, so the session would not end with the game (Core ADR 0007). |
| `mangoapp` | Gamescope starts `mangoapp` from `PATH` (`steamcompmgr.cpp:9444`, 9607). This package ships no `mangoapp`. |
| `mura-map` | Steam Deck panel calibration: a path prefix for `_red.png` and `_green.png` (`steamcompmgr.cpp:798`). No Korri device has a mura map. |
| `xwayland-force-touch-pointer-emulation` | New in 3.16.31 and not yet reviewed for a typed setting. It clears Xwayland's `no_touch_pointer_emulation`, which Gamescope sets by default (`main.cpp:324`, `wlserver.cpp:1880`). |
| 16 `vr-*` options | OpenVR overlay; Korri has no VR device. |
| `debug-layers`, `disable-layers`, `debug-focus`, `synchronous-x11`, `debug-hud`, `debug-events`, `composite-debug`, `hdr-debug-force-support`, `hdr-debug-force-output`, `hdr-debug-heatmap` | Debug options. |

Append text honours single/double quotes, backslash escapes, empty quoted
words, and escaped newlines. It performs no variable, tilde, glob, or command
expansion. It never invokes a shell. Shell operators and comment characters
are literal argument text. Malformed quoting and NUL bytes refuse composition.
Append words follow typed flags, including duplicate flags. Native options in
append remain the person's responsibility; they can change Gamescope behavior
or fail when Gamescope parses them.

The handler preserves the runner's `env`, `envUnset`, `cwd`, `directories`,
and `files` unchanged. Errors carry `code`, a readable `message`, and
`retryable: false`. Missing named binary paths refuse composition. The host
must verify package/file existence and report native startup failures. The
plugin cannot inspect files or start a process, and never returns an unmodified
plan as a fallback.

## Build and checks

Run only on a build machine:

```sh
bun test plugins/gamescope/compose.test.ts
nix build --no-link .#checks.x86_64-linux.korri-gamescope-plugin
nix build --no-link .#checks.aarch64-linux.korri-gamescope-plugin
nix build --no-link .#packages.aarch64-linux.korri-plugin-gamescope
```

The check exercises the packaged handler, manifest, strict TypeScript types,
and the native binary's `--version` and `--help`. `nix/gamescope-options-check.ts`
then reads `gamescope_options` from the patched `src/main.cpp` and requires 84
options. Each typed key must be an exact entry, `no_argument` for a boolean
and `required_argument` for the other kinds. The source check is necessary
because getopt accepts abbreviations: the binary accepts `--hdr-enable`. For
each key the built binary must then accept `--key VALUE --help` (both limits,
every choice, or the bare flag), exit 0 and print its usage. Gamescope parses
`parse_integer`, `parse_float`, scaler and filter values before `--help`, so a
value outside those parsers' range fails this check. It does not start a nested
compositor or establish display, touch, controller, audio, or frame-rate
acceptance on hardware. The current pinned Core predates modifier admission
and execution. Host integration must be verified when Core lands that support.

`package.nix` asserts Gamescope 3.16.31, the version in nixpkgs
`02c087f3fe673c9e317f206a627cb6b910336dbe` (nixos-unstable 2026-10-20). Its
options and values were checked in upstream `src/main.cpp` and
`src/steamcompmgr.cpp` at that version; line numbers in this file are
upstream 3.16.31 before any patch. Nixpkgs' packaging and system-library
patches stay intact. These additional patches are applied:

| Patch | Source and reason |
| --- | --- |
| `0001` | Unchanged ROCKNIX nested Wayland `wl_touch` patch (ValveSoftware/gamescope#1606), copied from Korri `b22b82d6a24e6164846ad97adb347e783579b531`. Byte-identical to ROCKNIX's `0001` at distribution commit `d209b09`. |
| `0002` | Unchanged ROCKNIX `0024-WaylandBackend-acquire-only-attached-buffers.patch`, which targets 3.16.31. Acquire framebuffers at the shared attach site, after the configure gate and clipping, so skipped planes do not retain references waiting for a release that cannot arrive. Also covers the black backing buffer. |
| `0003` | Unchanged upstream master `56861b7cbe324e0593f41dfb3c374815050de68c`: revert `d12ec394` (shipped in 3.16.29 to 3.16.31), which loses mouse lock and causes erratic camera movement in nested mode (ValveSoftware/gamescope#2476). |
| `0004` | Korri-local. Enable `VK_EXT_robustness2` only if `nullDescriptor` is supported. Without it, bind 1x1 images (2x2 for YCbCr) to unused descriptor slots, and the shader treats a 1-texel shaper LUT as absent. panvk before v10 has no `nullDescriptor`, so `vkCreateDevice` failed. The fallback fills all 16 sampler slots: 8 layers, the blur slot and two NIS coefficient slots. |
| `0005` | Korri-local. Bind the constants UBO with the uploaded struct's size, not `VK_WHOLE_SIZE`. The whole-size range covers the rest of the 8 MB upload buffer, beyond `maxUniformBufferRange`. panvk v7's 12-bit UBO entry count wrapped and every composite was black. |
| `0006` | Korri-local. If no `HOST_VISIBLE`, `HOST_COHERENT`, `HOST_CACHED` memory type fits a mappable image, retry without `HOST_CACHED`. panvk has no cached coherent type. |
| `0007` | Korri-local. Do not start the `gamescope-shdr` precompile thread (a `std::jthread` since upstream `389e7e2c`). Its keys do not match the runtime keys, `pipeline()` compiles on first use, and on the RG353M it held one core at about 100% for over a minute. |
| `0008` | Korri-local. If no GPU qualifies, opt in to Mesa panvk for Bifrost from Gamescope's own process, retry once, then remove the opt-in from the environment. Prefer a GPU to a CPU device (llvmpipe). Details below. |

The 3.16.18 set also carried upstream `c2d8f0c33266e36f8d91978171ba74a7cbd8a2e4`
(skip planes that clip to zero or negative size; in 3.16.26 and later) and
upstream `c50ddfa9b71a75ec8df94bda8cf31d425dbdda24` plus
`6867f509874f9bc52e12d6f4c4596cdf0d5be6b4` (after a real toplevel unmap, wait
for a new configure before attaching another buffer; in 3.16.30 and 3.16.31).
3.16.31 contains them, so they are not patches any more.

Patch `0002`'s ROCKNIX source is distribution commit
`d209b09cbf2eebe74442ca9a4d50d59a468501d2` (2026-10-06, "gamescope: upgrade
to 3.16.31 and port ROCKNIX patches"):
<https://github.com/ROCKNIX/distribution/blob/d209b09cbf2eebe74442ca9a4d50d59a468501d2/projects/ROCKNIX/packages/apps/gamescope/patches/0024-WaylandBackend-acquire-only-attached-buffers.patch>.
No other ROCKNIX patches are included. Upstream master after 3.16.31 has its
own nested `wl_touch` commit (`30b1b1e7`) and a fix for a left click that
stays down after a 2-finger tap (`1b17fcc1`). This set does not include them.
The patches change neither the Gamescope version nor its options.

### Mali Bifrost (RG353M) and other GPUs

`0004` to `0008` are Korri-local. They are not upstream and were not sent
upstream. They make the same package run on the RG353M (Mali-G52, Mesa
26.2.3 panvk, architecture v7) with no device configuration.

Mesa panvk refuses v6/v7 GPUs unless `PAN_I_WANT_A_BROKEN_VULKAN_DRIVER` is
set. It reports Vulkan 1.0 on v7 unless `MESA_VK_VERSION_OVERRIDE` is set.
Gamescope needs 1.2. Without both, only llvmpipe qualifies, and Gamescope
aborts on it. `0008` changes device selection as follows:

1. Select as before, but prefer a non-CPU device to a CPU device. A device
   named by `--prefer-vk-device` still wins.
2. If no device or only a CPU device qualifies, and there is no SDL surface,
   set each of the two variables that is unset (`1` and `1.3`). Log
   `no GPU Vulkan device qualified; retrying with Mesa opt-in: ...`.
3. Destroy and recreate the Vulkan instance, and select once more.
4. Unset the variables that step 2 set.

Mesa reads both variables only while it creates the instance and enumerates
physical devices. Gamescope initialises Vulkan inside backend `Init()`, before
it starts Xwayland and the child, so games do not inherit the variables. A
variable that the caller set stays as the caller set it. A GPU that qualifies
on the first pass never reaches steps 2 to 4.

`0004`, `0006` and `0008` change behaviour only where upstream fails: no
`nullDescriptor`, no cached coherent memory type, or no qualifying GPU.
`0004` also changes the shader for every GPU: a real shaper LUT has 4096
texels, so the added size check is true wherever upstream's check is true.
`0005` and `0007` run on every GPU. `0005` replaces invalid usage
(`VUID-VkWriteDescriptorSet-descriptorType-00332`) with a range of at most
16384 bytes, which every conformant driver must accept; a `static_assert`
keeps each constants struct within that size. `0007` changes only when
pipelines compile, not which pipelines run. With `0007`, the first frame that
uses an upscaler (FSR, NIS or SGSR) compiles its pipeline then.

Adreno (Turnip) on Retroid Pocket Mini V2 and AYN Odin 2 Portal has not run
this package. Its Vulkan driver qualifies on the first pass, so only `0004`'s
shader change, `0005` and `0007` apply there.

The next paragraph's runs used the 3.16.18 set, where these patches were
`0005` to `0009`. The 3.16.31 set has not run on the Mini V2 or Odin 2 Portal
yet; its RG353M run is described after this paragraph. On 2026-10-22 the
3.16.31 x86_64 build passed
`tests/nested-windows.py` nested in a headless Sway 1.11 on Intel UHD (TGL
GT1): 25 handoffs, `REPRO_COMPLETE`, exit status 0, no protocol error, 313
buffer attachments. With only llvmpipe it logged the opt-in line, selected
llvmpipe, and passed the same test. 3.16.31 only warns about a missing
`VK_EXT_physical_device_drm`, so llvmpipe no longer stops there.

On 2026-10-21 the aarch64 build ran on the RG353M nested in the Korri
compositor as user `korri`, with no Vulkan variables and an empty
`/dev/input`. Around glxgears and around Mega Man Rock N Roll it logged the
opt-in line and selected `Mali-G52 r1 MC1`. Gamescope's own screenshot matched
the compositor's (the game frame was pixel-identical). After start, Gamescope
used 14.7 to 15.3% of one core with the game and 19.7 to 20.0% with glxgears
at 60 FPS; the earlier build with exported variables used 21.1% with
glxgears. The child, `gamescopereaper` and Xwayland had neither variable in
`/proc/<pid>/environ`. `tests/nested-windows.py` completed all 25 handoffs
with exit status 0 and no protocol error. The x86_64 build passed the same
test nested in a headless Sway 1.12 on Intel, without the opt-in line. With only
llvmpipe it logged the opt-in line, selected llvmpipe again, and stopped on the
missing `VK_EXT_physical_device_drm`, as before the patch.

On 2026-10-23 the 3.16.31 aarch64 build
(`z9y9jddlg8wsk7a6glyc857m8x57i31h`) ran on the RG353M (Mesa 26.2.3) nested in
the Korri compositor (Sway 1.12) as user `korri`, with no Vulkan variables.
The 3.16.18 build from `main` (`idni6chymvbglya9wvmyj4z5dw3iz0dw`) ran the same
three tests in alternation, three times each. Both logged the opt-in line,
selected `Mali-G52 r1 MC1` and logged `physical device does not support
nullDescriptor, using dummy descriptors`, so `0004`'s fallback ran.

| Test, 640x480 output | 3.16.31 | 3.16.18 |
|---|---|---|
| glxgears, `linear` | 60 FPS; Gamescope 9.4 and 10.4% of one core | 60 FPS; 11.5 and 9.3% |
| glxgears, 320x240 with `--filter fsr` | 12 to 15 FPS | 12 to 15 FPS |
| `tests/nested-windows.py` | 25 handoffs, 20 remaps, `REPRO_COMPLETE`, exit 0, no protocol error, 226 to 230 buffer attachments | Same; 234 to 235 attachments |

No child, `gamescopereaper` or Xwayland process had either Mesa variable in
its environment. FSR is limited to about 15 FPS by the GPU on both versions,
so it is not a regression. Both versions sometimes log `Compositor released us
but we were not acquired` (3.16.31 twice in four runs, 3.16.18 once in three).
The X11 client receives 2 `ConfigureNotify` events on 3.16.31 and 7 on
3.16.18. The RG353M has no touch panel, so `0001` was not exercised. No game
ran in this pass.

### Nested regression and input acceptance

`tests/nested-windows.py` uses Python's standard library and libX11. Run it
inside Gamescope on a build machine or copy the interpreter and library as
prebuilt store paths to the device. For an existing Wayland session:

```sh
GAMESCOPE="$(nix build --no-link --print-out-paths .#gamescope)/bin/gamescope"
X11_LIB="$(nix build --no-link --print-out-paths nixpkgs#libx11)/lib/libX11.so.6" \
WAYLAND_DEBUG=client "$GAMESCOPE" --backend wayland --fullscreen --expose-wayland \
  --output-width 1240 --output-height 1080 -- \
  python3 plugins/gamescope/tests/nested-windows.py 2> nested.log
```

Run those build commands only on a build machine. The client maps a main window, a transient dialog, and an override-redirect popup. After
nine seconds it moves the popup beyond the output. Before upstream `c2d8f0c3`
(in 3.16.26 and later; the 3.16.18 set carried it as `0002`), Sway 1.12
on Mini V2 disconnects Gamescope with:

```text
wl_display#1.error(wp_viewport#59, 0, "wl_viewport.set_source sent with invalid values")
```

The preceding request has source size `-760 x -920`. The input thread then
calls `abort()`. This is not a touch-patch crash: the X11 repro needs no touch
input. The patched package must remain alive through `REPRO_COMPLETE` after
about 50 seconds, including 20 main-window unmap/remap cycles and 25
focus-window destroy/recreate handoffs. The popup is
visible before it moves offscreen; the main window remains visible afterward.

With the patched package on Mini V2, injecting a centre tap through its
`ft5x06` evdev device reached Sway, the nested `wl_touch` listener, and the X11
client as `XEVENT 4` then `XEVENT 5` (button press/release). A Sway-injected
mouse click produced the same X11 events. The existing `0001` is sufficient
for this path and is retained unchanged. This is synthetic input verification,
not a physical-panel or Steam/Proton session acceptance test.

### Launch handoff regression (#105)

The post-clipping-fix Steam core (2026-10-19 06:33 UTC, PID 319891) retains
`xdg_surface#51: error 3: xdg_surface has never been configured` in memory.
The shortened-gap destroy/recreate case on Mini V2 with Sway 1.12 reproduced
this on the installed package (`iw35i62ccjdirpd5z99837rpx08rnhf9`) with
`WAYLAND_DEBUG=client`:

```text
wl_display#1.error(xdg_surface#51, 3, "xdg_surface has never been configured")
```

Losing the last focus window makes Gamescope attach NULL to its host
toplevel. xdg-shell resets that toplevel's configured state on unmap.
Gamescope can attach the next game's buffer before receiving and acknowledging
a new configure. Sway disconnects it; the input thread then aborts.
Upstream `c50ddfa9` plus `6867f509` (in 3.16.31; the 3.16.18 set carried
them as `0004`) wait for configure only when an attached buffer was actually
unmapped. Patch `0002` acquires a framebuffer only after that wait, so a
skipped attachment holds no reference.
Waiting after a NULL attach before the first frame would instead leave Steam
startup blank (the upstream follow-up fixes that case). Subsurface planes do
not wait: they have no libdecor configure callback.

The regression varies handoff gaps from 20 to 320 ms. Unmap/remap alone can
retain Gamescope's old focus/held commit and does not reliably exercise the
host toplevel unmap. A pass requires `RECREATE_COMPLETE 25`, `REPRO_COMPLETE`,
a successful Gamescope exit, and no host protocol error. Confirm that buffers
are attached after the remaps too; an alive but permanently blank window is
not a pass. This synthetic test does not replace published-plugin Steam
launch acceptance.

On 2026-10-19 the final client aborted with signal 6 on its first handoff
using the installed package. With the 3.16.18 set's `0004`, two device runs each completed all
25 handoffs and 20 unmap/remap cycles with exit status 0 and no protocol error.
The host trace contained new buffer attachments in every handoff (115 and 113
toplevel buffer attachments in total), not just a live but blank process.

Building or checking this package does not publish it, grant permissions,
configure cascade enablement, install it on a device, or approve deployment.

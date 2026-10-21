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

Each key is the exact Gamescope 3.16.18 long option name in
`gamescope_options` (`src/main.cpp:58`). The korrid cascade merges `settings`
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

Integer limits come from `parse_integer` (`main.cpp:445`, `std::from_chars`
into `int`, so at most 2147483647). Float limits for `parse_float`
(`main.cpp:459`) are `FLT_MIN` 1.1754943508222875e-38 to `FLT_MAX`
3.4028234663852886e38; the built binary refuses `1e-50` and `3.5e38`.
Options that Gamescope reads with `atoi`/`atof` (the
`steamcompmgr_main` loop, `src/steamcompmgr.cpp:8103`) never fail to parse.
For those, Korri sets the limit given in the table. "Line" names the option's
entry in `main.cpp` and the code that reads its value.

| Key | Kind | Accepted values | When absent | Line |
| --- | --- | --- | --- | --- |
| `output-width` | integer | 1..2147483647, with `output-height` | Width of the `display` fact | 67; `parse_integer` 733 |
| `output-height` | integer | 1..2147483647, with `output-width` | Height of the `display` fact | 68; `parse_integer` 736 |
| `nested-width` | integer | 1..2147483647, with `nested-height` | Gamescope default | 61; `parse_integer` 724 |
| `nested-height` | integer | 1..2147483647, with `nested-width` | Gamescope default | 62; `parse_integer` 727 |
| `nested-refresh` | integer | 1..2147483 (Gamescope multiplies by 1000 in an `int`, `src/refresh_rate.h:7`) | Gamescope default | 63; `parse_integer` 730 |
| `scaler` | choice | `auto`, `integer`, `fit`, `fill`, `stretch` | Gamescope default (`auto`) | 65; `parse_upscaler_scaler` 383 |
| `filter` | choice | `linear`, `nearest`, `fsr`, `nis`, `pixel` | Gamescope default (`linear`) | 66; `parse_upscaler_filter` 401 |
| `sharpness` | integer | 0..20 (`--help`: 0 is max, 20 is min) | Gamescope default (2) | 69; `parse_integer` 796 |
| `framerate-limit` | integer | 0..2147483647; 0 disables | Gamescope default (0) | 95; `atoi`, steamcompmgr 8162 |
| `max-scale` | float | `FLT_MIN`..`FLT_MAX` | Gamescope default (no limit) | 64; `parse_float` 742 |
| `force-composition` | boolean | `true`, `false` | **`true`**: Korri adds `--force-composition` | 133; steamcompmgr 8124 |
| `adaptive-sync` | boolean | `true`, `false` | Off | 76; 813 |
| `rt` | boolean | `true`, `false`; acts only with `CAP_SYS_NICE` (846) | Off | 71; 799 |
| `fade-out-duration` | integer | 0..2147483647 (milliseconds) | Gamescope default (0) | 136; `atoi`, steamcompmgr 8142 |
| `force-windows-fullscreen` | boolean | `true`, `false` | Off | 138; steamcompmgr 8144 |
| `hdr-enabled` | boolean | `true`, `false` | Off | 142; steamcompmgr 8146 |
| `hdr-sdr-content-nits` | float | 1..10000 (the atom path treats below 1 as unset, steamcompmgr 565; 10000 nits is the PQ ceiling) | Gamescope default | 143; `atof`, steamcompmgr 8156 |
| `hdr-itm-enabled` | boolean | `true`, `false` | Off | 144; steamcompmgr 8152 |
| `hdr-itm-sdr-nits` | float | 1..1000 (the atom path clamps the same, steamcompmgr 6225) | Gamescope default (100) | 145; `atof`, steamcompmgr 8158 |
| `hdr-itm-target-nits` | float | 1..10000 (atom clamp, steamcompmgr 6234) | Gamescope default (1000) | 146; `atof`, steamcompmgr 8160 |
| `sdr-gamut-wideness` | float | 0..1 (`--help`) | Gamescope default | 141; `atof`, steamcompmgr 8154 |
| `disable-color-management` | boolean | `true`, `false` | Off | 140; 781 |
| `force-grab-cursor` | boolean | `true`, `false` | Off | 85; 809 |
| `mouse-sensitivity` | float | `FLT_MIN`..`FLT_MAX` (multiplier; 0 and negative values are refused) | Gamescope default (1.0) | 74; `parse_float` 763 |
| `default-touch-mode` | integer | 0..6: hover, left, right, middle, passthrough, disabled, trackpad (`src/backend.h:100`) | Gamescope default (1, left) | 92; `parse_integer` 790 |
| `cursor` | path | Absolute path to an image file | Host cursor | 121; steamcompmgr 8138 |
| `cursor-hotspot` | string | `X,Y`, each an integer 0..2147483647, no spaces (`sscanf "%d,%d"`) | 0,0 | 122; steamcompmgr 8140 |
| `cursor-scale-height` | integer | 1..2147483647 | Off | 123; `parse_integer` 819 |
| `hide-cursor-delay` | integer | 0..2147483647 (milliseconds) | Gamescope default (10000) | 127; `atoi`, steamcompmgr 8118 |
| `prefer-vk-device` | string | `VENDOR:DEVICE`, 1..8 hex digits each, no `0x` (`sscanf "%X:%X"`) | First qualifying GPU | 72; 801 |
| `reshade-effect` | string | A relative file name; no empty, `.` or `..` segment, no NUL | None | 151; steamcompmgr 8164 |
| `reshade-technique-idx` | integer | 0..2147483647 | Gamescope default (0) | 152; `atoi`, steamcompmgr 8166 |
| `xwayland-count` | integer | 1..2147483647 | Gamescope default (1) | 118; `parse_integer` 783 |
| `steam` | boolean | `true`, `false` | Off | 132; 766 |
| `virtual-connector-strategy` | choice | `SingleApplication`, `SteamControlled`, `PerAppId`, `PerWindow` | `SingleApplication`; `SteamControlled` with `steam` | 124; 827 |
| `borderless` | boolean | `true`, `false` | Off | 82; 751 |
| `disable-xres` | boolean | `true`, `false` | Off | 135; steamcompmgr 8127 |
| `allow-deferred-backend` | boolean | `true`, `false` | Off | 157; 823 |

`steam` comes before `virtual-connector-strategy` in the order. `--steam`
changes a `SingleApplication` strategy to `SteamControlled` (`main.cpp:766`),
so an explicit strategy must come after it. Gamescope ignores an unknown
strategy name (`main.cpp:827`); Korri refuses it.

Gamescope looks for `reshade-effect` in
`$HOME/.local/share/gamescope/reshade/Shaders/` and then
`/usr/share/gamescope/reshade/Shaders/` (`src/reshade_effect_manager.cpp:970`).
This package ships no shaders. Gamescope reads `cursor` with `stbi_load`
(`steamcompmgr.cpp:7453`). Gamescope is the main process of the game's session
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

These Gamescope 3.16.18 options have no typed setting. `config.append` still
passes them to Gamescope. All 82 options are accounted for: 38 typed, 3 fixed,
41 here.

| Options | Reason |
| --- | --- |
| `backend`, `fullscreen`, `expose-wayland` | Korri always passes them. |
| `help`, `version` | Gamescope exits before it starts the game. |
| `ready-fd`, `stats-path` | Gamescope opens or writes the named path (`steamcompmgr.cpp:8107`, 8110). Korri owns readiness and diagnostics. |
| `prefer-output`, `force-orientation`, `generate-drm-mode` | Inert under `--backend wayland`; read only in `Backends/DRMBackend.cpp` (1304, 2172, 3263). |
| `display-index`, `nested-unfocused-refresh` | Inert under `--backend wayland`; read only in `Backends/SDLBackend.cpp` (258, 847). SDL runs only if the Wayland backend cannot start (`main.cpp:939`). |
| `immediate-flips` | Inert under `--backend wayland`; tearing needs `SupportsTearing()` (`steamcompmgr.cpp:8829`), which is `false` for Wayland (`WaylandBackend.cpp:2279`). |
| `grab` | Inert under `--backend wayland`; it only adds " (grabbed)" to the window title (`WaylandBackend.cpp:1244`). The keyboard grab is SDL-only (`SDLBackend.cpp:253`). |
| `fsr-sharpness` | The same variable as `sharpness` (`main.cpp:796`). Two keys for one value would let argv order, not the cascade layer, choose the value. Use `sharpness`. |
| `keep-alive` | Gamescope stays alive after the game exits (`main.cpp:825`). Gamescope is the session unit's main process, so the session would not end with the game (Core ADR 0007). |
| `mangoapp` | Gamescope starts `mangoapp` from `PATH` (`steamcompmgr.cpp:8082`). This package ships no `mangoapp`. |
| `mura-map` | Steam Deck panel calibration: a path prefix for `_red.png` and `_green.png` (`steamcompmgr.cpp:670`). No Korri device has a mura map. |
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
then reads `gamescope_options` from the patched `src/main.cpp` and requires 82
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

`package.nix` still asserts Gamescope 3.16.18. Its options and values were
checked in upstream `src/main.cpp` and `src/steamcompmgr.cpp` at that version. Nixpkgs' packaging and
system-library patches stay intact. These additional patches are applied:

| Patch | Source and reason |
| --- | --- |
| `0001` | Unchanged ROCKNIX nested Wayland `wl_touch` patch (ValveSoftware/gamescope#1606), copied from Korri `b22b82d6a24e6164846ad97adb347e783579b531`. |
| `0002` | Unchanged upstream `c2d8f0c33266e36f8d91978171ba74a7cbd8a2e4`: skip planes that clip to zero or negative size. |
| `0003` | ROCKNIX `0024-WaylandBackend-acquire-only-attached-buffers.patch`, adapted to 3.16.18's `Unwrap` API. Acquire framebuffers at attachment, not before clipping, so skipped planes do not retain references waiting for a release that cannot arrive. |
| `0004` | Upstream `c50ddfa9b71a75ec8df94bda8cf31d425dbdda24` plus `6867f509874f9bc52e12d6f4c4596cdf0d5be6b4`: after a real toplevel unmap, wait for a new configure before attaching another buffer. Adapted around `0003` so skipped attachments do not acquire framebuffers. |
| `0005` | Korri-local. Enable `VK_EXT_robustness2` only if `nullDescriptor` is supported. Without it, bind 1x1 images (2x2 for YCbCr) to unused descriptor slots, and the shader treats a 1-texel shaper LUT as absent. panvk before v10 has no `nullDescriptor`, so `vkCreateDevice` failed. |
| `0006` | Korri-local. Bind the constants UBO with the uploaded struct's size, not `VK_WHOLE_SIZE`. The whole-size range covers the rest of the 8 MB upload buffer, beyond `maxUniformBufferRange`. panvk v7's 12-bit UBO entry count wrapped and every composite was black. |
| `0007` | Korri-local. If no `HOST_VISIBLE`, `HOST_COHERENT`, `HOST_CACHED` memory type fits a mappable image, retry without `HOST_CACHED`. panvk has no cached coherent type. |
| `0008` | Korri-local. Do not start the `gamescope-shdr` precompile thread. Its keys do not match the runtime keys, `pipeline()` compiles on first use, and on the RG353M it held one core at about 100% for over a minute. |
| `0009` | Korri-local. If no GPU qualifies, opt in to Mesa panvk for Bifrost from Gamescope's own process, retry once, then remove the opt-in from the environment. Prefer a GPU to a CPU device (llvmpipe). Details below. |

Patch `0003`'s ROCKNIX source was reviewed at distribution commit
`8d6ef76cf7bd13a44538e5ef45aa97c3937e2d18`, under
`projects/ROCKNIX/packages/apps/gamescope/patches/0024-*`. No other ROCKNIX
patches are included. The patches change neither the Gamescope version nor its options.

### Mali Bifrost (RG353M) and other GPUs

`0005` to `0009` are Korri-local. They are not upstream and were not sent
upstream. They make the same package run on the RG353M (Mali-G52, Mesa
26.2.3 panvk, architecture v7) with no device configuration.

Mesa panvk refuses v6/v7 GPUs unless `PAN_I_WANT_A_BROKEN_VULKAN_DRIVER` is
set. It reports Vulkan 1.0 on v7 unless `MESA_VK_VERSION_OVERRIDE` is set.
Gamescope needs 1.2. Without both, only llvmpipe qualifies, and Gamescope
aborts on it. `0009` changes device selection as follows:

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

`0005`, `0007` and `0009` change behaviour only where upstream fails: no
`nullDescriptor`, no cached coherent memory type, or no qualifying GPU.
`0005` also changes the shader for every GPU: a real shaper LUT has 4096
texels, so the added size check is true wherever upstream's check is true.
`0006` and `0008` run on every GPU. `0006` replaces invalid usage
(`VUID-VkWriteDescriptorSet-descriptorType-00332`) with a range of at most
16384 bytes, which every conformant driver must accept; a `static_assert`
keeps each constants struct within that size. `0008` changes only when
pipelines compile, not which pipelines run.

Adreno (Turnip) on Retroid Pocket Mini V2 and AYN Odin 2 Portal has not run
this package. Its Vulkan driver qualifies on the first pass, so only `0005`'s
shader change, `0006` and `0008` apply there.

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
nine seconds it moves the popup beyond the output. Before `0002`, Sway 1.12
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
`0004` waits for configure only when an attached buffer was actually unmapped.
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
using the installed package. With `0004`, two device runs each completed all
25 handoffs and 20 unmap/remap cycles with exit status 0 and no protocol error.
The host trace contained new buffer attachments in every handoff (115 and 113
toplevel buffer attachments in total), not just a live but blank process.

Building or checking this package does not publish it, grant permissions,
configure cascade enablement, install it on a device, or approve deployment.

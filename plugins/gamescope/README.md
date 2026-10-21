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

The command is the manifest's named `files.gamescope`. Arguments are:

1. `--backend wayland --fullscreen --expose-wayland`.
2. Typed settings in the table's order.
3. Words from `config.append`.
4. `--`, then the runner command and its arguments.

| Setting | Accepted values |
| --- | --- |
| `output-width`, `output-height` | Positive integers, supplied together |
| `nested-width`, `nested-height` | Positive integers, supplied together |
| `nested-refresh` | Positive integer |
| `scaler` | `auto`, `integer`, `fit`, `fill`, `stretch` |
| `filter` | `linear`, `nearest`, `fsr`, `nis`, `pixel` |
| `sharpness` | Integer 0..20 |
| `framerate-limit` | Integer >= 0 |

Each setting maps to the same-named long flag and one value. Integers must be
exactly representable in JavaScript. Unknown settings, bad types, invalid
values, and unpaired dimensions refuse composition. If output dimensions are
absent, both dimensions come from the supplied logical `display` hardware
fact. Without either source, composition refuses the launch.

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
and the native binary's `--version` and `--help`. It does not start a nested
compositor or establish display, touch, controller, audio, or frame-rate
acceptance on hardware. The current pinned Core predates modifier admission
and execution. Host integration must be verified when Core lands that support.

`package.nix` still asserts Gamescope 3.16.18. Its flags and enum values were
checked in upstream `src/main.cpp` at that version. Nixpkgs' packaging and
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
patches are included. There is no Gamescope version change or launch-flag change.

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

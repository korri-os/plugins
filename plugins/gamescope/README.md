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

Patch `0003`'s ROCKNIX source was reviewed at distribution commit
`8d6ef76cf7bd13a44538e5ef45aa97c3937e2d18`, under
`projects/ROCKNIX/packages/apps/gamescope/patches/0024-*`. No other ROCKNIX
patches are included. There is no Gamescope version change or launch-flag change.

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
about 97 seconds, including 20 main-window unmap/remap cycles. The popup is
visible before it moves offscreen; the main window remains visible afterward.

With the patched package on Mini V2, injecting a centre tap through its
`ft5x06` evdev device reached Sway, the nested `wl_touch` listener, and the X11
client as `XEVENT 4` then `XEVENT 5` (button press/release). A Sway-injected
mouse click produced the same X11 events. The existing `0001` is sufficient
for this path and is retained unchanged. This is synthetic input verification,
not a physical-panel or Steam/Proton session acceptance test. The original
Steam core dumps have no retained protocol log, so their exact error cannot
be confirmed from those dumps alone.

Building or checking this package does not publish it, grant permissions,
configure cascade enablement, install it on a device, or approve deployment.

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

`package.nix` asserts the pinned Nixpkgs version is 3.16.18. Its flags and enum
values were checked in upstream `src/main.cpp` at that version. Nixpkgs'
packaging/system-library patches stay intact. The only added patch is ROCKNIX
0001 for nested Wayland `wl_touch` (ValveSoftware/gamescope#1606), copied
unchanged from Korri commit `b22b82d6a24e6164846ad97adb347e783579b531`.
No other ROCKNIX patches are included.

Building or checking this package does not publish it, grant permissions,
configure cascade enablement, install it on a device, or approve deployment.

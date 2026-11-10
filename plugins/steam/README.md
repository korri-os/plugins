# Steam

The `@korri:steam/steam` runner admits system `steam` and passes the selected
provider `ref` to the packaged `steam-session <appid>` program. It declares
`STEAM_HOME=${accountRoot}/steam` and that directory. `plugin.ts` performs no
effects.

## Launch steps

This declaration requires a korrid with runner steps support (korri #387).
Older runner declaration decoders do not accept `steps`.

| Key | Label | Reached when |
|---|---|---|
| `start-steam` | Starting Steam | Preparing the seed and starting the client |
| `update` | Updating Steam | A startup update or update restart is observed |
| `sign-in` | Signing in | The client reaches the login gate after startup updates |
| `install` | Installing the game | Steam acts on an AppID that is not installed |
| `answer` | Waiting for your answer in Steam | Steam reports `LaunchApp waiting for user response`, such as a EULA |
| `game` | Starting the game | Steam reports `CreatingProcess` for the AppID, or a game process is added |

The session sends `STATUS=korri-step: <key>` through `systemd-notify` only
when `NOTIFY_SOCKET` is set. Steps only move forward; unused steps are skipped.
An AppID forward is only a request, not proof that the game is starting:
Steam can still ask for installation or a EULA. Retries and client restarts
do not repeat earlier steps. The game unit must allow `NotifyAccess=all`.
korrid ends these steps at the initial game handoff. The declaration build check
compares the native session's ordered keys and labels with the runner declaration.
A change to only one side fails the package's publication gate.

## Launch refusals

Before a failed launch exits, the session sends `STATUS=plugin-launch: <reason>`
through the same notification socket. korrid uses this existing status as the
refusal on each client; there is no new treaty field.

The session reads only bytes written during this session in `console_log.txt`,
`content_log.txt` and `gameprocess_log.txt` below `STEAM_HOME/logs`. It accepts
only lines for the selected AppID. Known Steam launch and download errors become
short fixed messages: ownership, platform availability, missing executable,
disk space/read/write errors, corrupt downloads and connection failures. An
`Update Required` app state explains a timed-out launch but does not stop a
working download. Suspended updates and helper process exit codes are not
launch errors. A `LaunchApp failed` event ends the wait immediately.

The status never copies raw log text, paths or account IDs. Unknown launch errors
use a generic Steam launch-error message. With no recognized Steam diagnostic,
it reports the last launch step's label plus “failed”. Client exit and the
10-minute sign-in timeout have their own plain messages. Notification failure
does not change the exit code or skip Steam cleanup. Unknown Steam wording can
therefore lose detail; it cannot expose arbitrary log content.

## Runtime

`plugin.nix` requires the exact `@korri:fex` and `@korri:proton` outputs, and
the runner lists their artifacts, `@korri:fex/rootfs` and
`@korri:proton/cachyos`. korrid downloads, verifies and unpacks those before
it starts the runner (ADR 0012); see `plugins/fex/README.md` and
`plugins/proton/README.md`. The FEX rootfs exists for `aarch64-linux` only, so
an x86_64 device skips it (Core ADR 0052). `launch.prepare` refuses the launch
unless korrid supplies the Proton directory, and the FEX config file whenever
it supplies the FEX rootfs. It passes them to the session program:

| Variable | Launch input |
|---|---|
| `KORRI_FEX_CONFIG` | `files["@korri:fex/config"]` |
| `KORRI_FEX_ROOTFS` | `artifacts["@korri:fex/rootfs"]` |
| `KORRI_PROTON_CACHYOS` | `artifacts["@korri:proton/cachyos"]` |

The FEX variables are set only when korrid supplied the FEX rootfs.

One plugin serves both architectures; `packages/default.nix` builds the
session for its platform:

| | ARM64 (RP Mini V2) | x86_64 (aka) |
|---|---|---|
| Client | Valve's ARM64 client, seeded into the Steam home and run from the package's own FHS | nixpkgs' Steam FHS, with the same input guard preloaded |
| FEX | Required: config and rootfs | None |
| Proton | Proton-CachyOS arm64 | Proton-CachyOS x86_64 |
| Channel | `steamdeck_stable`, with the manifest repair below | Steam's public channel |
| Scaling | `-forcedesktopscaling 1.5` | none |

On x86_64 the session points `~/.steam/steam`, `~/.steam/root` and
`~/.local/share/Steam` at `STEAM_HOME`, so Valve's bootstrap starts, or
installs, the client there. It refuses to start if one of them is a separate
directory.

`steam-session` refuses with status 2 if a required path is missing or is not a
directory.
The session sets `FEX_ROOTFS` to the rootfs directory and
`FEX_APP_CONFIG_LOCATION` to the FEX plugin's `config` directory. On every
launch it links `compatibilitytools.d/proton-cachyos-11.0-20260601-slr-arm64`
to the Proton directory; the seed does not. The seed still downloads Valve's
unpinned arm64 client into the Steam home on first run. The manual sign-in
window starts after the seed and settings steps. The session program still
owns the Steam client, its FHS environment and the Steam settings.

Provisional slice decisions: Flinthook (401710), Valve's arm64 Steam client,
Proton-CachyOS `proton-cachyos-11.0-20260601-slr-arm64` and FEX. Steam runs under
Sway/Xwayland without gamescope. Steam Input is off; the game uses Korri Seat P1.
Steam stops with the game session. The existing game-unit sandbox is unchanged.

The current catalog is `catalog/library.yaml`: a release uses `system: steam`
and `identity: {kind: provider, value: '@korri:steam/401710'}`. Its `device.yaml`
location is `{provider: '@korri:steam', ref: '401710'}` under that identity key.
These reuse the existing provider release-key and location shapes.

No discovery, installation flow, sign-in automation, typed settings, raw config
overrides, other games or session controls are implemented by this slice.
Sign-in, when needed, remains a manual step in Steam.

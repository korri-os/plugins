# Steam

The plugin's `steam` runner admits system `steam` and passes the selected
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
korrid ends these steps at the initial game handoff. The package generates the session's
ordered keys and labels from `runners.steam.steps`. The subprocess tests drive a
full launch through fixture logs and compare its emitted statuses with that
declaration. No hand-kept native step list or label list remains.

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

## Settings

Both runners have two typed settings in the plugin bucket (Core ADR 0037,
ADR 0083): `plugin.proton` and `plugin.fex`. Each value is the id of an
artifact the runner names. Each list has one entry today,
`@korri:proton/cachyos` and `@korri:fex/rootfs`, and the first entry is the
default. They are set like any launch setting, for the device, a runner or one
game:

```sh
korri launch-settings set plugin.proton @korri:proton/cachyos --game <game>
```

Another Proton or FEX version is one more artifact of that plugin and one
more entry in `PROTON_CHOICES` or `FEX_CHOICES` in `plugin.ts`. A value that
is not in the list is skipped with a launch warning, and the default applies.

## FEX and Proton must be installed and on

The runners name `@korri:fex/rootfs` and `@korri:proton/cachyos`, so the FEX
and Proton plugins must be installed and enabled, on x86_64 too: there the FEX
plugin is what tells korrid that the rootfs is not for this platform. While
one of them is off, both runners are off and korrid logs
`runner @korri:steam/engine is off: no enabled plugin provides <artifact>`.

A device that moves Steam from a release that required the exact FEX and
Proton packages (before `build-85abd07f2d57-steam-engine-14`) to a later one
must turn FEX and Proton on afterwards. The plugin host had them on only as
Steam's requirements and turns them off when Steam stops requiring them
(seen on aka, 2026-11-24):

```sh
korri-plugin enable @korri:fex
korri-plugin enable @korri:proton
```

## Runtime

The runners list the artifacts `@korri:fex/rootfs` and
`@korri:proton/cachyos`. `plugin.nix` requires no exact `@korri:fex` or
`@korri:proton` output (Core ADR 0083): korrid resolves each artifact from
the enabled plugin that declares it and passes that plugin's files, so each of
the three plugins moves to a new release by itself. A runner is off, and says
which artifact it lacks, while no enabled plugin declares one of them. Both
session programs read Proton's tool name from the ready folder's
`compatibilitytool.vdf` at launch. korrid downloads, verifies and unpacks those before
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
and `identity: {kind: provider, value: '<plugin id>/401710'}`. Its `device.yaml`
location is `{provider: '<plugin id>', ref: '401710'}` under that identity key.
These reuse the existing provider release-key and location shapes.

No discovery, installation flow, sign-in automation, typed settings, raw config
overrides, other games or session controls are implemented by this slice.
Sign-in, when needed, remains a manual step in Steam.

## Engine runner (`engine`, Core ADR 0083)

`plugin.ts` declares full ids, as the published `@korri:fex` and
`@korri:proton` do: runners `@korri:steam/steam` and `@korri:steam/engine`,
artifact `@korri:steam/engine-package`, discovery
`@korri:steam/installed-apps`. They are built from one constant, `PLUGIN_ID`.
A sideloaded test build under another publisher rewrites that one line in
its own scratch copy; the repository keeps `@korri`.

A second, opt-in runner that plays Steam games through Valve's engine
(`steamclient.so`) with no Steam client and no Steam UI. The client runner
above stays the default. It runs on aarch64-linux and x86_64-linux; each
platform has its own engine package from Valve and its own engine map.

| Part | Where |
|---|---|
| Runner, steps `update`, `sync`, `game` | `plugin.ts` `runners.engine` |
| Engine package `@korri:steam/engine-package` (for client 1792618285, by name and `sha2vz`; no `unpack`): Valve's `bins_sdk_linuxarm64_linuxarm64` on aarch64-linux, `bins_sdk_ubuntu12` on x86_64-linux | `plugin.ts` `artifacts` |
| Valve's `legacycompat/` folder `@korri:steam/legacycompat` (Valve's `bins_misc_linuxarm64` or `bins_misc_ubuntu12` for client 1792618285, one file under two names, by name and `sha2vz`; unpack program `steam-legacycompat-unpack`) | `plugin.ts` `artifacts`, `engine/legacycompat-unpack.py` |
| The Steam provider `@korri:steam`, the plugin's own id (korrid serves search and listing from `list-apps`) | korrid |
| `korri-steam-host` (Rust, from an engine map) | `engine-host/`, `packages/engine-host.nix` |
| Its start wrapper: the person's engine folder, then the host in the Steam FHS | `engine/host-run.sh` |
| `steam-engine-session <appid>`: the game unit's program | `engine/session.sh`, `engine/launch-entry.py`, `engine/x-placeholder.py` |

The engine map is the flake input `steam-engine-map`: a folder with one map
per system, `aarch64-linux/engine.map` and `x86_64-linux/engine.map`. A host
is built from the map of the system it runs on. The public maps
(`engine-host/map/<system>/engine.map`) are empty, and a host built from one
reports `{"event":"engine_map_missing"}` and exits 1. The pinned engines'
maps are made privately on aka and are in no repository; a real build passes
them with `--override-input steam-engine-map path:<folder>`. At start the host compares
the engine file's sha256 with the map's and reports `engine_mismatch` on a
difference, before it loads the engine.

The person's folder is `<account root>/steam-engine`: `steam/` is the Steam
root the engine writes (its own `config/config.vdf` and `local.vdf`), `home/`
is HOME, and `home/.steam/{steam,sdkarm64}` are links. The wrapper links the
engine file and korrid's Proton into it and merges only the compat-tool
mapping into the engine's config. It names `steam/compatibilitytools.d` in
`STEAM_EXTRA_COMPAT_TOOLS_PATHS`. The engine looks for that folder beside the
`steamclient.so` it was loaded from, in korrid's cache. Without the variable it
never registers the pinned Proton, so the mapping reads back empty and Windows
builds do not install (korri#531). It grants the account root's owner reading
of `steam/steamapps/appmanifest_*.acf`, as the client runner does.

The launch channel `$KORRI_STEAM_ENGINE_CHANNEL` holds `commands` (the host's
FIFO), `session.lock`, `host.lock`, `events.jsonl` (the host's stdout) and
`saves/` (the `save_export` archives). The session program takes the session
lock, sends `install`, then `launched`, starts no game on a Steam Cloud
`conflict` (`STATUS=plugin-launch: steam-cloud-conflict`), plays the game
through Proton with the x-placeholder window, and sends `exited`.

### The end of a session and the device's name (korri#595)

Steam hears that a game session ended only from `Cloud.SignalAppExitSyncDone`.
The engine sends it at the end of every sync job that has the `up` bit, also
when there is nothing to upload. So the exit sync always ends with one
`SynchronizeApp` upload call, as Valve's client ends it: with nothing to upload
(state 2, or 4 with only remote changes) the call is the exit notice
(`cloud_call` with `"exit_notice":true`). States 6 and 7 still upload
nothing. Without the notice Steam kept the session as an `UploadPending`
operation "from machine ''" and refused the next launch's download.

korrid passes the device's Korri title as `KORRI_STEAM_DEVICE_NAME`. The host
uses it as the QR sign-in's device name and, before the logon, as the engine's
machine name (`IClientUser::SetUserMachineName`, a map entry since korri#595),
which Steam shows for this device's cloud operations. Without the variable the
host sets no machine name.

### Another device's save is still uploading (Core ADR 0083, 2026-11-21)

The launch sync is always one `AC Launch,down,` job, also with nothing to
download: its launch intent is how Steam says that another device has a
session open or a save not uploaded yet. Steam then refuses the download. The
engine keeps those operations only in an object the host cannot read, so the
host reads the two lines the job writes to `steam/logs/cloud_log.txt`
(`src/pending.rs`): only bytes written after the call, at most 1 MiB, also
across a rotation to `cloud_log.previous.txt`. A report it cannot read, or a
log it cannot open, counts as a pending operation of an unknown device.

The host then reports
`{"event":"cloud_pending","appid":N,"operations":[{"operation":"upload_pending","machine":"Living room"}]}`
(`machine` only when Steam names one) and the launch waits, with no time limit,
for korrid's answer: `retry <appid>` evaluates and asks Steam again,
`play-anyway <appid>` downloads with the engine's `ignore pending` flag. The
host confirms with `cloud_pending_answered`, and the launch limit starts again.
The session program waits with no limit while the question is open; korrid
stops the game unit when the person cancels.

### Steamworks games: `legacycompat` (korri#589)

A Steamworks game's `steam_api` loads the `steamclient.dll` or
`steamclient64.dll` that the registry names in
`C:\Program Files (x86)\Steam`. Proton copies both from
`$STEAM_COMPAT_CLIENT_INSTALL_PATH/legacycompat/` into the prefix. Proton's
ntdll then loads `lsteamclient` and overwrites each export of that Valve DLL
with a jump into lsteamclient. lsteamclient loads
`$HOME/.steam/sdkarm64/steamclient.so` (aarch64-linux) or
`$HOME/.steam/sdk64/steamclient.so` (x86_64-linux; `sdk32` for a 32-bit
lsteamclient), the engine library, which reaches the running host. An engine-only folder has no client and so no
`legacycompat/`: without it the game reports that it cannot load
`steamclient.dll`.

Valve's `bins_misc_linuxarm64` package of the same manifest carries the
folder (on x86_64-linux the same file is named `bins_misc_ubuntu12`). In that package `legacycompat\steamclient.dll`,
`legacycompat\steamclient64.dll` and `legacycompat\GameOverlayRenderer64.dll`
are symbolic links to files at the package root. korrid's own archive reader
refuses links, so the artifact names the plugin's unpack program.
`steam-legacycompat-unpack <work-dir> <package>` decodes the VZ package and
writes only `<work-dir>/legacycompat/`, each link as a copy of its target. It
refuses a link to any other place and a package without `steamclient.dll`,
`steamclient64.dll` and `Steam.dll`. `steam-engine-session` links
`steam/legacycompat` to the ready folder (`KORRI_STEAM_LEGACYCOMPAT`) before
each launch. It replaces only a link, and refuses the launch if the folder is
missing or `steam/legacycompat` is a real folder.

The engine also makes `steamapps/common/Steam.dll`, a link to
`legacycompat/Steam.dll` beside the engine package in korrid's cache. That
link stays broken: the engine package is a separate artifact.

### The private engine map in publication

The published `@korri:steam` carries the pinned engine's map compiled into
its engine host (ADR 0083: the map "ships only with the prebuilt engine
host"). The map file is in no repository and in no published closure.

- **Secret.** `STEAM_ENGINE_MAP_TGZ_B64`, a repository Actions secret of
  korri-os/plugins: base64 of `tar czf` of the map folder, whose files are
  `aarch64-linux/engine.map` and `x86_64-linux/engine.map` (the layout of
  `engine-host/map`). `setup` refuses an archive with any other file or
  without one of the two.
- **Use.** The build jobs of `plugin-repository.yml` and
  `publish-core-main-cache.yml` run `.github/workflows/steam-engine-map.py
  setup` before any build. It unpacks the map to `$RUNNER_TEMP/steam-engine-map`
  (0700, the file 0600), outside the checkout, and puts a `nix` shim first on
  PATH that adds `--override-input steam-engine-map path:<folder>` to every nix
  command on this flake. Without the secret (forks, pull requests) nothing
  changes and the host builds with the empty public map, so it reports
  `engine_map_missing`. Nothing prints the secret or the map. Nix's
  "not writing modified lock file" warning names the folder and the map's
  narHash, not its content.
- **Check.** After the build, `steam-engine-map.py check-closure` fails the job
  if the map's store path, or the host build's copy of it
  (`…-korri-steam-engine-map`), is in the runtime closure of the paths it
  uploads (`korri-cache export` copies exactly that closure). The host build
  reads the map from that content-named copy, so a change to another file of
  this repository does not rebuild the host. The compiled host binary
  holds the map's addresses by design.
- **Host check.** `steam-engine-map.py check-host <system>` then fails the job
  if the upload closure holds a `korri-steam-host` other than the one the shim
  evaluates from the private map, and names the empty public map's host when
  it finds it. Without the private map, any engine host in the closure fails
  the job. The shim covers only a `nix` that it precedes on PATH; a tool that
  puts its own nix first bypasses it. `korri-cache` therefore runs the
  caller's nix and uses its own only when there is none. Before this, the
  release `build-fecbea69dc50-steam-engine-2` shipped the public-map host:
  `korri-cache build` evaluated without the override, and the closure check
  passed because a public-map host holds no map path.
- **Update when the engine pin moves.** On aka, make each system's map for
  the new client version with the private pipeline
  (`/var/lib/korri-private/steam-engine/make-map <version> <system> <steamclient sha256>`,
  once for `aarch64-linux` and once for `x86_64-linux`), change the artifact
  pins in `plugin.ts`, then replace the secret from the new folder, piped so
  no file or output holds the value:

  ```sh
  ssh root@aka 'tar -C /var/lib/korri-private/steam-engine/<version> -czf - aarch64-linux/engine.map x86_64-linux/engine.map | base64 -w0' \
    | gh secret set STEAM_ENGINE_MAP_TGZ_B64 -R korri-os/plugins
  ```

  The x86_64 map is derived by the same program from the x86_64 library. Its
  slot numbers must equal the aarch64 map's of the same client version;
  `make-map` checks that.

  A host built from a map that does not match the pinned engine refuses to
  start (`engine_mismatch`), so the secret and the pin move in the same
  publication.

Checks: `korri-steam-engine-host` (rustfmt, unit tests, clippy and the
`engine_map_missing` start with the empty map), `korri-steam-source` (the
session program's tests), `korri-steam-declaration` and `korri-steam-package`.
The aarch64 cross-builds with the public and the private maps run on aka
(`korri-steam-host-aarch64`), as does the native x86_64 host with the private map.

# Steam

The `@korri:steam/steam` runner admits system `steam` and passes the selected
provider `ref` to the packaged `steam-session <appid>` program. It declares
`STEAM_HOME=${accountRoot}/steam` and that directory. `plugin.ts` performs no
effects.

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

# Skate 3

`@korri:skate-3` is a native launcher for the existing library game. It does not
create a separate game tile. Core must support runner `releases`, introduced
in `korri-os/korri` commit `13a074832`.

## Native package

The x86_64-only output is `korri-plugin-skate-3`. It uses the prebuilt `skate3`
launcher from `simonwjackson/skate-3-flake`, pinned at
`e309e451f644eab95490c8e7c4bab9de398cda40`. That flake fetches upstream
`Skate3Recomp-Linux.zip` v2.0.2 and patches its library paths. It does not
compile game executables or include disc assets. No ARM output is provided.

`plugin.nix` names that package and its executable. `plugin.ts` declares the
runner and returns a launch plan. Neither declaration reads, hashes, writes,
downloads, or starts anything. Core performs the launch effects. The native
game installs and downloads its title update after launch.

Upstream publishes no redistribution license. The native binary contains
code generated from EA's game. Do not publish this closure to the public
plugin cache without a separate rights review and approval. A local build
and an admission check grant no publication or device installation approval.

## Accepted disc

The runner accepts this measured whole-file identity:

| Disc | Bytes | SHA-256 |
|---|---:|---|
| Skate 3 (USA, Europe) (En,Fr,De,Es,It,Nl).iso | 7838695424 | `bd8d430188aa61b0ebf2e33e5672822dd7e59c9080fc09e802195e1ee75ebff0` |

The measurement streamed the one ISO inside the owner's
`~/Downloads/Skate 3 (USA, Europe) (En,Fr,De,Es,It,Nl).zip` on aka. Python's ZIP
reader checked its CRC while reading. The archive stayed unchanged and no
ISO was extracted to disk. This is not the archive hash or the game's XEX
hash. Other dumps are not accepted until measured and verified.

The field follows Core's `RunnerRecord.releases` and existing
`config::ArtifactIdString` validator. Several accepted entries would mean
any one dump. The namespace follows this publisher's existing `@korri`
composition. Native launch variables come from the pinned flake's
`launcher.nix`, not a new Korri configuration schema.

## Launch and limits

Core passes the matched file through `PluginLaunchInput.contentPath`. The
callback sets `SKATE3_INSTALL_ISO` to that exact path and sets
`SKATE3_INSTALL_TU=download`. The native launcher handles writable game data,
logs, first-run windowing, and library paths. The game needs internet for its
first title-update download and a working Vulkan driver at
`/run/opengl-driver`. Later launches reuse the installed game files.

Discovery needs the bare `.iso` in an existing library folder. The ZIP is
not discoverable through this claim. The claim assigns `.iso` to `xbox-360`;
a different system claiming `.iso` still causes Core's `ClaimConflict`.
There is no archive extraction, hash-based discovery, launch-time rehashing,
or ARM build in this plugin.

## Build and verify

Run these commands on a build machine, never on a device:

```sh
nix build --no-link .#korri-plugin-skate-3
nix build --no-link .#checks.x86_64-linux.korri-skate3-plugin
```

The check uses the actual packaged source. It typechecks against Core's
exported contract, checks the generated manifest and measured hash, runs
host admission, and invokes the production sandboxed callback and launch
executor with the real `env` program. Paths with spaces and shell syntax
must reach `SKATE3_INSTALL_ISO` unchanged. The check performs no game
installation or download. It does not establish gameplay, controller, or
device acceptance. Installation still needs a compatible Core runtime,
normal signature and permission checks, and a selected device.

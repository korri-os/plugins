# Korri plugins

This repository publishes prebuilt Linux plugins through a signed Nix cache on
GitHub Releases. Devices download exact store outputs. They never compile them.

Core supplies the supported builder and generated launch contract. This
repository owns its Nixpkgs and flake-utils inputs, initially locked to the
same revisions previously consumed through Core. Plugin builds do not use
Core's Rust overlay or host binaries. Host admission and lifecycle checks use
Core's own host composition, separately from plugin builds.

This ownership move changes neither devices nor releases. Publication and
physical-device acceptance need separate approval. Batch 3 validation uses a
candidate Core input override. Before production use, update the GitHub lock to
the reviewed, reachable Core revision that exports the new interface.

## Packages

| Flake output (`packages.<system>`) | Plugin | Source |
|---|---|---|
| `korri-tailscale` | `@korri:tailscale` | `plugins/tailscale/` |
| `korri-plugin-retroarch` | `@korri:retroarch` | `plugins/retroarch/` |
| `korri-plugin-<core>` | `@korri:<core>` | Generated from `plugins/libretro/cores.nix` |
| `korri-plugin-solarus` | `@korri:solarus` | `plugins/solarus/` |
| `korri-plugin-eden` | `@korri:eden` | `plugins/eden/` |
| `eden` | Standalone Eden 0.2.1 launcher | `plugins/eden/` |
| `korri-plugin-bitsybox` | `@korri:bitsybox` (restricted license; publication blocked) | `plugins/bitsybox/` |
| `bitsybox` | Standalone native Bitsybox 0.2-8.12, single-file CLI | `plugins/bitsybox/` |
| `solarus` | Standalone Solarus 2.1.4 engine | `plugins/solarus/` |
| `korri-plugin-cemu` | `@korri:cemu` (Wii U) | `plugins/cemu/` |
| `cemu` | Standalone Cemu main with offline Github989 graphic packs | `plugins/cemu/` |
| `korri-plugin-gamescope` | `@korri:gamescope` | `plugins/gamescope/` |
| `gamescope` | Standalone Gamescope 3.16.31 with nested Wayland touch | `plugins/gamescope/` |
| `korri-plugin-starter-pack` | `@korri:starter-pack` | `plugins/starter-pack/` |
| `korri-plugin-pico8` | `@korri:pico8` (PICO-8 BBS search provider; declared host `www.lexaloffle.com`) | `plugins/pico8/` |
| `korri-plugin-itchio` | `@korri:itchio` (supported-creator free raw Bitsy attachments; finite exact hosts) | `plugins/itchio/` |
| `korri-plugin-tic80gallery` | `@korri:tic80gallery` (TIC-80 catalog provider) | `plugins/tic80gallery/` |
| `korri-plugin-wasm4gallery` | `@korri:wasm4gallery` (WASM-4 gallery provider) | `plugins/wasm4gallery/` |
| `korri-plugin-lowresnxgallery` | `@korri:lowresnxgallery` (LowRes NX programs provider) | `plugins/lowresnxgallery/` |
| `korri-plugin-puzzlescript` | `@korri:puzzlescript` (raw-source gallery provider) | `plugins/puzzlescript/` |
| `korri-plugin-pyxelgallery` | `@korri:pyxelgallery` (versioned official sample catalog provider) | `plugins/pyxelgallery/` |
| `korri-plugin-pyxel` | `@korri:pyxel` (native `.pyxapp` runner candidate) | `plugins/pyxel/` |
| `korri-plugin-homebrewhub` | `@korri:homebrewhub` (declared games with pinned artifacts) | `plugins/homebrewhub/` |
| `korri-plugin-retrobrews` | `@korri:retrobrews` (declared games with pinned artifacts) | `plugins/retrobrews/` |
| `starter-pack-cartridges` | Standalone content payload | `plugins/starter-pack/` |
| `korri-plugin-ssh` | `@korri:ssh` | `plugins/ssh/` |
| `korri-plugin-sunshine` | `@korri:sunshine` | `plugins/sunshine/` and `services/sunshine/` |

Sunshine is a build candidate. Do not publish it until the ARM build and
plugin lifecycle gates pass. Its presence in a release does not establish
streaming acceptance.

Supported systems are `x86_64-linux` and `aarch64-linux`. Publisher composition
binds `korri.lib.<system>.mkPlugin { pkgs = publisherPkgs; }`. The catalogue emits one package per core entry. Each core package carries its selected RetroArch frontend and
core library in one closure. Nix deduplicates identical store paths.

## Native fantasy-console candidates

Runners and acquisition providers are independent plugins. Local play needs
only the runner. GET GAMES needs an enabled provider and the matching system
and runner. The existing surface handles search, details, download progress,
import and play; these plugins do not introduce a separate store UI.

| System | Runner plugin | Search provider | Content |
|---|---|---|---|
| TIC-80 | `@korri:tic80` | `@korri:tic80gallery` | `.tic` |
| WASM-4 | `@korri:wasm4` | `@korri:wasm4gallery` | `.wasm` |
| LowRes NX | `@korri:lowresnx` | `@korri:lowresnxgallery` | `.nx` |
| PuzzleScript | `@korri:pzretro` | `@korri:puzzlescript` | `.pz` |
| Pyxel | `@korri:pyxel` | `@korri:pyxelgallery` | `.pyxapp` |

These are candidates until their recorded checks pass. A declaration or an
ARM build alone does not prove device play. TIC-80's libretro serialization
stores persistent memory, not live execution state. LowRes NX's core has no
standard savestates or virtual-disk integration. PuzzleScript discovery
recognizes only `.pz`. Plus compatibility, `.pzp` discovery, other engine
forks and HTML exports are not promised.

Pyxel's initial source is the versioned upstream sample-app directory, not
all community websites. Its cartridges can contain multiple Python modules.
Core must preserve byte-identified native `.pyxapp` content rather than
unpack it as transport. Older Core acquisition does not do that. The native
runner executes Python under Korri's existing game-process restrictions;
this is not a full filesystem or network sandbox. Opt-in automated acceptance
executes only the reviewed, pinned Space Rescue cartridge, not arbitrary
Python downloads. Plain `.py` projects and external pip dependency resolution
are outside this slice.

Providers fetch author-offered content at the person's request. Runtime
licenses do not grant rights to redistribute those games. No third-party
cartridges belong in the runner packages merely because a gallery lists them.
Publication and physical-device acceptance remain separate approval steps.

## Starter pack

`@korri:starter-pack` displays `Starter pack`. It retains 24 PICO-8 games in
25 unchanged cartridge files and adds Perlshaw's Problems 0.8 and Vegan on a
Desert Island 0.3 as native Solarus archives under `share/starter-pack`.
Credits, notices and checksums accompany all 27 files. The PICO-8 cartridges
remain noncommercial CC BY-NC-SA 4.0; the quests retain their own GPL and
per-file CC/public-domain grants. The complete mixed pack is not commercially
licensed. Blue Isle and Yarntown are excluded.
The plugin requires this repository's exact `@korri:fake08` and `@korri:solarus` outputs.
Installed and enabled, the pack's games appear in the library through `packageFile` declarations.
Into Ruins remains a known FAKE-08 failure, not a verified compatible game.
See [the pack instructions](plugins/starter-pack/README.md) for license conditions and limits.

The locked Core supports exact `requires` and dependency-aware image seeding.
Image composition must select the pack and both exact runtime dependencies.
This source change does not update existing product-image pins, install a
package on a device, or grant signature/permission approval.
Seeding uses each publisher's own binding and preserves normal runtime approval
and signature checks.

Run on a build host, never on a target device:

```sh
nix build --no-link .#korri-plugin-starter-pack .#starter-pack-cartridges \
  .#checks.x86_64-linux.korri-starter-pack-package \
  .#checks.x86_64-linux.korri-starter-pack-admission
nix build --no-link .#checks.aarch64-linux.korri-starter-pack-package \
  .#checks.aarch64-linux.korri-starter-pack-admission
```

## Solarus

`@korri:solarus` is the official, standalone Solarus 2.1.4 producer. Its runner
is `@korri:solarus/solarus`. It discovers `.solarus` archives and keeps native
saves under the account root supplied by Core. The engine plugin contains no
quests. Its controller database is upstream's; Korri seats avoid its swapped
D-pad row by reporting a different controller version. There is no alias for the previous personal publisher identity.
See [the engine instructions](plugins/solarus/README.md) for native checks,
account isolation, corresponding source and installation limits.

`.github/workflows/solarus.yml` checks the real engine and starter pack on
native x86_64 and ARM64 build runners without signing or publishing a cache.
It validates original content bytes, the three-root approval graph and bounded
headless startup. Display, sound, physical controls and full gameplay remain
separate acceptance checks.

## Bitsybox

`@korri:bitsybox` contributes the native `bitsy` system (`.bitsy` data) and
`@korri:bitsybox/bitsybox` runner. It runs exactly the selected file without a
chooser, game copies, browser execution, or bundled games. Bitsybox's
Anti-Capitalist Software License v1.4 restricts eligible users and organizations;
it is not unrestricted OSS. **Publication remains blocked pending separate
eligibility and redistribution approval.** Acquisition remains separate in
[`@korri:itchio`](plugins/itchio/README.md), limited to verified free raw
attachments on a finite approved creator-host set, not the full Bitsy catalog.
See [native behavior, exact notices and focused checks](plugins/bitsybox/README.md).

## Cemu

`@korri:cemu` packages a pinned, ARM-CI-verified Cemu main with SDL3, bundled
Cubeb and offline graphic packs. It uses account-local native configuration
and per-game MLC saves. See [its instructions](plugins/cemu/README.md) for
source/CI provenance, native path grounding, checks and acceptance limits.

## Eden

`@korri:eden` is the official Nintendo Switch `.nsp`/`.xci` runner, packaged
from nixpkgs Eden 0.2.1 for aarch64 and x86_64 Linux. A plugin-only unstable
input (`nixpkgs-eden`) pins the exact Eden build that was tested on devices;
the upstream emulator is reused from cache.nixos.org. Native configuration and
keys stay account-local; the native save NAND uses korrid's save root. On the
AYN Odin 2 Portal, Super Mario Odyssey held 60 FPS on Turnip with NCE (the
shipped default) and with Dynarmic, at a labelled static view. On the Retroid
Pocket Mini V2, Eden ran out of memory within 5.4 GiB without swap; no FPS
result exists there. Device tests used a personally signed build of the same
source; official `@korri` publication is separate. See
[the Eden instructions](plugins/eden/README.md) and
[bench status](plugins/eden/bench/STATUS.md) for evidence and limits. Nothing
is bundled for proprietary content.

## Gamescope

`@korri:gamescope` contributes the `@korri:gamescope/gamescope` launch modifier.
It composes an existing runner plan for nested Wayland. Typed settings, keyed
by Gamescope's own long option names, cover scaling, frame pacing, HDR, input
and cursor options; `--force-composition` is on unless a layer sets it to
`false`. It requires output dimensions from settings or a display hardware
fact. Invalid settings or missing dimensions refuse composition.
See [the modifier instructions](plugins/gamescope/README.md) for the contract,
checks, patch provenance, and hardware acceptance limits. The pinned Core
predates modifier execution; production integration needs that Core support.
This package does not enable itself or install anything on a device.

## Authoring

A hand-written plugin uses `plugin.nix` for native artifacts and `plugin.ts`
for identity and Korri contributions. The libretro catalogue generates one
ordinary plugin source and package per core. Generated plugins use the same
builder and admission rules as hand-written plugins.

`nix/default.nix` calls Core's supported builder with `publisher.namespace = "@korri"`.
The builder renders service units with the same pinned Nixpkgs, checks named
files, and creates `manifest.json`. The immutable output contains the closed
TypeScript source root and manifest. The Nix closure contains its packages and
native units. There is no `package.nix` compatibility route.

Publisher composition supplies the namespace **before** Nix signs the output.
The exporter does not rewrite manifests or remap store paths. This preserves
cross-plugin pins. A manifest claim or a signature's key name does not grant
trust: the device binds a namespace to one full public key and one cache URL,
then verifies the actual NAR signature with that key.

## Tailscale installation and login

Use the new core host and configure `services.korri.pluginHost.publishers` with
an administrator-approved `@korri` binding (`publicKey`, `cacheUrl`). Keep Nix
signature checks enabled. For a non-NixOS host, follow core's root-owned
`/etc/korri-plugin-host/publishers.json` contract and configure the same Nix key.
Neither repository installs trust or device configuration automatically.

After publication, select the device architecture's exact path from the batch
assets described in [PUBLICATION.md](PUBLICATION.md):

```sh
sudo korri-plugin inspect "$CACHE_URL" "$PACKAGE"
sudo korri-plugin install "$CACHE_URL" "$PACKAGE" "$APPROVAL"
sudo korri-plugin enable @korri:tailscale
```

Read the inspection report and use its exact approval value. The rendered unit
requests notification readiness, cleanup, `CAP_NET_ADMIN`, `CAP_NET_RAW`, and
`DeviceAllow=/dev/net/tun rw`. The host applies UDP 41641 and a final hardening
drop-in. These capabilities permit substantial host-network changes; approval
is not a promise of isolation from the host network.

Enablement starts the daemon but does not join a tailnet. Set `TAILSCALE_CLI` to
the named `files.tailscale` path in the package's manifest and `SOCKET` to the
reported runtime directory plus `/tailscaled.sock`. Run an explicit login:

```sh
sudo "$TAILSCALE_CLI" --socket="$SOCKET" up --accept-dns=false
```

Open the login URL that Tailscale prints and approve the device separately.
There is no `LoadCredential`, auth key, auto-login hook, or secret in this
package. Host DNS integration is not implemented. State survives disablement
and ordinary removal; `remove --purge` deletes it. Restoring an older package
does not restore older application data.

## Optional SSH

After installing a compatible host, `@korri:ssh` uses the normal inspection,
installation and approval commands. Its approval explicitly grants root
service authority. It is not installed or enabled by publishing this package.

```sh
sudo korri-plugin enable @korri:ssh
sudo korri-plugin disable @korri:ssh
```

These commands need no system generation switch. The package listens on TCP
2222, uses existing accounts with public-key authentication, and creates its
own device-local host key. It leaves recovery SSH on TCP 22 unchanged. Root
authority is device-wide; disabling the listener does not undo administrative
changes. [`plugins/ssh/README.md`](plugins/ssh/README.md) documents native policy and verification.

The owner still needs an existing administrator path to install and toggle it.
Local owner enrollment and a graphical plugin-management interface are not
provided by this package. No owner or host private key is published.

## Publication and checks

[PUBLICATION.md](PUBLICATION.md) covers signed exports, verified upstream
omission, append-only metadata, immutable batch path listings and retries.
This repository owns RetroArch, generated libretro core packages, SSH, and
Sunshine native recipes and producer gates. The combined x86_64 cold-host lifecycle gate
passed on 2026-09-17 with the external mGBA package. Physical-hardware
acceptance remains pending.

Run focused checks on a build machine:

```sh
python3 nix/github-cache-test.py # requires Nix, Python, OpenSSL and Bash
nix build --no-link .#checks.x86_64-linux.korri-github-cache
nix build --no-link .#checks.x86_64-linux.korri-plugin-builder
nix run .#korri-retroarch-check
nix build --no-link .#checks.x86_64-linux.korri-tailscale-package
nix build --no-link .#checks.x86_64-linux.korri-retroarch-package
nix build --no-link .#checks.x86_64-linux.korri-retroarch-settings
nix build --no-link .#checks.x86_64-linux.korri-libretro-example
nix build --no-link .#checks.x86_64-linux.korri-libretro-frontend-override
nix build --no-link .#checks.x86_64-linux.korri-libretro-typecheck
nix build --no-link .#checks.x86_64-linux.korri-ssh-upstream .#checks.x86_64-linux.korri-ssh-host-support
```

The Python test uses real signed Nix caches, a local HTTPS server and isolated
stores with builds disabled for downloads. GitHub writes use a file-backed API
subprocess, not a live repository. Package builds need cached dependencies or
separate permission to build their closures.

Evaluate both architectures against the checked-in GitHub lock, without an
override:

```sh
for system in x86_64-linux aarch64-linux; do
  nix eval --no-write-lock-file --json ".#packages.$system" \
    --apply 'packages: builtins.attrNames packages'
done
```

This checks the catalogue shape without discarding nixpkgs platform metadata.
Building a selected core still fails when nixpkgs does not support that target.
For future updates, select a reachable reviewed core commit and verify its
GitHub revision and hash in `flake.lock`. Recheck both architectures and
mGBA's exact RetroArch frontend path before publication. Never commit a local
source path. Update publisher Nixpkgs separately; its changes can require a
new native dependency review and new plugin outputs.

## Native tools and boundaries

Publisher owns `sunshine-korri`, `sunshine-retire-all-clients`, and the ARM-only
`sunshine-korri-v4l2m2m` and `sunshine-v4l2m2m-probe` outputs. The existing
`sunshine-retire-all-clients` app moves here too. The ARM plugin uses one reviewed
FFmpeg archive with RKMPP and V4L2 M2M, not two independent bundles. The standalone
probe retains its separate V4L2 FFmpeg recipe. Tool ownership does not authorize
running probes or retiring client state.

Core retains host authority, shared input seats, certificate authorization,
SSH account/PAM support, and packaged consumer checks. `nix/integration.nix`
uses host binaries only for tests and the existing publisher CLI tooling. It
imports no Core host recipe with publisher pkgs.
Historical rotation tools keep their exact Core baseline. The Android check
remains inactive historical source; neither is a shipping dependency.

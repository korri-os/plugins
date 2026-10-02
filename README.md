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
| `korri-plugin-ssh` | `@korri:ssh` | `plugins/ssh/` |
| `korri-plugin-sunshine` | `@korri:sunshine` | `plugins/sunshine/` and `services/sunshine/` |

Sunshine is a build candidate. Do not publish it until the ARM build and
plugin lifecycle gates pass. Its presence in a release does not establish
streaming acceptance.

Supported systems are `x86_64-linux` and `aarch64-linux`. Publisher composition
binds `korri.lib.<system>.mkPlugin { pkgs = publisherPkgs; }`. The catalogue currently emits 90
core packages. Each core package carries its selected RetroArch frontend and
core library in one closure. Nix deduplicates identical store paths.

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

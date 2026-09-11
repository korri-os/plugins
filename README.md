# Korri plugins

This repository publishes prebuilt Linux plugins through a signed Nix cache on
GitHub Releases. Devices download exact store outputs. They never compile them.

The checked-in lock pins core main commit
`f352e9f5e565c0ca0fdfb78025c4814fee50f072`, including the native plugin builder,
compatible host and optional SSH package. Devices need one compatible host
update before inspecting these packages. Publication and physical-device
acceptance remain pending; this cutover changes neither devices nor releases.

## Packages

| Flake output (`packages.<system>`) | Plugin | Source |
|---|---|---|
| `korri-tailscale` | `@korri:tailscale` | This repository's `plugins/tailscale/` |
| `korri-plugin-retroarch` | `@korri:retroarch` | Locked core output, unchanged |
| `korri-plugin-mgba` | `@korri:mgba` | Locked core output, unchanged |
| `korri-plugin-ssh` | `@korri:ssh` | Locked core output, unchanged |

Supported systems are `x86_64-linux` and `aarch64-linux`. Core supplies Nixpkgs,
toolchains and `lib.<system>.mkPlugin`. mGBA's `requires` pins the same exact
RetroArch output exported here. Install and approve RetroArch before mGBA;
downloading the dependency closure does not approve its plugins.

## Authoring

Each plugin has two source files:

- `plugin.nix` declares `packages`, named `files`, native NixOS `services`, exact
  plugin `requires`, and optional `ports` using NixOS firewall list names.
- `plugin.ts` declares identity and Korri contributions through named exports.
  It cannot declare a namespace or systemd configuration.

`nix/default.nix` calls core's builder with `publisher.namespace = "@korri"`.
The builder renders service units with the same pinned Nixpkgs, checks named
files exist, and creates `manifest.json`. The immutable output contains that
manifest and `plugin.ts`; the Nix closure contains its packages and native units.
There is no `package.nix` compatibility route.

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
changes. Core's `plugins/ssh/README.md` documents native policy and verification.

The owner still needs an existing administrator path to install and toggle it.
Local owner enrollment and a graphical plugin-management interface are not
provided by this package. No owner or host private key is published.

## Publication and checks

[PUBLICATION.md](PUBLICATION.md) covers signed exports, verified upstream
omission, append-only metadata, immutable batch path listings and retries.
RetroArch, mGBA and SSH are published directly from core; their source is not copied
into this repository. The workflow retains its combined cold-host lifecycle
gate with SSH. Core records that VM gate as passed on 2026-09-10; this publisher
cutover did not rerun a VM or test physical hardware. The separate Effect
runtime is not a dependency.

Run focused checks on a build machine:

```sh
python3 nix/github-cache-test.py # requires Nix, Python, OpenSSL and Bash
nix build --no-link .#checks.x86_64-linux.korri-github-cache
nix build --no-link .#checks.x86_64-linux.korri-tailscale-package
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
    --apply 'p: builtins.mapAttrs (_: v: v.outPath) p'
done
```

For future updates, select a reachable core main commit and review its GitHub
revision and hash in `flake.lock`. Recheck both architectures and mGBA's exact
RetroArch requirement before publication. Never commit a local source path or
add a second Nixpkgs input.

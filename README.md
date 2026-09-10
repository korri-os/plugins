# Korri plugins

This repository publishes prebuilt Linux plugins through a signed Nix cache on
GitHub Releases. Devices download exact store outputs. They never compile them.

**Integration gate:** the checked-in core lock still names
`a17c5c35e74066251184a3fd8d1e4e386559002a`. It does not provide the new builder.
Land core's plugin-authoring changes on core main, update this lock to that
commit, and rerun evaluation before publishing. Do not inspect these packages
with the old host. No publication or device change is part of this migration.

## Packages

| Flake output (`packages.<system>`) | Plugin | Source |
|---|---|---|
| `korri-tailscale` | `@korri:tailscale` | This repository's `plugins/tailscale/` |
| `korri-plugin-retroarch` | `@korri:retroarch` | Locked core output, unchanged |
| `korri-plugin-mgba` | `@korri:mgba` | Locked core output, unchanged |

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

## Publication and checks

[PUBLICATION.md](PUBLICATION.md) covers signed exports, verified upstream
omission, append-only metadata, immutable batch path listings and retries.
RetroArch and mGBA are published directly from core; their source is not copied
into this repository. The workflow retains its cold-host lifecycle gate. This
migration did not run a VM or test physical hardware.

After updating the core pin, run on a build machine:

```sh
python3 nix/github-cache-test.py # requires Nix, Python, OpenSSL and Bash
nix build --no-link .#checks.x86_64-linux.korri-github-cache
nix build --no-link .#checks.x86_64-linux.korri-tailscale-package
```

The Python test uses real signed Nix caches, a local HTTPS server and isolated
stores with builds disabled for downloads. GitHub writes use a file-backed API
subprocess, not a live repository. Package builds need cached dependencies or
separate permission to build their closures.

For development evaluation only, use the new core worktree without saving a
local lock entry:

```sh
CORE=/absolute/path/to/korri/.worktree/plugin-standard
for system in x86_64-linux aarch64-linux; do
  nix eval --no-write-lock-file --override-input korri "path:$CORE" \
    --json ".#packages.$system" \
    --apply 'p: builtins.mapAttrs (_: v: v.outPath) p'
done
```

To finalize, run `nix flake update korri` only after core main contains the
builder and both game outputs. Review the GitHub revision and hash in
`flake.lock`, then evaluate both architectures without an override. Never
commit a local source path or add a second Nixpkgs input.

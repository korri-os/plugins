# Tailscale for Linux

Tailscale installs independently through the [generic plugin host](https://github.com/korri-os/korri/blob/main/services/korrid/plugin-host/README.md). The system image contains no Tailscale package or named service registration. Install, enable, update, disable, and remove use the administrator CLI without a NixOS update.

`packages.<system>.korri-tailscale` contains the runtime-interpreted `plugin.ts` declaration and links to the unchanged `pkgs.tailscale` binaries from the locked core input's nixpkgs. The small declaration package is also built in CI. Nix exports and signs its complete closure for a standard binary cache hosted on GitHub Releases. Devices never build it locally. Both CLI and daemon come from that same selected package.

## Installation

First install core's generic `nixosModules.korri-plugin-host` support in the base system. The module does not name Tailscale. After publication, use the cache metadata release URL and the exact store path from the build artifact. Configure the cache public key through the approved host configuration first. No destination or key is installed by this change.

```sh
sudo korri-plugin inspect "$CACHE_URL" "$PACKAGE"
```

Read the reported declaration, effective systemd policy, and permission warning. Then supply the report's exact approval value:

```sh
sudo korri-plugin install "$CACHE_URL" "$PACKAGE" "$APPROVAL"
sudo korri-plugin enable @korri:tailscale
```

The daemon uses a dynamic unprivileged user with `CAP_NET_ADMIN` and `CAP_NET_RAW`. These capabilities permit host-network changes, including routes and firewall rules. Approval grants substantial authority. It is not browser-style isolation or a promise that the publisher is safe.

The declaration uses the upstream daemon command, notification readiness, and cleanup operation. systemd supplies private state and socket directories. The host reports their exact paths. There are no install scripts, plugin-specific host options, or authentication keys in the package.

## Authentication and limits

Enablement starts the daemon. It does not join a tailnet. Use the selected package's CLI and the socket path from the report to perform a separately authorized login with `--accept-dns=false`. This first slice carries traffic without changing the host DNS configuration. Keep secrets out of declarations and the Nix store.

Private state survives disablement, updates, and ordinary removal. `remove --purge` explicitly deletes it. Automatic rollback restores package selection, not a snapshot of application data. A newer binary can change state that an older binary cannot read. Failed recovery retains the package references and reports an error.

The maintained VM proves TUN creation, authenticated IP traffic through a disposable local Headscale network, cleanup, reboot recovery, and the full installation lifecycle. It does not prove host DNS changes, handheld kernel support, or remote streaming. The restricted service cannot rewrite arbitrary host files or acquire new permissions.

## Checks

Run these on a development or CI machine, never on a download-only device:

```sh
nix build .#checks.x86_64-linux.korri-plugin-host .#checks.x86_64-linux.korri-runtime-plugin-host --no-link
nix build .#checks.x86_64-linux.korri-github-cache --no-link
nix build .#checks.x86_64-linux.korri-tailscale-package --no-link
```

The [curator-triggered publication workflow](../../PUBLICATION.md) builds selected packages on standard x86_64 and ARM64 Linux runners. A batch can contain several plugins. Nix generates the cache metadata; no catalog is maintained in this publication path. Core's separate catalog commands remain unchanged. Publishing, device deployment and real tailnet enrollment require their own approval.

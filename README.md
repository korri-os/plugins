# Korri plugins

`korri-os/plugins` owns independently released plugin packages and their release
preparation. `@korri:tailscale` is the first package. Devices download verified
archives; they do not build plugins.

[Korri core](https://github.com/korri-os/korri) owns the plugin host, runtime,
NixOS modules, catalog contract, Rust publisher, and Rust validation. This
repository consumes those interfaces through one locked `korri` flake input.
Nixpkgs and toolchains come from core's inputs, not a second selection.
`flake.nix` indexes the composition in `nix/default.nix`.

The move originates at rewritten core commit
`c9d0ac5e0921bcc213258ed55b2c266dcff0143c`. Tailscale's `package.nix`,
`package-check.nix`, and `plugin.ts` retain their bytes and `@korri:tailscale`
identity. Core retains test fixtures, not the distributable plugin package.

## Build-machine checks

Run from this repository on Linux, never on a download-only device:

```sh
nix build .#korri-tailscale
nix build --no-link .#checks.x86_64-linux.korri-tailscale-package .#checks.x86_64-linux.korri-publication-workflow
nix run .#korri-publisher-check
nix build --no-link .#checks.x86_64-linux.korri-runtime-plugin-host
```

Both `x86_64-linux` and `aarch64-linux` expose package and policy checks. The
workflow runs them on native runners and runs the full lifecycle VM on x86_64.
The publisher app passes this repository's actual Tailscale store path to the
pinned core test app. The VM also receives this actual package. Publisher tests
need a writable build-machine Nix store; the VM needs virtualization resources.
Uncached builds and closure conversion can exceed runner disk or time limits.

## Core pin updates

Publish and verify the compatible core revision first. Update only the core
input, then review the resulting core revision and transitive lock changes:

```sh
nix flake update korri
```

Run the checks above and evaluate both architectures before committing
`flake.lock`. Do not add independent nixpkgs or toolchain inputs. The lock must
reference a published core revision, never a local filesystem path.

## Publication is not live

No official catalog is deployed or configured here. The generated catalog
contains one selected plugin release for two architectures. It is **not
cumulative**. Retaining older offered records needs a separate deliberate merge.

[Publication controls and operator steps](PUBLICATION.md) are the release
contract. Before use, verify public repository/free runner availability, the
`plugin-release` environment, and immutable-release settings. Only curator
`simonwjackson` may dispatch or rerun `main`. Supply an explicit destination,
a new bounded tag without `/`, and an independent plugin release label. Before
draft writes, the destination tag must already resolve to the checked commit.

The manual workflow produces separate catalog and archive artifacts. Explicit
approval permits draft-only writes to this repository. It never creates tags,
publishes a release, or deploys Pages. Public release downloads, catalog hosting,
`officialCatalogUrl` configuration, and device acceptance need separate approval
and verification. See [Tailscale usage and limits](plugins/tailscale/README.md).

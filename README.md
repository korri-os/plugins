# Korri plugins

This repository builds independently installed plugins. Devices download prebuilt
packages. They do not compile them.

`@korri:tailscale` is the first package. The flake pins
[korri-os/korri](https://github.com/korri-os/korri), which supplies the runtime,
plugin declaration contract, Nixpkgs and toolchains.

## Distribution

GitHub Releases hosts a standard signed Nix binary cache:

- Each build batch has a release for its compressed NAR files. A batch can
  contain several packages on both architectures. Its tag does not name a plugin.
- One public mutable release holds `nix-cache-info` and `.narinfo` files.
  Each narinfo points to its NAR asset with an absolute HTTPS URL.
- The workflow omits dependencies verified in `https://cache.nixos.org`, including
  their NAR payloads. Dependencies absent upstream remain in the plugin cache.
- Nix generates and signs the metadata. There is no hand-maintained catalog in
  this publication path. The build produces exact store paths as text artifacts.

`nix run .#korri-cache -- --help` exposes build, export, prepare, combine,
upload and publish commands. See [PUBLICATION.md](PUBLICATION.md) for setup,
signing, failure handling and the workflow.

Partial caches require an updated core raw-cache installer that combines the
plugin cache with configured trusted upstream caches. Update and verify core
before publishing or using these caches. This change leaves the core pin unchanged.
Core's HTTPS catalog reader remains separate and unchanged. This change does not add plugin browsing,
automatic source selection, or a new device metadata format.

## Checks

Run on a build machine:

```sh
nix build --no-link .#checks.x86_64-linux.korri-github-cache
nix build --no-link .#checks.x86_64-linux.korri-tailscale-package
nix build --no-link .#checks.x86_64-linux.korri-runtime-plugin-host
```

The cache check downloads two packages from a real TLS server into an empty Nix
store with builds disabled. It verifies signature refusal, redirect handling,
damaged downloads, cache misses and retained metadata across batches. It also
checks upstream omission, dependency reuse and fail-closed upstream errors. GitHub
write tests use a file-backed API subprocess. They do not publish anything.

The existing cold-host VM checks plugin installation and Tailscale networking.
The cache test does not replace device acceptance.

## Core pin updates

Run `nix flake update korri`, review `flake.lock`, then run the checks. Evaluate
both Linux architectures before committing the pin. Never add a local source
path or a second Nixpkgs input.

## Limits

GitHub limits each release to 1,000 assets and each asset to less than 2 GiB.
The publisher stops before exceeding those limits. The shared metadata release
therefore has finite capacity. Free hosting is not unlimited hosting.

A signing key and explicit device trust are required. No key, tag, release,
repository setting or device configuration is created by the local checks.

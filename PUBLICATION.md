# Signed Nix cache publication

The publisher uses Nix's file-cache format. It does not convert store paths to
content-addressed paths, pack closure tarballs, or produce Korri catalog records.
Nix owns signatures and verifies downloaded contents.

## Hosting setup

Use two distinct release tags:

| Release | Contents | Change policy |
|---|---|---|
| Build batch | Compressed NAR files for any selected packages and both architectures. | Upload while draft, then publish. Release immutability can lock these files. |
| Cache metadata | `nix-cache-info` and signed `.narinfo` files. | Public and mutable. The publisher only adds files; it never replaces or deletes one. |

The cache URL is `https://github.com/OWNER/REPO/releases/download/CACHE_TAG/`.
NAR URLs name their batch release. Tags identify storage locations, not plugin
versions. Updating two plugins together needs one batch tag, not two plugin tags.

Create the metadata release before enabling immutability for future releases.
If that release is immutable, publication refuses it. Do not disable protection
on an existing release or move a tag to bypass the check.

No setup step below has been performed by this code change.

## Signing key

Generate a persistent key with the standard Nix command on a trusted machine:

```sh
umask 077
nix-store --generate-binary-cache-key korri-plugins-1 cache.secret cache.public
```

Store the private key as the `NIX_CACHE_SIGNING_KEY` Actions secret. Keep it out
of Git, the Nix store and workflow artifacts. Configure the public key as an
additional trusted key on each device through its approved host configuration.
Keep `require-sigs = true`. Never use a signature bypass to make an install work.

A signature authorizes Nix store contents. It is not permission to start a
privileged plugin. Core's administrator approval remains a separate step.

## Workflow

Only `simonwjackson` can dispatch or rerun `main`. Review the `plugin-release`
environment before the first run. Jobs use standard x86_64 and ARM runners.

Inputs to `.github/workflows/plugin-repository.yml`:

- `packages` selects one or more flake package output names, separated by spaces.
  The tool rejects expressions, flags and paths. It does not hardcode a plugin ID.
- `tag` identifies the build batch. Before publication, this tag must already
  resolve to the workflow's exact source commit. The publisher never creates or
  moves a tag.
- `cache_tag` identifies the existing public mutable metadata release.
- `publish` defaults to false. True explicitly permits NAR release creation,
  publication and metadata uploads after both builds and the lifecycle gate pass.

Builds run before the signing key is exposed. Signed exports use `nix copy` with
zero build jobs and no remote builders. The secret is removed before artifacts
upload. When publication is false and no signing secret exists, the build uses a
temporary test key. Such outputs are not production artifacts.

The workflow prepares against `https://cache.nixos.org` by default. It uploads
only paths not already verified there, normally custom plugin wrappers and their
Nix metadata. It retains any dependencies genuinely absent upstream. This saves
hosted assets, not CI disk: the local signed export still contains the full closure.

Each architecture artifact contains prepared cache files and the exact output
paths emitted by Nix in `paths-SYSTEM.txt`. These are generated build outputs,
not manually maintained metadata. Actions artifacts expire after seven days;
published cache assets do not use Actions retention.

The workflow combines both architectures, then uploads NARs to the batch draft.
It checks GitHub's reported SHA256 and size for each uploaded asset. It publishes
that exact release ID before adding any metadata that refers to it. Existing
release settings determine whether publication makes it immutable.

## Commands on a build machine

Build the package outputs you want. Pass their exact store paths to the export
command. Do not pass flake references to export.

```sh
nix run .#korri-cache -- build --system aarch64-linux --paths-file paths.txt korri-tailscale
nix run .#korri-cache -- export file-cache --key-file cache.secret /nix/store/EXACT_OUTPUT
nix run .#korri-cache -- prepare file-cache prepared --nar-base-url https://github.com/OWNER/REPO/releases/download/BATCH_TAG/ --upstream-cache https://cache.nixos.org
```

`EXACT_OUTPUT`, repository, tag and key path above are operator inputs, not real
published values. `export` can take several store paths. Nix exports and signs
their full dependency closure. Repeat `prepare --upstream-cache HTTPS_URL` to
check more than one upstream. Each matching path must have the same store path,
NAR hash, NAR size and references as the local signed export. Nix verifies the
fetched metadata's signatures against the build machine's configured
`trusted-public-keys`. No trust is granted by naming an upstream URL. Configure
extra upstream keys through Nix's normal configuration, not through this tool.

Only a valid HTTPS 404 means absent. Authentication, TLS, network, server,
malformed metadata, conflicting identity and signature failures stop preparation
without leaving a prepared output. Every configured upstream is checked, even
if another supplies the path. Preparation checks metadata, not upstream payload
availability; Nix checks payload contents during installation.

For verified upstream paths, `prepare` omits both the narinfo and its compressed
NAR. For retained paths it changes only each narinfo's `URL:` line; that field is
outside Nix's signed fingerprint. All retained signatures remain unchanged.
Without `--upstream-cache`, the explicit command keeps the complete closure.

After approval, `publish` performs the GitHub writes:

```sh
nix run .#korri-cache -- publish prepared --repo OWNER/REPO --tag BATCH_TAG --cache-tag CACHE_TAG --revision EXACT_COMMIT
```

The lower-level `upload --part nars` and `upload --part metadata` commands allow
separate operator stages. Metadata upload refuses draft NAR releases.

## Device installation

**Partial caches require an updated core raw-cache installer that combines the
plugin cache with configured trusted upstream caches.** A core installer that
expects the plugin cache to contain the entire closure cannot use this workflow's
output. Update and verify core before publication or device use. This publisher
change does not update the core flake pin or device configuration.

Devices must configure the same upstream caches and their trusted public keys,
with signatures required and builds disabled. Use the exact store path from the
build artifact and the metadata release URL:

```sh
sudo korri-plugin inspect CACHE_URL EXACT_STORE_PATH
sudo korri-plugin install CACHE_URL EXACT_STORE_PATH APPROVAL_FROM_INSPECTION
```

Read the approval report before installing. Enable the plugin separately. This
uses the raw-cache CLI with the updated core importer, not `repository install`. The cache protocol
cannot list plugins. Browsing and source-pinned catalog operations are unchanged;
they still need their existing catalog contract. No new discovery file is
introduced here.

## Retries and failures

All workflow batches share one concurrency group. Uploads never use `--clobber`
or delete assets. A retry skips assets whose reported SHA256 and size match.
A different file under an existing name stops publication before that upload set
writes anything. Partial uploads remain available for an identical retry.

Different batches often contain the same dependencies. If their narinfos differ
only in the NAR URL, retain the first published metadata and URL. Every other
field, including signatures, must match. Key changes require a separate migration;
this publisher does not replace existing signatures.

Failure can leave a partial draft, a published NAR release, or some added cache
metadata. It cannot make a cache-wide update atomic. Nix sees missing paths as
cache misses, and devices must refuse builds. A retry repairs missing assets;
it does not remove valid assets from another batch. An administrator can still
change releases outside the workflow. Do not edit them during publication.

## Capacity and verification limits

[GitHub's release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
are 1,000 assets per release and less than 2 GiB per asset. The metadata release
holds one narinfo per store path plus `nix-cache-info`. It will eventually fill.
No automatic rotation or deletion is implemented. Publication refuses the limit;
it does not remove old software to make room.

Metadata points to immutable NAR locations, but signing is the trust mechanism.
Deletion or account loss can still cause an outage. There is no storage bill in
this public-Release design; there is no uptime or unlimited-capacity guarantee.

Local checks cover Nix signature and byte verification, TLS redirects, multiple
packages, merging architecture outputs, shared dependencies, partial-upload
retry, wrong-commit refusal and conflicting assets. Local HTTPS upstream tests
also cover omitted NARs and metadata, dependency reuse in an empty store, genuine
404s, authentication/server/TLS/network failures, untrusted and damaged signatures,
and mismatched metadata. GitHub operations use a
file-backed test process. Live release downloads and physical ARM installation
remain separate acceptance gates. No claim of live verification follows from
these tests.

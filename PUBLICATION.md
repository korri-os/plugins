# Signed Nix cache publication

The publisher uses Nix's file-cache format. It does not convert store paths to
content-addressed paths, pack closure tarballs, or produce Korri catalog records.
Nix owns signatures and verifies downloaded contents.

## Hosting setup

Use two distinct release tags:

| Release | Contents | Change policy |
|---|---|---|
| Build batch | Compressed NAR files, generated `paths-SYSTEM.txt` lists and `revision.txt`. | Upload while draft, then publish. Release immutability can lock these files. |
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

Core's builder writes `publisher.namespace` into the generated manifest before
this exporter signs the Nix closure. The namespace is fixed by trusted build
composition, not by `plugin.ts` or by reading a signature name. Core's game
outputs already contain it; this repository exports them unchanged so mGBA's
exact RetroArch requirement remains valid. Never rewrite a manifest after build.

The device must bind `@korri` to the full public key and the exact cache URL in
`services.korri.pluginHost.publishers` (or core's root-owned publisher file on
non-NixOS). The new host checks the actual NAR signature with that bound key.
A matching signature label or another globally trusted signer is insufficient.
Administrator approval to start the plugin remains a separate step.

## Workflow

Only `simonwjackson` can dispatch or rerun `main`. Review the `plugin-release`
environment before the first run. Jobs use standard x86_64 and ARM runners.

Inputs to `.github/workflows/plugin-repository.yml`:

- `packages` selects one or more flake package output names, separated by spaces.
  The tool rejects expressions, flags and paths. It does not hardcode a plugin ID.
  Defaults: `korri-tailscale korri-plugin-retroarch korri-plugin-mgba`. The latter
  two are unmodified outputs from the locked core flake.
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

Each architecture artifact contains prepared cache files, the exact output
paths emitted by `nix build --print-out-paths` in `paths-SYSTEM.txt`, and the
workflow's full `GITHUB_SHA` in `revision.txt`. These are generated build outputs,
not manually maintained metadata. Combine preserves both architecture lists and
refuses conflicting revisions or same-named files. `publish` requires these
files and checks their revision against both its argument and the batch tag.
Actions artifacts expire after seven days; the same text files are uploaded
with the NARs **before the batch is published**, so published lookup evidence
does not expire with Actions. They never enter the mutable cache release.

The workflow combines both architectures, then uploads NARs and path listings to the batch draft.
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

Preparation first fetches each upstream's `nix-cache-info` over HTTPS and has Nix
parse it. Missing, invalid or unavailable cache info stops preparation. Only a
narinfo HTTPS 404 from a cache that passed this check means a path is absent.
Authentication, TLS, network, server, malformed metadata, conflicting identity
and signature failures stop preparation without leaving a prepared output.
Every configured upstream is checked, even if another supplies the path.
Preparation checks metadata, not upstream payload availability; Nix checks
payload contents during installation.

For verified upstream paths, `prepare` omits both the narinfo and its compressed
NAR. For retained paths it changes only each narinfo's `URL:` line; that field is
outside Nix's signed fingerprint. All retained signatures remain unchanged.
Without `--upstream-cache`, the explicit command keeps the complete closure.

For manual batches, retain each architecture's `build --paths-file` output as
`prepared/paths-SYSTEM.txt` and write the exact checked source commit plus a
newline to `prepared/revision.txt`. Do not create these from guessed paths.
For example, copy `paths.txt` from the build above to
`prepared/paths-aarch64-linux.txt`. These files describe the build, not the
signing identity. After approval, `publish` performs the GitHub writes:

```sh
nix run .#korri-cache -- publish prepared --repo OWNER/REPO --tag BATCH_TAG --cache-tag CACHE_TAG --revision EXACT_COMMIT
```

The lower-level `upload --part nars` and `upload --part metadata` commands allow
separate operator stages. Metadata upload refuses draft NAR releases.

## Device installation

**Publication is blocked until core main provides the new plugin builder and
host, and this repository pins that main commit.** The current lock still names
`a17c5c35e74066251184a3fd8d1e4e386559002a`. Development evaluation may override
core locally with `--no-write-lock-file`; production must not. The old host
cannot inspect the new named-export source and manifest contract.

Partial caches also require core's multi-cache importer. Devices combine the
plugin cache with configured trusted upstream caches. This repository does not
change device configuration.

Devices must configure the same upstream caches and their trusted public keys,
with signatures required and builds disabled. Use the exact store path from the
immutable batch's architecture-specific path list and the metadata release URL:

```sh
sudo korri-plugin inspect CACHE_URL EXACT_STORE_PATH
sudo korri-plugin install CACHE_URL EXACT_STORE_PATH APPROVAL_FROM_INSPECTION
```

Read the approval report before installing. Enable the plugin separately. This
uses the raw-cache CLI with the updated core importer, not `repository install`. The cache protocol
cannot list plugins. Browsing and source-pinned catalog operations are unchanged;
they still need their existing catalog contract. No new discovery file is
introduced here.

## Exact commit lookup evidence

For the brief's `build-<rev12>` convention, the full commit identifies the batch
tag by its first 12 characters. Publication requires that tag to resolve to the
full checked commit. Existing custom batch tags remain supported; supply their
exact names rather than assuming they follow this convention. No `latest`,
stable pointer, or tag-moving operation is introduced.

| Batch asset | Producer | Contents |
|---|---|---|
| `revision.txt` | Workflow checkout (`GITHUB_SHA`) | One full 40-character commit and a newline |
| `paths-x86_64-linux.txt` | `korri-cache build` / Nix stdout | One selected output store path per line |
| `paths-aarch64-linux.txt` | `korri-cache build` / Nix stdout | One selected output store path per line |

These lists do not map plugin IDs to paths, and they are not signed catalogs.
They are durable lookup evidence from the existing publication path. The new
host must still verify and inspect a selected store output to determine its
identity, permissions and bound publisher. Downloading a list grants no trust.
The brief's `install CACHE ID --release <commit>` consumer is not implemented
by this repository. Core must implement that lookup separately; this change does
not invent another catalog schema or claim the CLI already exists.

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
also cover omitted NARs and metadata, dependency reuse in an empty store, healthy
empty caches, missing or invalid cache info, genuine narinfo 404s,
authentication/server/TLS/network failures, untrusted and damaged signatures,
and mismatched metadata. GitHub operations use a
file-backed test process. Live release downloads and physical ARM installation
remain separate acceptance gates. No claim of live verification follows from
these tests.

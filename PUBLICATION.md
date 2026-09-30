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
composition, not by `plugin.ts` or by reading a signature name. This repository
builds each game package through that builder. Never rewrite a manifest after
build.

The device must bind `@korri` to the full public key and the exact cache URL in
`services.korri.pluginHost.publishers` (or core's root-owned publisher file on
non-NixOS). The new host checks the actual NAR signature with that bound key.
A matching signature label or another globally trusted signer is insufficient.
Administrator approval to start the plugin remains a separate step.

## Core updates and plugin publication

The locked Core input supplies build dependencies. It is not a requirement
that every new Core commit publish new plugin packages. Keep this pin for
unrelated Core changes. Current Core tests the unchanged published packages
with `nix run .#korri-published-plugins-check` in the Core repository. That gate
checks both architecture selections and offline closure proofs. Its x86 VM
checks image receipts, approval refusal, SSH lifecycle and the game registry.
The packaged mGBA callback test checks route and `launch.prepare` behavior,
not emulator gameplay. A host-only operation-name break must fail that test.

Advance the publisher pin only for a consumed builder, contract, native
package or toolchain change that needs adoption. Evaluate the candidate
package outputs on a build machine. Compare their exact paths with prior
published outputs, using the existing architecture path lists and verified
host declarations. The lists do not map IDs to paths. Select only affected
outputs in the workflow's existing `packages` input. An unchanged output
needs no publication. Batch 1's source-mutation gate remains unchanged.

Core images name exact published output paths in native Nix composition and
pin the matching immutable offline metadata assets by hash. They no longer
import this publisher's recipes or advance its Core pin during image builds.
A plugin update requires an explicit image pin edit and acceptance before
image delivery. Publication and deployment need separate approval; a
successful Core test grants neither. Independent closures can retain old dependency versions and use
more disk. A Core dependency update does not update those plugin dependencies;
security updates to them still require deliberate plugin publication.

## Workflow

Only `simonwjackson` can dispatch or rerun `main`. Review the `plugin-release`
environment before the first run. Jobs use standard x86_64 and ARM runners.

Inputs to `.github/workflows/plugin-repository.yml`:

- `packages` selects one or more flake package output names, separated by spaces.
  The tool rejects expressions, flags and paths. It does not hardcode a plugin ID.
  Defaults: `korri-tailscale korri-plugin-retroarch korri-plugin-mgba korri-plugin-ssh korri-plugin-sunshine`.
  RetroArch and game packages are built from this repository. SSH and Sunshine
  are unmodified outputs from the locked core flake. Sunshine cannot publish
  until the core lock pins the verified Sunshine plugin and combined encoder build.
- `tag` identifies the build batch. Before publication, this tag must already
  resolve to the workflow's exact source commit. The publisher never creates or
  moves a tag.
- `cache_tag` identifies the existing public mutable metadata release.
- `publish` defaults to false. True explicitly permits NAR release creation,
  publication and metadata uploads after both builds and the lifecycle gate pass.

Build jobs read the signed publisher cache before their test and build commands.
Lifecycle verification also reads Core's signed cache through `--include-core`.
`nix/ci-cache-settings.nix` reads URLs from the locked Core product requirements,
Core keys from `korri.cache`, and publisher trust from the existing `@korri`
binding. The helper preserves stock and inherited settings, verifies the
effective configuration, and requires signatures. Publishing builds refuse an
inherited Core cache, including a URI with priority parameters.

Core cache imports can retain Core signatures when Nix exports the same path
with a publisher signature. This makes an unchanged path fail the publisher's
strict append-only metadata comparison. A real isolated-store fixture reproduced
that conflict on Nix 2.31 and 2.34. On 2026-09-29, the owner chose publisher-only
build reuse and both caches for lifecycle verification. Export, signature checks,
and the upstream filter remain unchanged. Build jobs lose Core-only reuse.
Missing outputs still require builds on CI. Cache outages can stop downloads.

Each build job runs `korri-plugin-churn-check` for its architecture. The check
evaluates the real Mini V2 selection from Core, rather than maintaining another
package list. It proves an unrelated documentation change preserves the selected
package paths and the libretro typecheck, plugin-host, and settings check paths.
Contract, helper, settings-producer, and RetroArch source changes must invalidate
only their expected outputs. Copies retain executable bits and symlinks. This
is an evaluation check, not a build or device acceptance test.

The libretro typecheck copies only the consumed contract file into the store.
Changes elsewhere in Core no longer invalidate it. Changes to the contract bytes
still invalidate the check. Generated contract source remains read-only.

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

The workflow combines both architectures, then uploads NARs, path listings, and
one `offline-metadata-SYSTEM.tar.gz` asset per architecture to the batch draft.
Each archive contains the signed, Nix-produced `nix-cache-info` and `.narinfo`
files for the full selected closure, including paths omitted from the public
cache because a trusted upstream already serves them. It contains no NAR or
private key. An image builder pins the immutable asset by hash; the device
registers these proofs only after its shipped paths are in the local Nix store.
Nix must still verify each package's bound publisher key and closure contents.
The archive alone grants no trust. This adds archive bytes and a first-boot
verification step; it does not make network-dependent plugin features work
without internet.

The publisher checks GitHub's reported SHA256 and size for each uploaded asset.
It publishes that exact release ID before adding any metadata that refers to it.
Existing release settings determine whether publication makes it immutable.

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
NAR from the public mutable cache. The offline metadata archive keeps the
original signed narinfo for every path. For retained public cache paths,
`prepare` changes only each narinfo's `URL:` line; that field is outside Nix's
signed fingerprint. All signatures remain unchanged. Without
`--upstream-cache`, the explicit command keeps the complete public closure.

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

**Publication and device acceptance remain pending.** The lock pins Korri
`main` commit `e382290e9ec62b122c05bf9542d9bd6f6fba3ccc`, with the Sunshine
and SSH outputs. The ARM build and plugin VM have not passed. This is a build
candidate, not permission to publish.
Production uses this GitHub lock, not a local path override. Each device still
needs one compatible host update and explicit publisher trust configuration.
The old host cannot inspect the named-export source and manifest contract.
After that update, approved SSH enable/disable commands need no system
generation switch.

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
The locked core implements `install CACHE ID --release COMMIT` as an
inspection-only lookup for `build-<rev12>` batches. It verifies `revision.txt`,
reads the host architecture's path list, and imports and inspects every
candidate with the bound publisher key. It rejects ambiguous plugin IDs.
Despite the command name, it does not install or enable anything: review its
report, then use the exact-path approval command above. Custom batch tags still
use the exact-path route. No new catalog schema is introduced.

The consumer refuses duplicate paths and lists larger than 64 KiB. The
publisher's list validation does not impose those two limits, and arbitrary
package selections can include non-plugin outputs that inspection refuses.
Keep commit-lookup batches to distinct plugin outputs; the workflow's default
four-plugin selection satisfies that contract. Raw-cache exact-path installation
remains available independently.

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

## CI reuse verification

Run these checks on a build host, never on a handheld:

```sh
nix run .#korri-plugin-churn-check
python3 nix/ci-cache-config-test.py
python3 nix/ci-cache-substitution-test.py "$CORE_STORE_OUTPUT" "$PUBLISHER_STORE_OUTPUT"
```

The churn command checks both supported architectures by default. Use
`-- --system x86_64-linux` or `-- --system aarch64-linux` for one architecture.
The substitution command needs two existing, input-addressed published outputs
without references. It downloads each into an empty isolated store, verifies signatures and content,
and proves unsigned and wrong-key exports fail without registering paths.
It neither builds nor installs the fetched outputs in the host store.
Source evaluation uses the normal Nix store. The test depends on live cache access.

The 2026-09-29 verification passed all five source mutations on both architectures,
with 21 selected packages per architecture. The original typecheck failed the
unrelated-change assertion on both architectures before the contract-file fix.
The final source-copy fixture preserves the original NAR hash before mutation.
Two real signed cache downloads and four signature refusals passed. Both job
configurations passed effective-configuration tests. Publishing also refuses an
inherited Core cache before writing the GitHub environment.

Read-only metadata probes found coverage for seven of twelve queried current
outputs across both architectures. Both Tailscale outputs, both Sunshine outputs,
and the x86 plugin-host output lacked metadata in either custom cache. These
probes did not verify their complete closures. A later live probe received HTTP
403 from GitHub. Cache coverage and availability still limit reuse.

Before this batch, [run 36588085951](https://github.com/korri-os/plugins/actions/runs/36588085951)
measured these CI steps. Jobs overlap, so these durations are not additive.

| CI step | Measured time |
| --- | --- |
| Cold-host lifecycle gate | 38m04s |
| Broad x86 validation | 20m24s |
| Selected x86 package builds | 5m54s |
| x86 signing and preparation | 2m47s |

Local mutation evaluations took 72.37 seconds for x86 and 55.54 seconds for ARM.
All eleven x86 check outputs were reused without builds on two subsequent runs,
at 49.21 and 48.05 seconds. The existing cold-host lifecycle gate passed locally
in 1285.35 seconds. Its unchanged rerun reused the result in 10.63 seconds.
The typecheck's actual derivation inputs contain the consumed contract file,
not the Core source root.

These local numbers are build-host measurements, not CI timings. The regression
adds an evaluation gate. Identical uncached checks still run, and changed
dependencies still require builds.

Post-change [run 36651820275](https://github.com/korri-os/plugins/actions/runs/36651820275)
passed on 2026-09-30 at `dc51e438e97b31c6f35d7adf382086676b963416` with
`publish=false`. Both architecture jobs passed the real cache-configuration and
source-invalidation gates, all existing checks, selected package builds, signing,
and preparation. The cold-host lifecycle passed. Publication was skipped.
Logs show publisher-cache downloads in both build jobs and lifecycle verification.
This run shows no Core-cache download; the isolated-store test separately verifies
that source. The downloaded architecture artifacts combine locally without
metadata or signature conflicts. This is not live publication acceptance.

| CI step | x86 | ARM |
| --- | --- | --- |
| Cache configuration | 3s | 3s |
| Cache-configuration regression | 6s | 5s |
| Source-invalidation regression | 1m23s | 1m07s |
| Broad validation | 26m16s | 7m35s |
| Selected package builds | 7s | 6s |
| Signing and preparation | 4m09s | 3m32s |
| Cold-host lifecycle | 49m31s | Not run |

These step durations come from GitHub's completed-job timestamps. Jobs overlap.
Selected builds follow broad validation, which can already build their outputs;
that step's short duration alone does not prove a cache speedup. This run did not
show an overall speedup: x86 validation and lifecycle both took longer than the
recorded baseline. The Core input also changed between the two runs, so this is
not a controlled comparison. No live publication or handheld operation belongs
to this batch.

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

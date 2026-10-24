# Move cache metadata to Pages

This is an explicit operational migration, not a runtime compatibility route.
The signing key, output paths, NAR URLs and binary releases stay unchanged.
The existing `cache` release remains readable but receives no new metadata.

## Stage metadata without remote writes

Use a clean checkout of the tested publisher commit. Record its full SHA and
check `test "$(git rev-parse HEAD)" = "$EXPECTED_SOURCE_SHA"` before builds or
uploads. Keep source checkouts for plugin builds pinned independently from the
publisher tool checkout.

```sh
nix run .#korri-cache -- migrate-metadata /tmp/metadata --repo OWNER/REPO
```

The command accepts only `nix-cache-info` and Nix-named narinfos. It downloads
all release assets, checks their sizes and GitHub SHA256 digests, and verifies
that the asset snapshot did not change during export. It changes no byte or
signature. It fails without a completed output directory on a conflict.

## Publish the staged index

After approval, create an orphan `cache-index` branch from the staged files.
Add an empty `.nojekyll` and the reviewed Pages workflow. Push the branch without
force. Enable Pages with `build_type: workflow`. The default branch must contain
`.github/workflows/cache-pages.yml` so manual workflow dispatch works. A Pages
branch is not a plugin source checkout and contains no signing key.

Dispatch `cache-pages.yml` from `main`. Compare every served file with the
staged bytes. Use Nix to resolve a known output from the new cache, with its
existing publisher key. Do not change a device binding until that verification
passes.

## New publications

The existing `build`, `export`, `prepare` and `combine` commands retain their
plugin batch evidence and architecture-specific offline metadata. `publish`
now takes `--index-branch cache-index --cache-url https://OWNER.github.io/REPO/`
instead of a mutable metadata release tag. It publishes and verifies the NAR
batch before appending metadata. It explicitly dispatches the Pages workflow
and waits for exact-byte visibility. Existing matching metadata retains its
first URL. A changed signature or signed field is a conflict, not an overwrite.

Other publisher repositories use this same tool at a full tested commit. They
do not carry another copy. Their Pages workflow uses the same deployment shape.
Their signing keys and rights reviews remain separate from this migration.

## Devices and rollback

The plugin host compares a receipt's raw-cache URL with the exact bound URL.
Changing a binding invalidates activation under old receipts even when the key
stays unchanged. Core's one-off `nix/cache/migrate-plugin-receipts.py` prepares
new approvals through the existing `seed-graph` producer, without changing any
package, data directory, enabled state or GC root.

Stop host consumers during the device cutover. Back up bindings and exact
receipt bytes, approve the new graph digests, change the binding, and apply
reviewed receipts before normal host restore. Dependency graphs require a
coordinated migration, not a sequence of leaf updates. The script refuses
pending operations, stale approvals, key rotations and changed live receipts.

Rollback restores both old bindings and original receipt bytes. A system reboot
alone does not restore receipts. Keep the old releases and GC roots. Personal
local caches remain bound until selected outputs have approved public sources;
never copy a private cache into the public index as part of this operation.

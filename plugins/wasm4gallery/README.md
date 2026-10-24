# WASM-4 Gallery

`@korri:wasm4gallery` is an acquisition provider, separate from the `wasm4`
native runner. Its name follows the legacy acquisition fixture provider.

Search reads `https://wasm4.org/play/` and filters the actual static catalog's
card titles and authors locally (at most 50 results). Details read the selected
`/play/<slug>/` page. Resolution requires that page's explicit link to
`/carts/<same-slug>.wasm`, rather than guessing that a cart exists. Details
include author and licence text when those are present. A page with no matching
cart link has no artifact in details and resolves as unsupported. HTTP or markup
failure is not an empty search. Slugs, URLs and download links use strict
anchored patterns. Only `wasm4.org` is approved; external author links are data,
not new fetch permissions.

Runtime compatibility is untested. The WASM header is format evidence only.
Engine and cartridge licences differ. No downloaded cartridge or catalog excerpt
is committed. Fixtures are original synthetic data; the production catalog is
never a fixture array.

See [cohort checks, output wiring and the opt-in live/Core RPC probe](../tic80gallery/README.md).
The live specimen is Snake. The fetched 2026-10-24 file is 11394 bytes, not the
16846 bytes reported in the earlier research. No native gameplay was tested.

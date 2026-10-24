# LowRes NX Programs

`@korri:lowresnxgallery` searches the actual upstream community catalog through
`https://lowresnx.inutilis.com/programs.php?search=<query>`. It references the
native `lowresnx` system and declares no runner. The `gallery` suffix keeps
this source identity separate from the native `@korri:lowresnx` core package,
as with TIC-80 and WASM-4.

Search reads the site's program cards (at most 50 results). Only the site's
explicit `No search results for` answer counts as an empty result. A missing
heading, missing/malformed cards, or HTTP failure remains an error. Details
read `/topic.php?id=<numeric-id>`, check the canonical topic URL, and read the
title, author and primary player attachment. Later comments can carry old or
unrelated `.nx` files: resolution requires the player's filename and an actual
same-host upload link for it. It never chooses an arbitrary comment upload.
Only `lowresnx.inutilis.com` is approved.

The live specimen is Heaven's Burger, topic 3873. An author-offered `.nx` file
is an acquisition-format observation, not runtime compatibility or an open-source
licence. Refer to each author's terms before redistribution. No third-party game
bytes or catalog excerpts are committed. All fixtures are original test data.

See [cohort checks, output wiring and the opt-in live/Core RPC probe](../tic80gallery/README.md).

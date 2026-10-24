# Pyxel Official Examples

`@korri:pyxelgallery` is separate from the `pyxel` runner directory and system.
The suffix follows `tic80gallery` and `wasm4gallery`. The displayed source is
**Pyxel Official Examples**, not all Pyxel community games.

Search, details and resolution read the actual finite GitHub contents endpoint:

`https://api.github.com/repos/kitao/pyxel/contents/python/pyxel/examples/apps?ref=5d8e7b4f37c106684c1e91692772569a32a5e3d4`

This is the full upstream commit behind version **2.9.9**. GitHub's annotated
`v2.9.9` tag object `e8052ccef8b0840f903af5260d64059658c1b285` resolves to
`5d8e7b4f37c106684c1e91692772569a32a5e3d4` through the Git tag API
(`https://api.github.com/repos/kitao/pyxel/git/tags/e8052ccef8b0840f903af5260d64059658c1b285`).
The version is a display label; catalog, source-reference and raw-download URLs
all use that full commit. Mutable tag URLs and metadata are not accepted.

At inspection this lists seven `.pyxapp` files: `30sec_of_daylight`,
`cursed_caverns`, `laser-jetman`, `mega_wing`, `megaball`, `space_rescue`,
`vortexion`. Production never embeds that list. It filters the current API data,
validates file type, path, versioned HTML/raw URLs and size, then searches the
actual filenames locally. Titles are filenames with separators replaced by spaces,
not invented game metadata. Details report those filenames and sizes. There is
no hardcoded game description or unverified blanket MIT claim.

Resolution rechecks the catalog and returns the actual versioned
`https://raw.githubusercontent.com/kitao/pyxel/5d8e7b4f37c106684c1e91692772569a32a5e3d4/python/pyxel/examples/apps/<filename>.pyxapp`
through the existing `FinalDownload` contract. Only `api.github.com` and
`raw.githubusercontent.com` are approved. GitHub HTML URLs are references;
handlers never fetch github.com, itch.io, a showcase, or external dependencies.
HTTP/rate-limit, JSON and row errors are failures, not empty results.

## Native-container and trust boundary

A `.pyxapp` is a native Pyxel ZIP container. **Integration requires the parent's
Core change that preserves a declared nontransport format only when the existing
byte-evidence matcher positively identifies it.** The runner supports `.pyxapp` only, not mixed `.py` projects, and must declare
its actual `PK0304` format evidence. Without that coordinated change Core unpacks the
file, which breaks native multi-module apps. This provider does not rename ZIP
bytes as `.py`, change wire fields, or substitute single-script support for the
seven-file catalog. Package/consumer checks must prove native bytes stay intact.

The considered narrower alternative was to keep generic extraction and discover
one `.py` file plus adjacent resources. Space Rescue has that shape; 30 Seconds
of Daylight has many modules and fails the exactly-one-unit rule. That alternative
would exclude valid native carts and is not the chosen behavior. The native
byte-evidence option uses existing producer/consumer rules without an engine
literal in Core. Its cost is a narrow ADR0030 exception: native ZIP-shaped formats
must be distinguished from transport archives. Byte evidence is identification,
not proof of safe container contents or safe Python code.

Inert acquisition never executes Python. Running a Pyxel app does execute author
Python with the existing native-game process permissions. The existing host
boundary is not a new full Python security sandbox. Dependencies, gameplay and
compatibility of these seven apps are untested. API and raw URLs are pinned to the full upstream commit, not the mutable
release tag. The provider adds no content-hash wire field. Controlled execution
still requires the reviewed Space Rescue SHA-256 allowlist; a source revision
alone is not a claim that all app code is trusted.

The live probe only downloads Space Rescue; its measured SHA-256 is
`250ababacc8f8b50a0e12c30e966b81e6aea1d8559e065a9a734baf59ba82be9`.
Parent reviewed that pinned code for controlled native acceptance. No other
third-party app is authorized for execution by this probe. Per-app code/assets
retain their own rights; an engine licence does not establish cart rights.
No upstream code or carts are committed. Fixtures are original synthetic records.

See [cohort checks, output wiring and the opt-in live/Core RPC probe](../tic80gallery/README.md).

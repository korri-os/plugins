# PuzzleScript Gallery

`@korri:puzzlescript` follows the legacy provider name and references the
independent native `puzzlescript` system. It does not provide a browser runtime.

Search reads `https://www.puzzlescript.net/games_dat.js`, then filters its real
catalog titles and authors locally (at most 50 results). The parser accepts only
the observed single `let games_gallery = [...]` assignment, JSON strings/objects,
optional leading line comments, and trailing commas outside strings. `JSON.parse`
reads the inert data. No `eval`, Function, import, JavaScript expressions, or
remote code execution exists. Invalid data remains a parser error, not empty.

The gallery also contains external HTML exports and forks. Only exact original
`https://www.puzzlescript.net/play.html?p=<gist-id>` records are included.
Details recheck that catalog row and fetch its raw
`https://gist.githubusercontent.com/anonymous/<gist-id>/raw/script.txt`.
Resolution does the same in at most three calls (two requests). HTTP failures,
missing gists, and unsupported source responses remain distinct. Only
`www.puzzlescript.net` and `gist.githubusercontent.com` are approved.

A final download requires raw text with the expected PuzzleScript sections,
not HTML or a text/html response. It saves those unchanged bytes under
`<gist-id>.pz` via the existing `FinalDownload.filename` field. Nothing
extracts a script from an HTML export or labels HTML as `.pz`. This conservative
source check can exclude valid unusual scripts; it does not prove engine/fork
compatibility. Pattern:Script and other fork features are not promised.

The live specimen is Atlas Shrank, gist 6994394. Public gist visibility does
not grant a redistribution licence. No third-party scripts or gallery excerpts
are committed. The committed source fixture is original PuzzleScript-shaped test
data, not an acceptance game; the catalog fixture and malformed variants are original synthetic data.

See [cohort checks, output wiring and the opt-in live/Core RPC probe](../tic80gallery/README.md).

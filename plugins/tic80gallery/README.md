# TIC-80 Gallery

`@korri:tic80gallery` searches the real TIC-80 `Play/Games` directory. It is
independent of the native runner. It declares no system and references `tic80`.
Legacy's acquisition fixture provider supplies the name; the live native SURF
catalog supplies the records and download paths.

All three handlers are pure response turns. Search, details and resolution
request `https://tic80.com/json?fn=dir&path=Play/Games`. Search filters names
and filenames locally and returns at most 50 results. Details find the selected
numeric cart id in the same catalog. Resolution uses that row's validated
32-hex hash and actual `.tic` filename, returning
`https://tic80.com/cart/<hash>/<filename>.tic`. Only `tic80.com` is approved.
There is no guessed download for a cart absent from the current directory.

A blank query returns no claims without HTTP. A nonmatching query against a
valid catalog returns no claims. HTTP, JSON and row failures remain errors.
The directory is bounded by Core's 512 KiB response limit. This is the
`Play/Games` directory, not an exhaustive query over all TIC-80 content.

## Rights and limits

Cartridges remain their authors' works. Neither the TIC-80 engine licence nor
public download availability grants a cartridge redistribution licence. No
third-party cart, gallery excerpt, or downloaded script is bundled. All text in
`fixtures/` is original synthetic test data shaped to the observed producer.
No live-data recording mode exists in the probe.

No catalog game is claimed runtime-compatible. A direct `.tic` file establishes
an acquisition format, not successful gameplay, controls, audio or save behavior.

## Cohort checks and publisher wiring

The same source-only pattern applies to `wasm4gallery`, `lowresnxgallery`,
`puzzlescript` and `pyxelgallery`. Each directory has `plugin.ts`, `plugin.nix`,
`plugin.test.ts` and original `fixtures/`. Runtime imports are **type-only** and
use the exact existing generated `korrid` treaty. No runtime helper is needed.
Only `plugin.ts` and the generated manifest belong in a package. The cohort
probe imports these five implementations as test tooling; do not package it.

Parent composition must add these existing-builder calls and outputs on both
Linux architectures. No root composition file was changed by the provider work.

| Directory / `acquisitionPlugin` argument | Package output | Existing `acquisitionCheck` output |
| --- | --- | --- |
| `tic80gallery` | `korri-plugin-tic80gallery` | `korri-tic80gallery-plugin` |
| `wasm4gallery` | `korri-plugin-wasm4gallery` | `korri-wasm4gallery-plugin` |
| `lowresnxgallery` | `korri-plugin-lowresnxgallery` | `korri-lowresnxgallery-plugin` |
| `puzzlescript` | `korri-plugin-puzzlescript` | `korri-puzzlescript-plugin` |
| `pyxelgallery` | `korri-plugin-pyxelgallery` | `korri-pyxelgallery-plugin` |

Read each exact host list from its `plugin.nix` for `acquisitionCheck`; do not
expand existing itch.io permissions. Existing native runner declarations must
supply the corresponding systems and file extensions. Pyxel additionally needs
Core's positive byte-evidence native-container handling before integration.

Focused offline tests (48 tests across five test files, not
live traffic):

```sh
bun test plugins/tic80gallery/plugin.test.ts plugins/wasm4gallery/plugin.test.ts \
  plugins/lowresnxgallery/plugin.test.ts plugins/puzzlescript/plugin.test.ts \
  plugins/pyxelgallery/plugin.test.ts
```

The integrated `acquisitionCheck` also checks strict TypeScript, package contents
and host admission using Core's generated contract. Parent runs those package
checks after wiring. There is no repo-wide provider lint configuration; a
scoped Biome recommended lint can check only these TypeScript files.

## Opt-in live probe

`live-probe.ts` is a single test entry point for all five providers. `--live`
replays their real handlers against live upstreams and downloads a specimen in
memory. It enforces finite hosts, redirect and body bounds, then reports a
SHA-256. It never evaluates upstream JS or executes a cart. This checks
transport and parsing in Bun, **not** Core's QuickJS host or acquisition.

```sh
bun plugins/tic80gallery/live-probe.ts tic80gallery --live
# Also accepts wasm4gallery, lowresnxgallery, puzzlescript, pyxelgallery.
```

`--rpc` instead calls the existing local Core `/rpc` operations. Use a separately
started, approved disposable Core instance with the real packages installed,
enabled and host permissions approved. Keep signature checks enabled. Set
`KORRI_PROBE_RPC=http://127.0.0.1:<port>/rpc`, `KORRI_PROBE_CAPABILITY` and, if
required by that host, `KORRI_PROBE_ORIGIN`. Never commit or log the capability.
`--rpc` runs real provider listing, search and details through Core. Adding
`--acquire --isolated` explicitly permits importing one cart into that disposable
instance, then polls for `Imported`. It performs no deletion or launch. A
120-second timeout leaves the job for explicit inspection/cancellation.

```sh
bun plugins/tic80gallery/live-probe.ts tic80gallery --rpc --acquire --isolated
```

Do not use an existing person's library as the probe instance. Pyxel's specimen
is only the parent-reviewed Space Rescue from version 2.9.9, with the full
upstream revision pinned by `pyxelgallery`. Inert acquisition is not
permission to run arbitrary downloaded Python. Native launch acceptance belongs
to the separate reviewed runner integration.

### Live transport observations, 2026-10-24 06:20 UTC

All five searches, unmatched queries, details, resolutions and specimen downloads
passed. These observations correct earlier research's WASM-4 sizes; they are
measurements of the fetched files, not compatibility results.

| Provider | Query / claims | File / bytes | SHA-256 |
| --- | --- | --- | --- |
| TIC-80 | `panda` / 17 | `8_bit_panda.tic` / 132361 | `e0d94db2984675ed3669267db2e57b9d602a0a56a9d24fc1e9d9d6009aaeef53` |
| WASM-4 | `snake` / 2 | `snake.wasm` / 11394 | `f99dcf9e76d3427020169d78c284f53c9e81d2e5d71c0a648da35fdfd2de9e64` |
| LowRes NX | `burger` / 1 | `vy7cdsz3g8_Heavens_Burger.nx` / 54041 | `7f4813db8ef1c80e69cd7a92a062b8421f40b79e9ddc69df662b33770712dfd6` |
| PuzzleScript | `atlas shrank` / 1 | raw `script.txt`, saved as `6994394.pz` / 10283 | `5e3b8e9b0e01911742632dfda598b7818383e4e09a6f44940aa72a1188752eb3` |
| Pyxel | `space rescue` / 1 | `space_rescue.pyxapp` / 4207 | `250ababacc8f8b50a0e12c30e966b81e6aea1d8559e065a9a734baf59ba82be9` |

Core RPC import, packaging/admission, target execution and physical acceptance
were not run by this provider work. Full end-to-end support needs those gates.

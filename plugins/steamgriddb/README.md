# SteamGridDB

`@korri:steamgriddb` finds artwork for a game on SteamGridDB
(https://www.steamgriddb.com): a square tile, a poster, a hero and a logo. It
is a port of korrid's built-in fetcher, Core
`services/korrid/src/enrichment/steamgriddb.rs` at `0d0a2513`, which Core
ADR 0032 (`docs/adr/0032-steamgriddb-artwork-comes-from-a-plugin.md`) moves
out of korrid.

`plugin.ts` performs no effects. It has one handler,
`game-assets.candidates`, and no `providers` export. The handler returns the
GET requests it needs, and korrid calls it again with the responses (Core
ADR 0016, `services/korrid/SCRIPTING.md`, "Request and response turns").
korrid makes every request, downloads the image it chooses, checks it and
stores it.

## Your own API key

**No key ships with this plugin.** SteamGridDB gives each account its own API
key. Each person creates a key in their SteamGridDB account and enters it on
this plugin's row in Korri's settings, once on each device.

The plugin never sees the key (Core ADR 0034,
`docs/adr/0034-korrid-holds-plugin-secrets-and-plugins-never-see-them.md`).
`plugin.nix` names `www.steamgriddb.com` as `credentialHost`. korrid keeps the
key in its private folder and adds it as `Authorization: Bearer` to requests
for that host only. The image host never gets the key. `plugin.ts` sets no
`authorization` header, and korrid refuses one from a plugin. Without a key,
korrid does not call the handler.

## SteamGridDB's terms of use

SteamGridDB's Terms of Use (effective 2019-07-31, read 2026-10-23 from the
site's `Terms.jsx` bundle, as Core ADR 0032 section 7 records) say a user
must not:

- "access the Service for any reason other than your personal,
  non-commercial use solely as permitted by the normal functionality of the
  Service"
- "make any automated use of the Site, the Service or the related systems"
- "distribute any part or parts of the Site or the Service without our
  explicit written permission"

What this plugin does against those terms:

- Each person uses their own key, for the games on their own device.
- korrid stores one image for each role of a game on that device. Korri never
  redistributes an image, and no image is in this repository or this package.
- korrid looks artwork up in the background after it finds new games. That
  is still automated use as the terms are written.

**Owner decision, 2026-10-23** (Core ADR 0032 section 7): publish the plugin
in `korri-os/plugins` without asking SteamGridDB first. The cost: after
publication, SteamGridDB can ask for the plugin's withdrawal or revoke the
keys that people use with it.

## Requests

All requests are `GET` to `https://www.steamgriddb.com/api/v2`, with
`accept: application/json`. One lookup is three handler calls and five
requests; Core ADR 0016 allows four calls and eight requests a turn.

| Turn | Request | Role |
|---|---|---|
| 1 | `search/autocomplete/<title>` | |
| 2 | `grids/game/<id>?dimensions=512x512&styles=alternate,blurred,material,no_logo` | `tile` |
| 2 | `grids/game/<id>?dimensions=600x900` | `poster` |
| 2 | `heroes/game/<id>` | `hero` |
| 2 | `logos/game/<id>?mimes=image/png` | `logo` |

Every turn 2 request also has `types=static`, `nsfw=false` and `humor=false`.
The tile's `dimensions` and `styles` are those of main's `grids_for_game`. In
the search path, `/` and `?` in the title become spaces (main's
`url_path_segment`) and the rest is percent-encoded.

## Match

The search answers with its ten nearest names even when none is the game.
"Super Metroid Redesign" answers Super Metroid and nine other hacks. So the
plugin accepts a game only as main's `exact_verified_match` does:

1. Keep the names that equal the title after main's `normalized_match_name`:
   lower case, every character that is not a letter or a digit becomes a
   space, words joined by one space. "Wario-Land 4™" equals "wario land 4".
   Accents stay: "Pokemon" is not "Pokémon".
2. Of those, keep the games SteamGridDB marks `verified`.
3. Exactly one game must remain.

No equal name, no verified game and more than one verified game all answer
`{ candidates: [] }`, and turn 2 is not asked. A title with no letter or
digit answers the same with no request.

## Filter and order

The result is `{ candidates }`. Each candidate is
`{ role, width?, height?, source: { id, url } }`: `width` and `height` are
the asset's, `source.id` is the asset id as a string, and `source.url` is the
asset's `url`, unchanged. korrid takes the first candidate of each role.

- **Dropped:** an asset whose `nsfw`, `humor` or `epilepsy` flag is anything
  but `false` or absent, and an asset whose `tags` list names one of them
  (main's `safe_grid_tags`).
- **Tile styles:** main's `choose_grid` keeps a tile only when its style is
  `alternate`, `blurred`, `material`, `white` or `black`, or it has none.
  This is ported as it is. It means a `no_logo` tile, which the request asks
  for, is not used.
- **Order within a role:** the preferred size, then style, then `language`
  `en` first, then the API's own order. `score` is not used: it was 0 on all
  444 assets observed.
- **Preferred size:** the plugin prefers art no larger than a 1920x1080
  screen needs. A hero no wider than 1920 px comes before every wider one, a
  logo no wider than 1024 px before every wider one, and a poster no larger
  than 600x900 before every larger one. korrid takes the first candidate, and
  the shell keeps 24 MiB of decoded pixels for a surface. A 3840x1240 hero is
  19 MB once decoded and a 3611x1877 logo is 27 MB; a 1920x620 hero is under
  5 MB. A larger asset still follows, so a game that has only larger ones
  keeps its art. An asset whose size is not known counts as larger. Tiles
  have no preferred size: the request asks for 512x512 only.

| Role | Style order |
|---|---|
| `tile`, `poster`, `hero` | `alternate`, `material`, `blurred`, then `white_logo` and `no_logo` together, then any other |
| `logo` | `official`, `white`, `custom`, `black`, then any other |

SteamGridDB states no style preference. This order is the one the Velvet
mockup's art was picked with on 2026-11-11 (`pick` in the mockup's
`scripts/fetch-sgdb.sh`).

A list that is empty, such as the heroes of Anguna, gives no candidate for
that role. A response that is not 2xx JSON with a `data` list fails the whole
lookup, also when the other three lists are good. korrid then asks again
after the next rescan, instead of keeping a game with part of its art.

## Hosts

`plugin.nix` declares two hosts. korrid refuses every other host, for the API
turns and for the image download.

| Host | Use | Evidence |
|---|---|---|
| `www.steamgriddb.com` | the API; the only host that receives the key | SteamGridDB OpenAPI |
| `cdn2.steamgriddb.com` | images | The `url` of all 444 assets in the responses observed on 2026-11-11 (24 lists, 6 games) is `https://cdn2.steamgriddb.com/…`, with no query and no fragment. |

If SteamGridDB moves its images to another host, korrid refuses the
download, and `plugin.nix` needs the new host and a new approval.

## Changes from main's fetcher

- Three more roles: `poster`, `hero` and `logo` (Velvet contract, 2026-11-11).
- The search sends the title as it is. Main sent the normalized title and
  `types=game`. The responses observed on 2026-11-11 answer plain titles.
- The order is preferred size, style, language, API order. Main ordered by
  `score`.
- The asset's `nsfw`, `humor` and `epilepsy` flags are read. Main read only
  `tags`, which no observed response has.
- No title is proposed, no retry waits, and no attempt is recorded. Core
  ADR 0032 sections 2 and 4 give those to korrid or drop them.

## Fixtures

`fixtures/` holds excerpts of SteamGridDB API v2 responses observed on
2026-11-11 with a personal key. The key travelled only in the request header
and is in no file. Each asset's `author` is removed and its `notes` is `null`.
No image is committed. The unit tests read only these files.

| File | Content |
|---|---|
| `search-super-metroid.json` | The ten names for "Super Metroid". The search answered "Super Metroid Redesign" with the same bytes. |
| `search-pokemon-emerald.json` | The ten names for "Pokemon Emerald". |
| `search-anguna.json` | The four names for "Anguna". |
| `search-empty.json` | The answer for "µCity": no names. |
| `pokemon-emerald-posters.json` | 8 of the 50 assets returned (`total` 114), in the API's order: positions 0, 1, 3, 29, 32, 40, 41, 42. |
| `pokemon-emerald-heroes.json` | 4 of 20: positions 0, 1, 3, 13. |
| `pokemon-emerald-logos.json` | 9 of 35: positions 0, 1, 5, 8, 10, 11, 15, 16, 24. The first is a 3611x1877 logo. |
| `super-metroid-heroes.json` | 5 of 27: positions 11, 12, 15, 18, 26. The first is a 3840x1240 hero. |
| `anguna-posters.json`, `anguna-heroes.json`, `anguna-logos.json` | Every asset: 2 posters, 0 heroes, 2 logos. |
| `constructed-tiles.json` | **Not an observed response.** No `dimensions=512x512` list was recorded. This list is written by hand in the observed asset shape; its ids and URLs name nothing real. |

There is no live probe: a probe needs a key.

## Checks

Packaging ships only `plugin.ts` and the generated manifest. Build on a build
host, never on a device. `korri-steamgriddb-plugin` checks the manifest
(`hosts` and `credentialHost`), the package contents, host admission,
`tsc --strict` and the unit tests (`nix/acquisition-plugin-check.nix` and
`check.nix`).

```sh
nix build --no-link .#checks.x86_64-linux.korri-steamgriddb-plugin
bun test plugins/steamgriddb/plugin.test.ts
```

The package and its Nix check need a Core that knows `credentialHost` (Core
ADR 0034) and admits `hosts` for a plugin with a `game-assets.candidates`
handler (Core ADR 0032). Core `0d0a2513`, the pin when this plugin was
written, has neither: its builder refuses `credentialHost`, and its host
refuses `hosts` without a `providers` export. `bun test` and `tsc` need no
Core change.

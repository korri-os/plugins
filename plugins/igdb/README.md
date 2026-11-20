# IGDB

`@korri:igdb` finds artwork for a game on IGDB (https://www.igdb.com): logos,
covers and artworks. It is slice 5 of the Velvet layered art contract and
follows `@korri:steamgriddb` (Core ADR 0032, ADR 0090).

`plugin.ts` performs no effects. It has one handler,
`game-assets.candidates`, and no `providers` export. The handler returns the
POST requests it needs, and korrid calls it again with the responses (Core
ADR 0016, `services/korrid/SCRIPTING.md`, "Request and response turns").
korrid makes every request, downloads the images, checks them and stores
them.

**Not published.** Publication waits on korri#558: the Twitch Developer
Services Agreement allows a 24-hour cache, and korrid keeps images. This
plugin lives on the branch `velvet-art-igdb` only.

## Your own Twitch client ID and secret

**No key ships with this plugin.** IGDB accepts only application
credentials of a Twitch application (api-docs.igdb.com, "Account Creation").
Each person registers their own application in the Twitch developer console
(client type `Confidential`, an account with two-factor authentication),
and enters its client ID and client secret on this plugin's row in Korri's
settings, once on each device, written as one value:

```
<client id>:<client secret>
```

The plugin never sees either value, or the token (Core ADR 0034 and its IGDB
amendment). `plugin.nix` declares:

- `credentialTokenUrl = "https://id.twitch.tv/oauth2/token"`: korrid sends the
  client ID and client secret there, in a form body, with
  `grant_type=client_credentials`, and gets an app token.
- `credentialHost = "api.igdb.com"`: korrid adds `Client-ID` and
  `Authorization: Bearer <token>` to requests for that host only.

korrid keeps the token in memory, gets a new one once after a 401, and stops
the pass with `CredentialUnauthorized` only if that also fails. The image
host never gets a credential. Without the value, korrid does not call the
handler.

## Requests

Every request is a `POST` to `https://api.igdb.com/v4` with an Apicalypse
text body and `accept: application/json`. IGDB documents only this form
(api-docs.igdb.com, "Requests"). korrid sends the body as
`text/plain; charset=utf-8` (Core ADR 0016, IGDB amendment). One request per
turn keeps a lookup inside IGDB's rate limit of 4 requests a second.

| Turn | Endpoint | Body |
|---|---|---|
| 1 | `games` | `search "<title>"; fields id,name; where platforms = (<ids>) & version_parent = null; limit 50;` |
| 2 | `multiquery` | `query covers "covers" { … where game = <id>; limit 50; };` and the same for `artworks` and `logos` |

Every art query asks `fields image_id,width,height,alpha_channel,animated`.
IGDB's `games` fields have no `logos`, so logos are asked by
`where game = <id>` (IGDB docs, Logo). In the title, a `"`, a `\` or a control
character becomes a space; the match is made on normalized names anyway.

A game with a stored IGDB id skips turn 1: one call and one request.

## Match

Core ADR 0090 sets the rule, as for `@korri:steamgriddb`.

- **Id first.** When the game's public ids hold an `igdb` id, the plugin
  asks for that game's art at once. A value that is not a whole number is
  not used.
- **Platform.** Otherwise the search is filtered by the system's IGDB
  platform ids, `system.externalIds.igdb`, such as `19` and `58` for the
  SNES. Editions are left out with `version_parent = null` (IGDB docs,
  "Search games but exclude versions"). A system with no IGDB id, or no
  system, gives no match and no request: a search over every platform
  answers with games of other systems.
- **Equal names only.** Accents folded (NFD, then the marks dropped), lower
  case, every character that is not a letter or a digit a word break, and a
  trailing `version` word optional. No fuzzy match.
- **One game.** The platform filter is the tie-break by system. korrid
  passes no release year, so two equal names on the system's platforms are
  no match.

A match returns `externalIds: { igdb: ["<id>"] }`. korrid stores it with the
game, so the next lookup goes by id. IGDB exposes no Wikidata id: its
external game sources and website types name none, and Wikidata's property
P5794 links the other way, to the IGDB slug. So no `wikidata` id is
returned.

The SteamGridDB store-type guard and `verified` check have no IGDB
counterpart and are not applied.

## Candidates

The result is `{ candidates, externalIds }`. Each candidate is
`{ kind, width, height, source: { id, url } }` (Velvet contract, slice 3:
`kind` replaces `role`). `source.id` is the IGDB `image_id`. The types
come from Core's generated contract (`GameAssetCandidate`,
`GameAssetCandidates`), so `tsc --strict` refuses a kind korrid does not
admit.

| Kind | From | Format | Kept |
|---|---|---|---|
| `picture` | `covers` and `artworks` | `.jpg` | not `animated` |
| `logo` | `logos` | `.png` | `alpha_channel` true and not `animated` |

Order: the first cover first, so a poster is among the candidates korrid
keeps; then every artwork, the largest first; then the other covers, such as
localized ones. Logos, the largest first. The plugin assumes no ratio: IGDB
says an artwork's "resolution and aspect ratio may vary", and Velvet picks a
picture by its ratio (Velvet contract, slice 4).

## Sizes

`width` and `height` are the size of the image korrid will download,
computed from the stored size IGDB's API gives for the image. The URL is
`https://images.igdb.com/igdb/image/upload/t_<size>/<image_id>.<jpg|png>`.

The plugin uses only IGDB's "Fit" sizes, which scale the whole image to
touch a box and keep its ratio. It picks the largest box that does not scale
the image up; an image smaller than every box is not offered.

| Size | Box | Used for |
|---|---|---|
| `1080p` | 1920x1080 | pictures |
| `720p` | 1280x720 | pictures, logos |
| `cover_big_2x` | 528x748 | pictures, logos |
| `cover_big` | 264x374 | pictures, logos |
| `logo_med` | 284x160 | logos |

The served size is the stored size times
`min(box width / width, box height / height)`, rounded. Measured on
images.igdb.com on 2026-11-20 (from the original, `t_original`, which IGDB's
current docs do not list and the plugin does not use):

| Image | Stored | `1080p` | `720p` | `cover_big_2x` | `cover_big` | `logo_med` |
|---|---|---|---|---|---|---|
| `co1wyy` | 1170x1559 | 811x1080 | 540x720 | 528x704 | 264x352 | 120x160 |
| `co1x7g` | 800x1148 | 753x1080 | 502x720 | 521x748 | 261x374 | 111x160 |
| `co1tnk` | 1200x1128 | 1149x1080 | 766x720 | 528x496 | 264x248 | 170x160 |
| `co1r7f` | 2893x3857 | 810x1080 | 540x720 | 528x704 | 264x352 | 120x160 |
| `co1nqv` | 342x456 | 810x1080 | 540x720 | 528x704 | 264x352 | |
| `ar1bpe` | 1600x190 | 1920x228 | 1280x152 | | | |

So a Fit size also scales a small image up (`co1nqv`), which is why the
plugin takes the largest box that does not. Not used:

- The crop sizes (`screenshot_med`, `screenshot_big`, `screenshot_huge`,
  `thumb`, `micro`) cut the image to their own ratio. IGDB's table also does
  not match what they serve: `screenshot_big` of `co1wyy` was 940x529, not
  889x500.
- `logo_med_2x` served 568x320 for every image above: it fills, it does not
  fit.
- The `_2x` of `1080p` and `720p`: a picture larger than a 1920x1080 screen
  only costs memory.

The `.png` of a Fit size came back as an 8-bit palette PNG for the opaque
images above. Whether a transparent logo keeps its alpha in that form was
not checked: no transparent IGDB image id was known without an API key.
korrid refuses a logo without transparency, so a wrong guess costs a logo,
not a wrong image.

## Hosts

`plugin.nix` declares three hosts. korrid refuses every other host.

| Host | Use | Evidence |
|---|---|---|
| `api.igdb.com` | the API; receives `Client-ID` and the token | api-docs.igdb.com, "Requests" |
| `id.twitch.tv` | the token exchange; receives the client ID and secret in a form body | dev.twitch.tv, "Getting OAuth Access Tokens" |
| `images.igdb.com` | images; receives no credential | api-docs.igdb.com, "Images" |

**Redirects.** korrid downloads an image with no redirect. On 2026-11-20
`images.igdb.com` answered every Fit size above, and `t_original`, with
`200` and the image, from CloudFront, with no redirect. An unknown image id
or size answered `404`. The IGDB docs say nothing about redirects; they say a
removed or replaced image stays for 30 days.

## Fixtures

`fixtures/` holds responses shaped as IGDB's documentation shows them: a
`games` search answers a list of `{ id, name }`, and a multiquery answers a
list of `{ name, result }`. No live IGDB answer is committed, because a call
needs a person's own Twitch application. The game ids are made up. The image
ids `co1wyy`, `co1x7g`, `ar5l8` and `ar1bpe` are real images whose stored
size was measured on images.igdb.com on 2026-11-20; which game they belong
to is not claimed. Every other image id is made up.

| File | Content |
|---|---|
| `search-super-metroid.json` | One equal name, a near name, another game. |
| `search-pokemon-emerald.json` | "Pokémon Emerald Version" and a near name. |
| `search-tetris.json` | Two games named "Tetris": a tie. |
| `search-empty.json` | No game. |
| `art-super-metroid.json` | Two covers, five artworks (one animated, one too small), three logos (one without alpha). |
| `art-empty.json` | Three empty lists. |

There is no live probe: a probe needs a person's own Twitch client ID and
secret.

## Checks

Packaging ships only `plugin.ts` and the generated manifest. Build on a build
host, never on a device. `korri-igdb-plugin` checks the manifest (`hosts`,
`credentialHost` and `credentialTokenUrl`), the package contents, host
admission, `tsc --strict` and the unit tests
(`nix/acquisition-plugin-check.nix` and `check.nix`).

```sh
nix build --no-link .#checks.x86_64-linux.korri-igdb-plugin
bun test plugins/igdb/plugin.test.ts
```

The package and its Nix check need a Core that knows `credentialTokenUrl`
and the raw text body (Core ADR 0034 and ADR 0016, IGDB amendments), and
the candidate `kind` (Core ADR 0091). The
pinned Core does not have them yet: until it does, build with
`--override-input korri <a Core checkout that has them>`.

## Terms

- IGDB is free for non-commercial use under the Twitch Developer Services
  Agreement. Each person uses their own application's keys on their own
  device, so no key is transferred (DSA section IV.B).
- The DSA allows a cache of 24 hours; IGDB's FAQ prefers local storage.
  korrid keeps the images it stores. This conflict is why publication waits
  on korri#558.
- korrid records each image's source (`source.provider`, `source.url`), the
  path to the source the DSA asks for (section VII.C).

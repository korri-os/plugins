// Artwork for a game from IGDB (https://www.igdb.com), Core ADR 0032 and the
// Velvet layered art contract, slice 5. The one handler is a pure request and
// response turn (Core ADR 0016): it returns the POST requests it needs,
// korrid performs them, and korrid calls the handler again with `responses`.
//
// This file never sees the person's Twitch client ID, client secret or token.
// plugin.nix declares `credentialHost` and `credentialTokenUrl` (Core ADR
// 0034, IGDB amendment): korrid exchanges the client pair for an app token at
// id.twitch.tv and adds `Client-ID` and `Authorization: Bearer` itself, to
// api.igdb.com only.

import type {
  PluginGameAssetCandidatesInput,
  PluginHttpRequest,
  PluginHttpRequests,
  PluginHttpResponse,
} from "../../contracts/generated/korrid"

// The candidate shape of the Velvet contract, slice 3: one `kind` instead of
// `role`. It is written here, not imported, because the generated contract
// that carries `kind` lands with the `media` worker's korrid change.
type Kind = "logo" | "picture" | "icon"
interface Candidate {
  kind: Kind
  width?: number
  height?: number
  source: { id?: string; url: string }
}
type CandidatesOutput =
  | PluginHttpRequests
  | { candidates: Candidate[]; externalIds?: Record<string, string[]> }
type GameSystem = NonNullable<PluginGameAssetCandidatesInput["system"]>

export const name = "igdb"
export const title = "IGDB"
export const description =
  "Finds logos, covers and artworks for each game on IGDB, with your own Twitch client ID and secret."

const API_BASE_URL = "https://api.igdb.com/v4"
const IMAGE_BASE_URL = "https://images.igdb.com/igdb/image/upload"
// IGDB's request examples all send `Accept: application/json`.
const JSON_HEADERS = { accept: "application/json" } as const

// This plugin's authority key in public ids (Core ADR 0090): the IGDB game id
// for a game and the IGDB platform id for a system, as text.
const AUTHORITY = "igdb"

// IGDB's default limit is 10 and its largest is 500. The search must see
// every equal name to know a tie; the art lists are short.
const SEARCH_LIMIT = 50
const ART_LIMIT = 50

// --- requests ---------------------------------------------------------------

function httpRequests(requests: PluginHttpRequest[]): PluginHttpRequests {
  return { _tag: "HttpRequests", requests }
}

// An Apicalypse query is the raw text body of a POST (Core ADR 0016, IGDB
// amendment). korrid sends it with `Content-Type: text/plain`.
function query(endpoint: string, body: string): PluginHttpRequest {
  return { url: `${API_BASE_URL}/${endpoint}`, method: "POST", headers: JSON_HEADERS, body }
}

// The search text inside an Apicalypse string. A quote or a backslash
// becomes a space: the match is made here on normalized names, so the search
// only needs to find the game.
function searchText(gameTitle: string): string {
  return gameTitle.replace(/["\\\u0000-\u001f]/g, " ").replace(/\s+/g, " ").trim()
}

// Turn 1 without a stored id: equal names among games on the system's
// platforms, editions excluded (IGDB docs, "Search games but exclude
// versions").
function searchRequest(gameTitle: string, platforms: readonly number[]): PluginHttpRequest {
  return query(
    "games",
    `search "${searchText(gameTitle)}"; fields id,name; ` +
      `where platforms = (${platforms.join(",")}) & version_parent = null; limit ${SEARCH_LIMIT};`,
  )
}

// The art of one game in one multiquery POST: one request per turn keeps a
// lookup inside IGDB's 4 requests a second. `logos` has no field on `games`,
// so each list is asked `where game = <id>` (IGDB docs, Logo).
const ART_LISTS = ["covers", "artworks", "logos"] as const
type ArtList = (typeof ART_LISTS)[number]
const ART_FIELDS = "fields image_id,width,height,alpha_channel,animated"

function artRequest(gameId: number): PluginHttpRequest {
  const body = ART_LISTS.map(
    list => `query ${list} "${list}" { ${ART_FIELDS}; where game = ${gameId}; limit ${ART_LIMIT}; };`,
  ).join("\n")
  return query("multiquery", body)
}

// --- handler ----------------------------------------------------------------

function gameAssetCandidates(input: PluginGameAssetCandidatesInput): CandidatesOutput {
  const responses = Array.isArray(input.responses) ? input.responses : []
  // Id first (Core ADR 0090): a stored IGDB game id skips the search.
  const stored = storedId(input.externalIds)
  if (stored !== undefined) return artTurn(stored, responses)

  const gameTitle = typeof input.title === "string" ? input.title : ""
  const platforms = systemPlatforms(input.system)
  // No platform to filter by, or a title with no letter or digit: no match,
  // and no request. A search over every platform would answer with games of
  // other systems.
  if (platforms.length === 0 || matchName(gameTitle) === "") return { candidates: [] }
  if (responses.length === 0) return httpRequests([searchRequest(gameTitle, platforms)])

  const [search, ...art] = responses
  const match = equalNameMatch(gameTitle, searchGames(search))
  if (match === undefined) return { candidates: [] }
  return artTurn(match, art)
}

function artTurn(gameId: number, art: readonly PluginHttpResponse[]): CandidatesOutput {
  if (art.length === 0) return httpRequests([artRequest(gameId)])
  if (art.length !== 1) throw new Error(`IGDB art: expected 1 response, got ${art.length}`)
  const lists = artLists(art[0])
  return {
    candidates: [...pictureCandidates(lists.covers, lists.artworks), ...logoCandidates(lists.logos)],
    // IGDB exposes no Wikidata id (its external game sources and website
    // types name none), so the match names only its own id.
    externalIds: { [AUTHORITY]: [String(gameId)] },
  }
}

export const handlers = {
  "game-assets.candidates": gameAssetCandidates,
}

// --- ids ----------------------------------------------------------------------

const ID = /^[0-9]{1,15}$/

// The first stored IGDB id that is a whole number. korrid stores what this
// plugin returned, so another value is not this plugin's.
function storedId(ids: unknown): number | undefined {
  return idsOf(ids)[0]
}

function idsOf(ids: unknown): number[] {
  if (!isRecord(ids) || !Array.isArray(ids[AUTHORITY])) return []
  return ids[AUTHORITY].filter((value): value is string => typeof value === "string" && ID.test(value)).map(Number)
}

// The system's IGDB platform ids (Core ADR 0090), such as 19 and 58 for the
// SNES and the Super Famicom.
function systemPlatforms(system: GameSystem | undefined): number[] {
  return isRecord(system) ? [...new Set(idsOf(system.externalIds))] : []
}

// --- match: one game with an equal name ---------------------------------------

interface SearchGame {
  readonly id: number
  readonly name: string
}

// Core ADR 0090. The search answers with near names too, so only an equal
// name counts: no fuzzy match. The platform filter in the query is the
// tie-break by system. korrid passes no release year, so two equal names on
// the system's platforms are no match.
function equalNameMatch(title: string, games: readonly SearchGame[]): number | undefined {
  const wanted = matchName(title)
  const equal = [...new Set(games.filter(game => matchName(game.name) === wanted).map(game => game.id))]
  return equal.length === 1 ? equal[0] : undefined
}

const MARK = /\p{M}/gu
const LETTER_OR_DIGIT = /[\p{Alphabetic}\p{N}]/u

// Core ADR 0090's normalization, as `@korri:steamgriddb` has it. Fold accents
// (NFD, then drop the marks) and case, drop punctuation, and treat a trailing
// `version` word as optional. Every character that is not a letter or a digit
// separates words, as main's `normalized_match_name` does.
function matchName(value: string): string {
  const folded = value.normalize("NFD").replace(MARK, "").toLowerCase()
  let spaced = ""
  for (const character of folded) spaced += LETTER_OR_DIGIT.test(character) ? character : " "
  const words = spaced.split(" ").filter(Boolean)
  if (words.length > 1 && words[words.length - 1] === "version") words.pop()
  return words.join(" ")
}

function searchGames(response: PluginHttpResponse): SearchGame[] {
  const body = json(response, "search")
  if (!Array.isArray(body)) throw new Error("IGDB search did not answer a list")
  return body.map(entry => {
    if (!isRecord(entry) || !isId(entry.id) || typeof entry.name !== "string") {
      throw new Error("IGDB search returned an unexpected game")
    }
    return { id: entry.id, name: entry.name }
  })
}

// --- art ------------------------------------------------------------------------

interface Image {
  readonly imageId: string
  readonly width: number
  readonly height: number
  readonly alpha: boolean
}

// The IGDB image sizes that scale the whole image to fit a box and keep its
// ratio ("Fit" in IGDB docs, Images). The served size is the stored size
// scaled to touch the box, rounded: measured on images.igdb.com on
// 2026-11-20 for all five, upward and downward (README, "Sizes"). The crop
// sizes (`screenshot_*`, `thumb`, `micro`) are not used: they cut the image
// to their own ratio, and IGDB's table does not match what they serve.
interface FitSize {
  readonly name: string
  readonly width: number
  readonly height: number
}
const FIT_SIZES: readonly FitSize[] = [
  { name: "1080p", width: 1920, height: 1080 },
  { name: "720p", width: 1280, height: 720 },
  { name: "cover_big_2x", width: 528, height: 748 },
  { name: "cover_big", width: 264, height: 374 },
  { name: "logo_med", width: 284, height: 160 },
]
// A picture fills a 1920x1080 screen at most. A 1920 px screen shows a logo
// at most about 960 px wide, so a logo starts at 720p.
const PICTURE_SIZES = FIT_SIZES.filter(size => size.name !== "logo_med")
const LOGO_SIZES = FIT_SIZES.filter(size => size.name !== "1080p")

interface Served {
  readonly size: string
  readonly width: number
  readonly height: number
}

// The largest size that does not scale the image up: IGDB scales a small
// image up to its box, and that only makes it soft. An image smaller than
// every box gets none.
function servedSize(image: Image, sizes: readonly FitSize[]): Served | undefined {
  for (const size of sizes) {
    const scale = Math.min(size.width / image.width, size.height / image.height)
    if (scale <= 1) {
      return {
        size: size.name,
        width: Math.max(1, Math.round(image.width * scale)),
        height: Math.max(1, Math.round(image.height * scale)),
      }
    }
  }
  return undefined
}

function candidate(kind: Kind, image: Image, sizes: readonly FitSize[], extension: string): Candidate[] {
  const served = servedSize(image, sizes)
  if (served === undefined) return []
  return [
    {
      kind,
      width: served.width,
      height: served.height,
      source: {
        id: image.imageId,
        url: `${IMAGE_BASE_URL}/t_${served.size}/${image.imageId}.${extension}`,
      },
    },
  ]
}

const servedArea = (entry: Candidate) => (entry.width ?? 0) * (entry.height ?? 0)

// Covers and artworks are pictures, as JPEG. Velvet picks a picture by its
// ratio (Velvet contract, slice 4), so the plugin assumes none: IGDB says an
// artwork's "resolution and aspect ratio may vary". The first cover comes
// first, so a poster is among the few korrid keeps; then every artwork, the
// largest first; then the other covers, such as localized ones.
function pictureCandidates(covers: readonly Image[], artworks: readonly Image[]): Candidate[] {
  const picture = (image: Image) => candidate("picture", image, PICTURE_SIZES, "jpg")
  const [cover, ...otherCovers] = covers.flatMap(picture)
  const art = artworks.flatMap(picture).sort((a, b) => servedArea(b) - servedArea(a))
  return [...(cover === undefined ? [] : [cover]), ...art, ...otherCovers]
}

// Logos keep transparency: only a logo IGDB marks `alpha_channel`, as PNG.
// The largest first.
function logoCandidates(logos: readonly Image[]): Candidate[] {
  return logos
    .filter(image => image.alpha)
    .flatMap(image => candidate("logo", image, LOGO_SIZES, "png"))
    .sort((a, b) => servedArea(b) - servedArea(a))
}

// The multiquery answer: one `{ name, result }` per query, by the names this
// plugin gave. An animated image is not used: korrid stores static images.
function artLists(response: PluginHttpResponse): Record<ArtList, Image[]> {
  const body = json(response, "art")
  if (!Array.isArray(body)) throw new Error("IGDB art did not answer a list")
  const lists: Partial<Record<ArtList, Image[]>> = {}
  for (const entry of body) {
    if (!isRecord(entry) || typeof entry.name !== "string" || !Array.isArray(entry.result)) {
      throw new Error("IGDB art returned an unexpected list")
    }
    const list = ART_LISTS.find(name => name === entry.name)
    if (list === undefined) continue
    lists[list] = entry.result.flatMap(image => {
      if (!isRecord(image)) throw new Error(`IGDB ${list} returned an unexpected image`)
      if (image.animated === true) return []
      if (typeof image.image_id !== "string" || !/^[a-z0-9]{1,64}$/.test(image.image_id)) return []
      if (!isPixelCount(image.width) || !isPixelCount(image.height)) return []
      return [{ imageId: image.image_id, width: image.width, height: image.height, alpha: image.alpha_channel === true }]
    })
  }
  for (const list of ART_LISTS) {
    if (lists[list] === undefined) throw new Error(`IGDB art has no ${list} list`)
  }
  return lists as Record<ArtList, Image[]>
}

// --- responses --------------------------------------------------------------------

// A response that is not 2xx JSON fails the operation. korrid then records the
// game as `transient` and asks again after the next rescan (Core ADR 0032).
// That includes a 429: IGDB allows 4 requests a second.
function json(response: PluginHttpResponse, what: string): unknown {
  if (!response.ok) throw new Error(`IGDB ${what} returned HTTP ${response.status}`)
  try {
    return JSON.parse(response.text)
  } catch {
    throw new Error(`IGDB ${what} is not JSON`)
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function isId(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0
}

function isPixelCount(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0
}

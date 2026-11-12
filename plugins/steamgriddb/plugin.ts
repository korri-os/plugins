// Artwork for a game from SteamGridDB (Core ADR 0032). A port of korrid's
// built-in fetcher, Core services/korrid/src/enrichment/steamgriddb.rs at
// 0d0a2513e0fee24f8c5c91f3fb7207c00370ec98. The fetcher called SteamGridDB
// itself. Here the one handler is a pure request/response turn (Core ADR
// 0016): it returns the GET requests it needs, korrid performs them, and
// korrid calls the handler again with `responses`.
//
// This file never sets an `authorization` header and never sees the API key.
// korrid adds `Authorization: Bearer` itself, and only for the host that
// plugin.nix names as `credentialHost` (Core ADR 0034).

import type {
  PluginHttpRequest,
  PluginHttpRequests,
  PluginHttpResponse,
} from "../../contracts/generated/korrid"

export const name = "steamgriddb"
export const title = "SteamGridDB"
export const description =
  "Finds a tile, poster, hero and logo for each game on SteamGridDB, with your own API key."

const API_BASE_URL = "https://www.steamgriddb.com/api/v2"
const JSON_HEADERS = { accept: "application/json" } as const

// --- the operation's wire (Core ADR 0032, section 1) ----------------------
// These mirror `GameAssetRole`, `GameAssetCandidateSource`,
// `GameAssetCandidate`, `GameAssetCandidates`,
// `PluginGameAssetCandidatesInput` and `PluginGameAssetCandidatesOutput` in
// Korri's `contracts/generated/korrid.ts`. Imports of those types replace
// them when this repository pins a Korri that has them.

// An enum in the generated contract; these are its values.
type GameAssetRole = "tile" | "poster" | "hero" | "logo"

interface GameAssetCandidateSource {
  id?: string
  url: string
}

interface GameAssetCandidate {
  role: GameAssetRole
  width?: number
  height?: number
  source: GameAssetCandidateSource
}

interface GameAssetCandidates {
  candidates: GameAssetCandidate[]
}

interface PluginGameAssetCandidatesInput {
  title: string
  responses: PluginHttpResponse[]
}

type PluginGameAssetCandidatesOutput = PluginHttpRequests | GameAssetCandidates

// --- the four art lists of turn 2 -----------------------------------------

// Style preference, lower first; styles that share a number keep the API's
// order. SteamGridDB states no preference and `score` was 0 on every asset
// observed, so this is the order the Velvet mockup's art was picked with on
// 2026-11-11 (README, "Order").
const GRID_STYLE_RANK: ReadonlyMap<string, number> = new Map([
  ["alternate", 0],
  ["material", 1],
  ["blurred", 2],
  ["white_logo", 3],
  ["no_logo", 3],
])
const LOGO_STYLE_RANK: ReadonlyMap<string, number> = new Map([
  ["official", 0],
  ["white", 1],
  ["custom", 2],
  ["black", 3],
])
const UNRANKED_STYLE = 4

// main `choose_grid`: a tile keeps only these styles, or no style at all.
// `white` and `black` are not grid styles and `no_logo`, which the request
// asks for, is not kept. Both are main's behaviour, ported as it is.
const TILE_STYLES: ReadonlySet<string> = new Set([
  "alternate",
  "blurred",
  "material",
  "white",
  "black",
])

interface ArtList {
  readonly role: GameAssetRole
  readonly endpoint: "grids" | "heroes" | "logos"
  readonly query: Readonly<Record<string, string>>
  readonly styleRank: ReadonlyMap<string, number>
  readonly keepsStyle: (style: string | undefined) => boolean
  // The asset's size group, lower first. korrid takes the first candidate, so
  // the first group holds the size a 1920x1080 screen needs. Every other
  // asset still follows: a game that has only those keeps its art.
  readonly sizeGroup: (asset: ArtAsset) => number
}

const anyStyle = () => true
const anySize = () => 0

// In request order: turn 2's responses arrive in this order.
const ART_LISTS: readonly ArtList[] = [
  {
    role: "tile",
    endpoint: "grids",
    // main `grids_for_game`.
    query: { dimensions: "512x512", styles: "alternate,blurred,material,no_logo" },
    styleRank: GRID_STYLE_RANK,
    keepsStyle: style => style === undefined || TILE_STYLES.has(style),
    sizeGroup: anySize,
  },
  {
    role: "poster",
    endpoint: "grids",
    query: { dimensions: "600x900" },
    styleRank: GRID_STYLE_RANK,
    keepsStyle: anyStyle,
    // The size the request asks for.
    sizeGroup: noLargerThan(600, 900),
  },
  {
    role: "hero",
    endpoint: "heroes",
    query: {},
    styleRank: GRID_STYLE_RANK,
    keepsStyle: anyStyle,
    // The shell keeps 24 MiB of decoded pixels for a surface. A 3840x1240
    // hero alone is 19 MB once decoded; a 1920x620 one is under 5 MB.
    sizeGroup: noLargerThan(1920),
  },
  {
    role: "logo",
    endpoint: "logos",
    query: { mimes: "image/png" },
    styleRank: LOGO_STYLE_RANK,
    keepsStyle: anyStyle,
    sizeGroup: logoSizeGroup,
  },
]

function httpRequests(requests: PluginHttpRequest[]): PluginHttpRequests {
  return { _tag: "HttpRequests", requests }
}

// main `url_path_segment`: `/` and `?` would end the path segment.
function searchRequest(gameTitle: string): PluginHttpRequest {
  const term = gameTitle.trim().replaceAll("/", " ").replaceAll("?", " ")
  return {
    url: `${API_BASE_URL}/search/autocomplete/${encodeURIComponent(term)}`,
    headers: JSON_HEADERS,
  }
}

// SteamGridDB's API description (static/openapi.yml) lists `nsfw`, `humor`
// and `epilepsy` for all three endpoints. `false` filters them out.
function artListRequest(list: ArtList, gameId: number): PluginHttpRequest {
  return {
    url: `${API_BASE_URL}/${list.endpoint}/game/${gameId}`,
    query: { ...list.query, types: "static", nsfw: "false", humor: "false", epilepsy: "false" },
    headers: JSON_HEADERS,
  }
}

// --- handler --------------------------------------------------------------

function gameAssetCandidates(
  input: PluginGameAssetCandidatesInput,
): PluginGameAssetCandidatesOutput {
  const gameTitle = typeof input.title === "string" ? input.title : ""
  const wanted = normalizedMatchName(gameTitle)
  // A title with no letter or digit can match no name.
  if (wanted === "") return { candidates: [] }

  const responses = Array.isArray(input.responses) ? input.responses : []
  if (responses.length === 0) return httpRequests([searchRequest(gameTitle)])

  const [search, ...artLists] = responses
  const match = exactVerifiedMatch(wanted, searchGames(search))
  // No match, unverified and ambiguous all mean "no artwork for this title".
  if (match._tag !== "Accepted") return { candidates: [] }

  if (artLists.length === 0) {
    return httpRequests(ART_LISTS.map(list => artListRequest(list, match.game.id)))
  }
  if (artLists.length !== ART_LISTS.length) {
    throw new Error(
      `SteamGridDB art lists: expected ${ART_LISTS.length} responses, got ${artLists.length}`,
    )
  }
  return {
    candidates: ART_LISTS.flatMap((list, index) =>
      roleCandidates(list, artAssets(artLists[index], list.role)),
    ),
  }
}

export const handlers = {
  "game-assets.candidates": gameAssetCandidates,
}

// --- search: one exact, verified name ---------------------------------------

interface SearchGame {
  readonly id: number
  readonly name: string
  readonly verified: boolean
}

type MatchDecision =
  | { readonly _tag: "Accepted"; readonly game: SearchGame }
  | { readonly _tag: "NoMatch" }
  | { readonly _tag: "Unverified" }
  | { readonly _tag: "Ambiguous" }

// main `exact_verified_match`. The search answers with its ten nearest names
// even when none is the game, so only an equal name counts.
function exactVerifiedMatch(wanted: string, games: readonly SearchGame[]): MatchDecision {
  const exact = games.filter(game => normalizedMatchName(game.name) === wanted)
  if (exact.length === 0) return { _tag: "NoMatch" }
  const verified = exact.filter(game => game.verified)
  if (verified.length === 0) return { _tag: "Unverified" }
  if (verified.length === 1) return { _tag: "Accepted", game: verified[0] }
  return { _tag: "Ambiguous" }
}

const LETTER_OR_DIGIT = /[\p{Alphabetic}\p{N}]/u

// main `discovery::title::normalized_match_name`: lower-case each character,
// turn every character that is not a letter or a digit into a space, and join
// the words with one space. Accents stay: "Pokemon" is not "Pokémon".
function normalizedMatchName(value: string): string {
  let spaced = ""
  for (const character of value) {
    for (const lower of character.toLowerCase()) {
      spaced += LETTER_OR_DIGIT.test(lower) ? lower : " "
    }
  }
  return spaced.split(" ").filter(Boolean).join(" ")
}

function searchGames(response: PluginHttpResponse): SearchGame[] {
  return dataList(response, "search").map(entry => {
    if (!isRecord(entry) || !isId(entry.id) || typeof entry.name !== "string") {
      throw new Error("SteamGridDB search returned an unexpected game")
    }
    // main: `verified` is false when absent.
    return { id: entry.id, name: entry.name, verified: entry.verified === true }
  })
}

// --- art lists: safe assets in order of preference --------------------------

interface ArtAsset {
  readonly id: number
  readonly url: string
  readonly width: unknown
  readonly height: unknown
  readonly style: string | undefined
  readonly language: unknown
}

const UNSAFE = ["nsfw", "humor", "epilepsy"]

// The asset's own flags as observed on 2026-11-11, and main `safe_grid_tags`
// for a `tags` list. A flag that is neither `false` nor absent drops the asset.
function isSafe(asset: Record<string, unknown>): boolean {
  if (UNSAFE.some(flag => asset[flag] !== undefined && asset[flag] !== false)) return false
  const tags = Array.isArray(asset.tags) ? asset.tags : []
  return !tags.some(tag => typeof tag === "string" && UNSAFE.includes(tag.toLowerCase()))
}

function artAssets(response: PluginHttpResponse, role: GameAssetRole): ArtAsset[] {
  return dataList(response, `${role} list`).flatMap(entry => {
    if (!isRecord(entry) || !isId(entry.id) || typeof entry.url !== "string" || entry.url === "") {
      throw new Error(`SteamGridDB ${role} list returned an unexpected asset`)
    }
    if (!isSafe(entry)) return []
    return [
      {
        id: entry.id,
        url: entry.url,
        width: entry.width,
        height: entry.height,
        style: typeof entry.style === "string" ? entry.style : undefined,
        language: entry.language,
      },
    ]
  })
}

// Assets known to be no larger than this first, then every other one. An
// asset whose size is not known counts as larger.
function noLargerThan(width: number, height?: number): (asset: ArtAsset) => number {
  return asset => {
    const fits =
      isPixelCount(asset.width) &&
      asset.width <= width &&
      (height === undefined || (isPixelCount(asset.height) && asset.height <= height))
    return fits ? 0 : 1
  }
}

const LOGO_MIN_WIDTH = 480
const LOGO_MAX_WIDTH = 1024

// A 1920 px screen shows a logo at most about 960 px wide. First a logo of
// about that width. Then a wider one: it is only heavier. Last a narrower one
// or one of unknown width: it would be drawn scaled up and soft.
function logoSizeGroup(asset: ArtAsset): number {
  if (!isPixelCount(asset.width) || asset.width < LOGO_MIN_WIDTH) return 2
  return asset.width <= LOGO_MAX_WIDTH ? 0 : 1
}

// The role's size group first, then style preference, then English, then the
// API's own order. Not `score`: it was 0 on all 444 assets observed.
function roleCandidates(list: ArtList, assets: readonly ArtAsset[]): GameAssetCandidate[] {
  return assets
    .filter(asset => list.keepsStyle(asset.style))
    .map((asset, apiOrder) => ({
      asset,
      apiOrder,
      size: list.sizeGroup(asset),
      style: (asset.style === undefined ? undefined : list.styleRank.get(asset.style)) ?? UNRANKED_STYLE,
      language: asset.language === "en" ? 0 : 1,
    }))
    .sort(
      (a, b) =>
        a.size - b.size ||
        a.style - b.style ||
        a.language - b.language ||
        a.apiOrder - b.apiOrder,
    )
    .map(({ asset }) => ({
      role: list.role,
      ...(isPixelCount(asset.width) ? { width: asset.width } : {}),
      ...(isPixelCount(asset.height) ? { height: asset.height } : {}),
      source: { id: String(asset.id), url: asset.url },
    }))
}

// --- responses --------------------------------------------------------------

// A response korrid could not get as 2xx JSON with a `data` list fails the
// operation. korrid then records the game as `transient` and asks again after
// the next rescan (Core ADR 0032, section 2).
function dataList(response: PluginHttpResponse, what: string): unknown[] {
  if (!response.ok) throw new Error(`SteamGridDB ${what} returned HTTP ${response.status}`)
  let body: unknown
  try {
    body = JSON.parse(response.text)
  } catch {
    throw new Error(`SteamGridDB ${what} is not JSON`)
  }
  if (!isRecord(body) || body.success !== true || !Array.isArray(body.data)) {
    throw new Error(`SteamGridDB ${what} has no data list`)
  }
  return body.data
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function isId(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0
}

function isPixelCount(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0
}

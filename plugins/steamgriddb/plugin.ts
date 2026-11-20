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
  GameAssetCandidate,
  GameAssetCandidates,
  GameAssetRole,
  PluginGameAssetCandidatesInput,
  PluginHttpRequest,
  PluginHttpRequests,
  PluginHttpResponse,
} from "../../contracts/generated/korrid"

// The wire enum is type-only: the sandbox cannot import generated Rust code.
// So a role is written as the enum's string value, and the output is
// `PluginGameAssetCandidatesOutput` with that role.
type Role = `${GameAssetRole}`
type Candidate = Omit<GameAssetCandidate, "role"> & { role: Role }
type CandidatesOutput =
  | PluginHttpRequests
  | (Omit<GameAssetCandidates, "candidates"> & { candidates: Candidate[] })
type GameSystem = NonNullable<PluginGameAssetCandidatesInput["system"]>

export const name = "steamgriddb"
export const title = "SteamGridDB"
export const description =
  "Finds a tile, poster, hero and logo for each game on SteamGridDB, with your own API key."

const API_BASE_URL = "https://www.steamgriddb.com/api/v2"
const JSON_HEADERS = { accept: "application/json" } as const

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
  readonly role: Role
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

// This plugin's authority key in a game's public ids (Core ADR 0090): the
// SteamGridDB game id, as text.
const AUTHORITY = "steamgriddb"

function gameAssetCandidates(
  input: PluginGameAssetCandidatesInput,
): CandidatesOutput {
  const responses = Array.isArray(input.responses) ? input.responses : []
  // Id first (Core ADR 0090): a game that holds a SteamGridDB id from an
  // earlier match is fetched by it, with no title search.
  const stored = storedGameId(input.externalIds)
  if (stored !== undefined) return artTurns(stored, responses)

  const gameTitle = typeof input.title === "string" ? input.title : ""
  // A title with no letter or digit can match no name.
  if (matchName(gameTitle) === "") return { candidates: [] }
  if (responses.length === 0) return httpRequests([searchRequest(gameTitle)])

  const [search, ...artLists] = responses
  const match = equalNameMatch(gameTitle, input.system, searchGames(search))
  // No match, unverified and ambiguous all mean "no artwork for this title".
  if (match._tag !== "Accepted") return { candidates: [] }
  return artTurns(match.game.id, artLists)
}

// The art lists of one SteamGridDB game, and its id for korrid to store.
function artTurns(gameId: number, artLists: readonly PluginHttpResponse[]): CandidatesOutput {
  if (artLists.length === 0) {
    return httpRequests(ART_LISTS.map(list => artListRequest(list, gameId)))
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
    externalIds: { [AUTHORITY]: [String(gameId)] },
  }
}

// The first stored SteamGridDB id that is a game id. korrid stores what this
// plugin returned, so another value is not this plugin's.
function storedGameId(ids: unknown): number | undefined {
  if (!isRecord(ids) || !Array.isArray(ids[AUTHORITY])) return undefined
  for (const value of ids[AUTHORITY]) {
    if (typeof value === "string" && /^[0-9]{1,15}$/.test(value)) return Number(value)
  }
  return undefined
}

export const handlers = {
  "game-assets.candidates": gameAssetCandidates,
}

// --- search: one verified game with an equal name ---------------------------

interface SearchGame {
  readonly id: number
  readonly name: string
  readonly verified: boolean
  // The stores SteamGridDB lists the game under, such as `steam` or `gog`.
  readonly types: readonly string[]
}

type MatchDecision =
  | { readonly _tag: "Accepted"; readonly game: SearchGame }
  | { readonly _tag: "NoMatch" }
  | { readonly _tag: "Unverified" }
  | { readonly _tag: "Ambiguous" }

// SteamGridDB's PC store types. A game listed only under these is a PC game.
const PC_STORES: ReadonlySet<string> = new Set(["steam", "egs", "gog", "origin", "uplay", "bnet"])
// Systems whose games are PC games. Every other system is a console, a
// handheld or a fantasy console.
const PC_SYSTEMS: ReadonlySet<string> = new Set(["steam", "dos", "scummvm"])

// Core ADR 0090. The search answers with its ten nearest names even when none
// is the game, so only an equal name counts: no fuzzy match.
// 1. Names equal after `matchName`.
// 2. The store-type guard: for a console, handheld or fantasy console, drop a
//    game listed only under PC stores (match eval, strategy f).
// 3. Only a verified game counts.
// 4. A tie is broken by system: a PC system keeps the games listed under a
//    PC store. korrid passes no release year, so a tie that remains is no
//    match.
function equalNameMatch(
  title: string,
  system: GameSystem | undefined,
  games: readonly SearchGame[],
): MatchDecision {
  const wanted = matchName(title)
  let equal = games.filter(game => matchName(game.name) === wanted)
  if (equal.length === 0) return { _tag: "NoMatch" }
  if (isConsoleLike(system)) equal = equal.filter(game => !onlyPcStores(game))
  const verified = equal.filter(game => game.verified)
  if (verified.length === 0) return equal.length === 0 ? { _tag: "NoMatch" } : { _tag: "Unverified" }
  if (verified.length === 1) return { _tag: "Accepted", game: verified[0] }
  if (isRecord(system) && typeof system.id === "string" && PC_SYSTEMS.has(system.id)) {
    const onPc = verified.filter(game => game.types.some(type => PC_STORES.has(type)))
    if (onPc.length === 1) return { _tag: "Accepted", game: onPc[0] }
  }
  return { _tag: "Ambiguous" }
}

// A system is a console, a handheld or a fantasy console when it declares a
// public id of an authority other than Steam, or when it is not a PC system.
function isConsoleLike(system: GameSystem | undefined): boolean {
  if (!isRecord(system) || typeof system.id !== "string") return false
  const authorities = isRecord(system.externalIds) ? Object.keys(system.externalIds) : []
  return authorities.some(authority => authority !== "steam") || !PC_SYSTEMS.has(system.id)
}

function onlyPcStores(game: SearchGame): boolean {
  return game.types.length > 0 && game.types.every(type => PC_STORES.has(type))
}

const MARK = /\p{M}/gu
const LETTER_OR_DIGIT = /[\p{Alphabetic}\p{N}]/u

// Core ADR 0090's normalization. Fold accents (NFD, then drop the marks) and
// case, drop punctuation, and treat a trailing `version` word as optional:
// "Pokémon: Emerald Version" and "pokemon emerald" are one name. Every
// character that is not a letter or a digit separates words, as main's
// `normalized_match_name` does: "Rock'n'Roll" is "rock n roll".
function matchName(value: string): string {
  const folded = value.normalize("NFD").replace(MARK, "").toLowerCase()
  let spaced = ""
  for (const character of folded) spaced += LETTER_OR_DIGIT.test(character) ? character : " "
  const words = spaced.split(" ").filter(Boolean)
  if (words.length > 1 && words[words.length - 1] === "version") words.pop()
  return words.join(" ")
}

function searchGames(response: PluginHttpResponse): SearchGame[] {
  return dataList(response, "search").map(entry => {
    if (!isRecord(entry) || !isId(entry.id) || typeof entry.name !== "string") {
      throw new Error("SteamGridDB search returned an unexpected game")
    }
    // main: `verified` is false when absent.
    const types = Array.isArray(entry.types)
      ? entry.types.filter((type): type is string => typeof type === "string")
      : []
    return { id: entry.id, name: entry.name, verified: entry.verified === true, types }
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

function artAssets(response: PluginHttpResponse, role: Role): ArtAsset[] {
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
function roleCandidates(list: ArtList, assets: readonly ArtAsset[]): Candidate[] {
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

import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import * as plugin from "./plugin"

// Excerpts of SteamGridDB API v2 responses observed on 2026-11-11 (README,
// "Fixtures"): `author` removed, `notes` blanked, lists cut to the assets
// named in the README, in the API's order. No image and no key is committed.
// `super-metroid-tiles.json` is the live answer to this plugin's own tile
// request, saved on 2026-11-12.
const fixture = (name: string) =>
  readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8")

// The search answered "Super Metroid" and "Super Metroid Redesign" with the
// same ten names, byte for byte.
const superMetroidSearch = fixture("search-super-metroid.json")
const pokemonSearch = fixture("search-pokemon-emerald.json")
const angunaSearch = fixture("search-anguna.json")
const tetrisSearch = fixture("search-tetris.json")
const tetrisLogos = fixture("tetris-logos.json")
const emptySearch = fixture("search-empty.json")
const superMetroidTiles = fixture("super-metroid-tiles.json")
const superMetroidPosters = fixture("super-metroid-posters.json")
const superMetroidLogos = fixture("super-metroid-logos.json")
const pokemonPosters = fixture("pokemon-emerald-posters.json")
const pokemonHeroes = fixture("pokemon-emerald-heroes.json")
const pokemonLogos = fixture("pokemon-emerald-logos.json")
const superMetroidHeroes = fixture("super-metroid-heroes.json")
const angunaPosters = fixture("anguna-posters.json")
const angunaHeroes = fixture("anguna-heroes.json")
const angunaLogos = fixture("anguna-logos.json")

const POKEMON = "Pokémon Emerald Version"

const ok = (text: string, url = "https://www.steamgriddb.com/api/v2/") => ({
  status: 200,
  ok: true,
  url,
  headers: { "content-type": "application/json; charset=utf-8" },
  text,
})
const status = (code: number, text = "") => ({ ...ok(text), status: code, ok: false })

type Candidate = {
  kind: string
  width?: number
  height?: number
  source: { id?: string; url: string }
}
type Request = { url: string; query?: Record<string, unknown>; headers?: Record<string, string> }

// Which of turn 2's lists each asset id of one answer came from. Tile, poster
// and hero are all `picture`, so a test that names a list looks it up here.
type ListName = "tile" | "poster" | "hero" | "logo"
const LIST_NAMES: readonly ListName[] = ["tile", "poster", "hero", "logo"]
const listOf = new WeakMap<object, Map<string, ListName>>()
const call = (title: string, responses: unknown[] = []) => {
  const output = plugin.handlers["game-assets.candidates"]({ title, responses } as never)
  if (responses.length === 5 && typeof output === "object" && output !== null) {
    const names = new Map<string, ListName>()
    responses.slice(1).forEach((response, index) => {
      const body = JSON.parse((response as { text: string }).text) as { data?: { id: unknown }[] }
      for (const asset of body.data ?? []) names.set(String(asset.id), LIST_NAMES[index])
    })
    listOf.set(output, names)
  }
  return output
}
const requestsOf = (output: unknown) => {
  expect(output).toHaveProperty("_tag", "HttpRequests")
  return (output as { requests: Request[] }).requests
}
// A match also names the matched game's SteamGridDB id (Core ADR 0090).
const candidatesOf = (output: unknown) => {
  expect(["candidates", "candidates,externalIds"]).toContain(Object.keys(output as object).join())
  return (output as { candidates: Candidate[] }).candidates
}
const matched = (id: number) => ({ steamgriddb: [String(id)] })
// The ids of one list's candidates, in the answer's order.
const idsOf = (output: unknown, list: ListName) =>
  candidatesOf(output)
    .filter(candidate => listOf.get(output as object)?.get(candidate.source.id ?? "") === list)
    .map(candidate => candidate.source.id)
const kindsOf = (output: unknown) => candidatesOf(output).map(candidate => candidate.kind)

// Turn 2's responses, in request order: tile, poster, hero, logo. No tile
// list was recorded for Pokémon Emerald: the observed empty list (Anguna's
// heroes) stands in for it.
const pokemonArt = (lists: { tile?: string; poster?: string; hero?: string; logo?: string } = {}) => [
  ok(pokemonSearch),
  ok(lists.tile ?? angunaHeroes),
  ok(lists.poster ?? pokemonPosters),
  ok(lists.hero ?? pokemonHeroes),
  ok(lists.logo ?? pokemonLogos),
]

type Asset = Record<string, unknown>
// A list as the API would send it with some assets changed.
const edited = (list: string, edit: (assets: Asset[]) => Asset[]) => {
  const body = JSON.parse(list) as { data: Asset[] }
  return JSON.stringify({ ...body, data: edit(body.data) })
}
const editedAsset = (list: string, id: number, change: Asset) =>
  edited(list, assets => assets.map(asset => (asset.id === id ? { ...asset, ...change } : asset)))
type Game = { id: number; name: string; verified?: boolean }
const editedSearch = (search: string, edit: (games: Game[]) => Game[]) => {
  const body = JSON.parse(search) as { data: Game[] }
  return JSON.stringify({ ...body, data: edit(body.data) })
}

// The live tile list has two tiles of one style and one language. For the
// style and language rules, its first tile is repeated here with other ids,
// styles and languages.
const variedTiles = edited(superMetroidTiles, ([tile]) => [
  { ...tile, id: 1, style: "no_logo" },
  { ...tile, id: 2, style: "material" },
  { ...tile, id: 3, language: "ja" },
  { ...tile, id: 4 },
  { ...tile, id: 5, style: "white_logo" },
  { ...tile, id: 6, style: "blurred" },
])

const artRequest = (endpoint: string, id: number, query: Record<string, string>) => ({
  url: `https://www.steamgriddb.com/api/v2/${endpoint}/game/${id}`,
  query: { ...query, types: "static", nsfw: "false", humor: "false", epilepsy: "false" },
  headers: { accept: "application/json" },
})
const artRequests = (id: number) => ({
  _tag: "HttpRequests",
  requests: [
    artRequest("grids", id, {
      dimensions: "512x512",
      styles: "alternate,blurred,material,no_logo",
    }),
    artRequest("grids", id, { dimensions: "600x900" }),
    artRequest("heroes", id, {}),
    artRequest("logos", id, { mimes: "image/png" }),
  ],
})

describe("SteamGridDB declaration", () => {
  test("declares one artwork handler and no provider", () => {
    expect(plugin.name).toBe("steamgriddb")
    expect(Object.keys(plugin).sort()).toEqual(["description", "handlers", "name", "title"])
    expect(Object.keys(plugin.handlers)).toEqual(["game-assets.candidates"])
  })
})

describe("turn 1: search", () => {
  test("asks the autocomplete search for the title", () => {
    expect(call("Super Metroid")).toStrictEqual({
      _tag: "HttpRequests",
      requests: [
        {
          url: "https://www.steamgriddb.com/api/v2/search/autocomplete/Super%20Metroid",
          headers: { accept: "application/json" },
        },
      ],
    })
  })

  test("keeps the title inside one path segment", () => {
    const [request] = requestsOf(call("  Fate/stay night: Who? #1 100% "))
    expect(request.url).toBe(
      "https://www.steamgriddb.com/api/v2/search/autocomplete/Fate%20stay%20night%3A%20Who%20%20%231%20100%25",
    )
    expect(requestsOf(call(POKEMON))[0].url).toBe(
      "https://www.steamgriddb.com/api/v2/search/autocomplete/Pok%C3%A9mon%20Emerald%20Version",
    )
  })

  test("answers a title with no letter or digit with no candidates and no request", () => {
    for (const title of ["", "   ", "???", "..", "™ - !"]) {
      expect(call(title)).toStrictEqual({ candidates: [] })
    }
  })
})

describe("the exact, verified name match", () => {
  test("accepts the one verified game whose name equals the title", () => {
    expect(call("Super Metroid", [ok(superMetroidSearch)])).toStrictEqual(artRequests(38157))
  })

  test("compares names without case, punctuation or decorations", () => {
    expect(call("  super-METROID™ ", [ok(superMetroidSearch)])).toStrictEqual(artRequests(38157))
    expect(call("Anguna - Warriors of Virtue", [ok(angunaSearch)])).toStrictEqual(
      artRequests(5490981),
    )
    expect(call(POKEMON, [ok(pokemonSearch)])).toStrictEqual(artRequests(34971))
    expect(call("POKÉMON: EMERALD VERSION", [ok(pokemonSearch)])).toStrictEqual(artRequests(34971))
  })

  test("yields no candidates for a near miss: Super Metroid is not Super Metroid Redesign", () => {
    // Observed: the search answers this ROM hack's title with Super Metroid
    // and nine other hacks. None is the game.
    expect(call("Super Metroid Redesign", [ok(superMetroidSearch)])).toStrictEqual({
      candidates: [],
    })
  })

  test("folds accents and treats a trailing Version as optional (Core ADR 0090)", () => {
    // Observed: "Pokemon Emerald" answers ten "Pokémon Emerald …" names.
    expect(call("Pokemon Emerald Version", [ok(pokemonSearch)])).toStrictEqual(artRequests(34971))
    expect(call("Pokemon Emerald", [ok(pokemonSearch)])).toStrictEqual(artRequests(34971))
    expect(call("pokémon - emerald", [ok(pokemonSearch)])).toStrictEqual(artRequests(34971))
    // An accented letter folds to its letter, never to a word break.
    expect(call("Pok mon Emerald Version", [ok(pokemonSearch)])).toStrictEqual({ candidates: [] })
    // Only a trailing Version is optional, and never the whole name.
    expect(call("Pokemon Version Emerald", [ok(pokemonSearch)])).toStrictEqual({ candidates: [] })
  })

  test("breaks words at an apostrophe, as main's normalized_match_name does", () => {
    // Observed in the eval: "Mega Man Rock N Roll" is "Mega Man: Rock'n'Roll".
    const rock = editedSearch(emptySearch, () => [
      { id: 9, name: "Mega Man: Rock'n'Roll", verified: true },
    ])
    expect(call("Mega Man Rock N Roll", [ok(rock)])).toStrictEqual(artRequests(9))
    const yoshi = editedSearch(emptySearch, () => [{ id: 8, name: "Yoshi’s Island", verified: true }])
    expect(call("Yoshi's Island", [ok(yoshi)])).toStrictEqual(artRequests(8))
    expect(call("Yoshis Island", [ok(yoshi)])).toStrictEqual({ candidates: [] })
  })

  test("yields no candidates when the search finds nothing", () => {
    expect(call("µCity", [ok(emptySearch)])).toStrictEqual({ candidates: [] })
  })

  test("yields no candidates for an unverified game", () => {
    const unverified = editedSearch(superMetroidSearch, games =>
      games.map(game => (game.id === 38157 ? { ...game, verified: false } : game)),
    )
    expect(call("Super Metroid", [ok(unverified)])).toStrictEqual({ candidates: [] })
    const unmarked = editedSearch(superMetroidSearch, games =>
      games.map(({ verified, ...game }) => (game.id === 38157 ? game : { ...game, verified })),
    )
    expect(call("Super Metroid", [ok(unmarked)])).toStrictEqual({ candidates: [] })
  })

  test("yields no candidates when two verified games share the name", () => {
    const ambiguous = editedSearch(superMetroidSearch, games => [
      ...games,
      { id: 999001, name: "Super-Metroid", verified: true },
    ])
    expect(call("Super Metroid", [ok(ambiguous)])).toStrictEqual({ candidates: [] })
  })

  test("accepts the verified game when an unverified one shares the name", () => {
    const shared = editedSearch(superMetroidSearch, games => [
      { id: 999001, name: "SUPER METROID", verified: false },
      ...games,
    ])
    expect(call("Super Metroid", [ok(shared)])).toStrictEqual(artRequests(38157))
  })
})

describe("turn 2: the four art lists", () => {
  test("asks for tile, poster, hero and logo in one turn", () => {
    const requests = requestsOf(call(POKEMON, [ok(pokemonSearch)]))
    expect(requests).toStrictEqual(artRequests(34971).requests)
    // ADR 0016 bounds: 8 requests a turn. Search, lists, result: 3 calls of 4.
    expect(requests.length).toBeLessThanOrEqual(8)
  })

  test("filters nsfw, humor and epilepsy out in every art request", () => {
    const requests = requestsOf(call(POKEMON, [ok(pokemonSearch)]))
    expect(requests).toHaveLength(4)
    for (const request of requests) {
      expect(request.query).toMatchObject({ nsfw: "false", humor: "false", epilepsy: "false" })
    }
  })

  test("asks for the tile list as the request of the live fixture did, with epilepsy=false added", () => {
    // The URL korrid sent for `super-metroid-tiles.json`. korrid sorts the
    // query keys, so the parameters are compared, not the text.
    const live = new URL(
      "https://www.steamgriddb.com/api/v2/grids/game/38157?dimensions=512x512&humor=false&nsfw=false&styles=alternate%2Cblurred%2Cmaterial%2Cno_logo&types=static",
    )
    const [tileRequest] = requestsOf(call("Super Metroid", [ok(superMetroidSearch)]))
    expect(tileRequest.url).toBe(live.origin + live.pathname)
    expect(tileRequest.query).toEqual({
      ...Object.fromEntries(live.searchParams),
      epilepsy: "false",
    })
  })

  test("never sets a header that korrid refuses", () => {
    const refused = ["authorization", "proxy-authorization", "cookie", "set-cookie", "host"]
    const requests = [...requestsOf(call(POKEMON)), ...requestsOf(call(POKEMON, [ok(pokemonSearch)]))]
    expect(requests).toHaveLength(5)
    for (const request of requests) {
      const names = Object.keys(request.headers ?? {}).map(name => name.toLowerCase())
      expect(names.filter(name => refused.includes(name))).toEqual([])
      expect(request.url.startsWith("https://www.steamgriddb.com/api/v2/")).toBe(true)
      expect(JSON.stringify(request)).not.toMatch(/bearer|token|key/i)
    }
  })
})

describe("candidates", () => {
  test("lists every list as a kind with the asset's id, size and url: Super Metroid", () => {
    const source = (id: string, path: string) => ({
      id,
      url: `https://cdn2.steamgriddb.com/${path}`,
    })
    expect(
      call("Super Metroid", [
        ok(superMetroidSearch),
        ok(superMetroidTiles),
        ok(superMetroidPosters),
        ok(superMetroidHeroes),
        ok(superMetroidLogos),
      ]),
    ).toStrictEqual({
      candidates: [
        // Pictures take turns: hero, poster, tile. Within its list, a hero
        // no wider than 1920 px comes first; a poster's alternate before
        // white_logo and no_logo; tiles keep the live list's API order.
        superMetroidHero("59734", 1920, 620),
        { kind: "picture", width: 600, height: 900, source: source("37974", "grid/167248f62dbaf61aff4b7d1be9439282.jpg") },
        { kind: "picture", width: 512, height: 512, source: source("800051", "grid/2581b4f20b66604537f96b64e27429e5.png") },
        superMetroidHero("158930", 1600, 650),
        { kind: "picture", width: 600, height: 900, source: source("179187", "grid/0228b076e81154aa189310ca02eeb89a.png") },
        { kind: "picture", width: 512, height: 512, source: source("727609", "grid/a2f3322f801d9fa81b0fd34a02d1e202.png") },
        superMetroidHero("181998", 1920, 620),
        { kind: "picture", width: 600, height: 900, source: source("346133", "grid/c0d28afd12cbaf1d2483cf470f3e8567.png") },
        superMetroidHero("77659", 3840, 1240),
        { kind: "picture", width: 600, height: 900, source: source("521614", "grid/d0c8e3a859c7a99aa64fc5b3164f6300.png") },
        superMetroidHero("17374", 3840, 1240),
        // logo: 480 to 1024 px wide first (official, custom), then wider
        // (official, white).
        { kind: "logo", width: 785, height: 338, source: source("42959", "logo/60eefdd92947076e89f98d7f4ddec6c9.png") },
        { kind: "logo", width: 638, height: 344, source: source("161228", "logo/46cfe0a5e65d476f9e426b6d09dec97d.png") },
        { kind: "logo", width: 1526, height: 651, source: source("11253", "logo/ddfa8a1fa86914072eb6e3e55c253856.png") },
        { kind: "logo", width: 1842, height: 744, source: source("81263", "logo/7a3bd1a79a7b85595b21c34410147dd4.png") },
      ],
      externalIds: matched(38157),
    })
  })

  test("lists poster, hero and logo in order of preference: Pokémon Emerald", () => {
    expect(call(POKEMON, pokemonArt())).toStrictEqual({
      candidates: [
        // Pictures take turns: hero, poster (no tile list was recorded).
        // Heroes: no wider than 1920 px first (alternate, then material),
        // then the wider one. Posters: alternate in English, alternate in
        // other languages, material, then white_logo and no_logo.
        hero("2748", 1920, 620),
        {
          kind: "picture",
          width: 600,
          height: 900,
          source: {
            id: "169090",
            url: "https://cdn2.steamgriddb.com/grid/052938e7b425df3acdd9dc4be44404ef.png",
          },
        },
        hero("15907", 1920, 620),
        poster("370856"),
        hero("142599", 1920, 620),
        poster("772444"),
        hero("145705", 3840, 1240),
        poster("772442"),
        poster("772440"),
        poster("341136"),
        poster("274559"),
        poster("858678"),
        // logo: 480 to 1024 px wide first (official with English first, then
        // white), then the wider ones in the same order, then the narrow one.
        logo("122408", 830, 355),
        logo("151629", 1000, 616),
        logo("185519", 654, 343),
        logo("6894", 3611, 1877),
        logo("163959", 1596, 886),
        logo("123823", 7682, 1922),
        logo("146694", 1088, 735),
        logo("163962", 1596, 958),
        logo("80111", 231, 84),
      ],
      externalIds: matched(34971),
    })
  })

  test("orders by size group, then style, then English, then the API's order", () => {
    const output = call(POKEMON, pokemonArt({ tile: variedTiles }))
    // main keeps alternate, blurred and material tiles only: `no_logo` (1)
    // and `white_logo` (5) are dropped.
    expect(idsOf(output, "tile")).toEqual([
      "4", // alternate en
      "3", // alternate ja
      "2", // material en
      "6", // blurred en
    ])
    expect(idsOf(output, "poster")).toEqual([
      "169090", // alternate en
      "370856", // alternate en
      "772444", // alternate ja
      "772442", // alternate it
      "772440", // alternate fr
      "341136", // material en
      "274559", // white_logo en
      "858678", // no_logo en
    ])
    expect(idsOf(output, "hero")).toEqual([
      "2748", // alternate 1920x620
      "15907", // alternate 1920x620
      "142599", // material 1920x620
      "145705", // alternate 3840x1240
    ])
    expect(idsOf(output, "logo")).toEqual([
      "122408", // 480 to 1024 px: official en 830x355
      "151629", // official es 1000x616
      "185519", // white en 654x343
      "6894", // wider: official en 3611x1877
      "163959", // official en 1596x886
      "123823", // official ja 7682x1922
      "146694", // custom en 1088x735
      "163962", // custom it 1596x958
      "80111", // narrower: official zh 231x84
    ])
  })

  test("puts a hero's material before blurred, a logo's black last, and an unknown style after the known", () => {
    const heroes = edited(pokemonHeroes, assets => [
      { ...assets[0], id: 1, style: "sketch" },
      { ...assets[0], id: 2, style: "blurred" },
      { ...assets[0], id: 3, style: "material" },
      { ...assets[0], id: 4, style: "alternate" },
      { ...assets[0], id: 5, style: "constructor" },
    ])
    expect(idsOf(call(POKEMON, pokemonArt({ hero: heroes })), "hero")).toEqual([
      "4",
      "3",
      "2",
      "1",
      "5",
    ])
    const logos = edited(pokemonLogos, assets => [
      { ...assets[0], id: 1, style: "black" },
      { ...assets[0], id: 2, style: "custom" },
      { ...assets[0], id: 3, style: "white" },
      { ...assets[0], id: 4, style: "official" },
    ])
    expect(idsOf(call(POKEMON, pokemonArt({ logo: logos })), "logo")).toEqual(["4", "3", "2", "1"])
  })

  test("puts a 1920x620 hero before a 3840x1240 one: Super Metroid", () => {
    // Observed: positions 11, 12, 15, 18 and 26 of Super Metroid's 27 heroes.
    // The API lists a 3840x1240 hero first here. It is 19 MB once decoded, and
    // korrid takes the first candidate. The other three lists do not matter:
    // the observed empty list stands in for them.
    const output = call("Super Metroid", [
      ok(superMetroidSearch),
      ok(angunaHeroes),
      ok(angunaHeroes),
      ok(superMetroidHeroes),
      ok(angunaHeroes),
    ])
    expect(candidatesOf(output)).toStrictEqual([
      superMetroidHero("59734", 1920, 620), // alternate
      superMetroidHero("158930", 1600, 650), // alternate
      superMetroidHero("181998", 1920, 620), // blurred
      superMetroidHero("77659", 3840, 1240), // alternate, first in the API's order
      superMetroidHero("17374", 3840, 1240), // alternate
    ])
    expect(candidatesOf(output)[0]).toStrictEqual({
      kind: "picture",
      width: 1920,
      height: 620,
      source: {
        id: "59734",
        url: "https://cdn2.steamgriddb.com/hero/7b1c718f91de50d902e00762ad5cac28.jpg",
      },
    })
  })

  test("still lists the wider heroes when a game has no other", () => {
    const wide = edited(superMetroidHeroes, assets => assets.filter(asset => asset.width === 3840))
    expect(idsOf(call(POKEMON, pokemonArt({ hero: wide })), "hero")).toEqual(["77659", "17374"])
  })

  test("puts a hero of unknown width after one known to be no wider than 1920 px", () => {
    const heroes = edited(superMetroidHeroes, assets => [
      { ...assets[1], id: 1, width: null },
      { ...assets[1], id: 2, width: 1921 },
      { ...assets[1], id: 3, width: 1920 },
    ])
    expect(idsOf(call(POKEMON, pokemonArt({ hero: heroes })), "hero")).toEqual(["3", "1", "2"])
  })

  test("picks a logo 480 to 1024 px wide over a 3611x1877 one: Pokémon Emerald", () => {
    // Observed: the API lists the 3611x1877 logo first.
    const logos = candidatesOf(call(POKEMON, pokemonArt())).filter(
      candidate => candidate.kind === "logo",
    )
    expect((JSON.parse(pokemonLogos) as { data: Asset[] }).data[0]).toMatchObject({
      id: 6894,
      width: 3611,
      height: 1877,
    })
    expect(logos[0]).toStrictEqual({
      kind: "logo",
      width: 830,
      height: 355,
      source: {
        id: "122408",
        url: "https://cdn2.steamgriddb.com/logo/5fc6bba3b49d8765a27712ef46444a54.png",
      },
    })
    // Three groups, in this order: 480 to 1024 px, wider, narrower.
    const group = (width = 0) => (width < 480 ? 2 : width <= 1024 ? 0 : 1)
    expect(logos.map(candidate => group(candidate.width))).toEqual([0, 0, 0, 1, 1, 1, 1, 1, 2])
  })

  test("picks a wide logo over a narrow one: Tetris (Game Boy)", () => {
    // Observed: Tetris has no logo from 480 to 1024 px wide. The 463x144 one
    // would be drawn scaled up and soft, so both wider ones come before it.
    // The other three lists do not matter: the observed empty list stands in.
    const output = call("Tetris (Game Boy)", [
      ok(tetrisSearch),
      ok(angunaHeroes),
      ok(angunaHeroes),
      ok(angunaHeroes),
      ok(tetrisLogos),
    ])
    expect(candidatesOf(output)).toStrictEqual([
      {
        kind: "logo",
        width: 2364,
        height: 704,
        source: {
          id: "24679",
          url: "https://cdn2.steamgriddb.com/logo/07b4498a303789d2829445c725dae35a.png",
        },
      },
      {
        kind: "logo",
        width: 1155,
        height: 361,
        source: {
          id: "3826",
          url: "https://cdn2.steamgriddb.com/logo/a292f1c5874b2be8395ffd75f313937f.png",
        },
      },
      {
        kind: "logo",
        width: 463,
        height: 144,
        source: {
          id: "14389",
          url: "https://cdn2.steamgriddb.com/logo/5dae854cd11d11715c91b6ce80f46b7c.png",
        },
      },
    ])
  })

  test("still lists the wider logos when a game has no other: Anguna", () => {
    // Observed: Anguna's two logos are 1936 px and 3067 px wide.
    const output = call("Anguna: Warriors of Virtue", [
      ok(angunaSearch),
      ok(angunaHeroes),
      ok(angunaHeroes),
      ok(angunaHeroes),
      ok(angunaLogos),
    ])
    expect(candidatesOf(output).map(({ kind, width, source }) => [kind, width, source.id])).toEqual([
      ["logo", 1936, "151230"],
      ["logo", 3067, "151225"],
    ])
  })

  test("still lists the narrow logos when a game has no other", () => {
    // No observed game has only narrow logos: Tetris's three, made narrow.
    const narrow = edited(tetrisLogos, assets => [
      { ...assets[0], width: 400, height: 119, language: "ja" },
      { ...assets[1], style: "custom" },
      { ...assets[2], width: 240, height: 75 },
    ])
    expect(idsOf(call(POKEMON, pokemonArt({ logo: narrow })), "logo")).toEqual([
      "3826", // official en
      "24679", // official ja
      "14389", // custom en
    ])
  })

  test("groups a logo by its width: 480 to 1024 px, then wider, then narrower or unknown", () => {
    const logos = edited(pokemonLogos, assets => [
      { ...assets[0], id: 1, width: null },
      { ...assets[0], id: 2, width: 479 },
      { ...assets[0], id: 3, width: 1025 },
      { ...assets[0], id: 4, width: 1024 },
      { ...assets[0], id: 5, width: 480 },
    ])
    expect(idsOf(call(POKEMON, pokemonArt({ logo: logos })), "logo")).toEqual([
      "4",
      "5",
      "3",
      "1",
      "2",
    ])
  })

  test("puts a 600x900 poster before a larger one, whatever its style", () => {
    const posters = edited(pokemonPosters, assets => [
      { ...assets[0], id: 1, width: 1200, height: 1800 },
      { ...assets[0], id: 2, width: 600, height: 1800 },
      ...assets,
    ])
    const expected = [...idsOf(call(POKEMON, pokemonArt()), "poster"), "1", "2"]
    expect(idsOf(call(POKEMON, pokemonArt({ poster: posters })), "poster")).toEqual(expected)
    expect(expected.at(-3)).toBe("858678") // a 600x900 no_logo poster is still before them
  })

  test("does not order by score", () => {
    const scored = edited(pokemonPosters, assets =>
      assets.map((asset, index) => ({ ...asset, score: index * 10, upvotes: index })),
    )
    expect(idsOf(call(POKEMON, pokemonArt({ poster: scored })), "poster")).toEqual(
      idsOf(call(POKEMON, pokemonArt()), "poster"),
    )
  })

  test("keeps a tile with no style, as main does, after the styled ones", () => {
    const unstyled = edited(variedTiles, assets => {
      const { style, ...first } = assets[0]
      return [first, ...assets.slice(1)]
    })
    expect(idsOf(call(POKEMON, pokemonArt({ tile: unstyled })), "tile")).toEqual([
      "4",
      "3",
      "2",
      "6",
      "1",
    ])
  })

  test("drops an asset flagged nsfw, humor or epilepsy, in every list", () => {
    const first = { tile: 800051, poster: 169090, hero: 2748, logo: 122408 }
    const lists = {
      tile: superMetroidTiles,
      poster: pokemonPosters,
      hero: pokemonHeroes,
      logo: pokemonLogos,
    }
    const all = call(POKEMON, pokemonArt(lists))
    expect(idsOf(all, "tile")).toEqual(["800051", "727609"])
    for (const role of ["tile", "poster", "hero", "logo"] as const) {
      for (const flag of ["nsfw", "humor", "epilepsy"]) {
        const flagged = editedAsset(lists[role], first[role], { [flag]: true })
        const output = call(POKEMON, pokemonArt({ ...lists, [role]: flagged }))
        expect(idsOf(output, role)).toEqual(idsOf(all, role).slice(1))
      }
    }
  })

  test("drops an asset whose flag is not a plain false, and one tagged as main's tags", () => {
    const expected = idsOf(call(POKEMON, pokemonArt()), "poster").slice(1)
    for (const change of [
      { nsfw: "false" },
      { humor: 1 },
      { epilepsy: null },
      { tags: ["NSFW"] },
      { tags: ["art", "Humor"] },
      { tags: ["epilepsy"] },
    ]) {
      const poster = editedAsset(pokemonPosters, 169090, change)
      expect(idsOf(call(POKEMON, pokemonArt({ poster })), "poster")).toEqual(expected)
    }
    const harmless = editedAsset(pokemonPosters, 169090, { tags: ["box art"] })
    expect(idsOf(call(POKEMON, pokemonArt({ poster: harmless })), "poster")).toHaveLength(8)
  })

  test("answers no candidates when every asset is flagged", () => {
    const flagged = (list: string) => edited(list, assets => assets.map(asset => ({ ...asset, nsfw: true })))
    expect(
      call(
        POKEMON,
        pokemonArt({
          tile: flagged(superMetroidTiles),
          poster: flagged(pokemonPosters),
          hero: flagged(pokemonHeroes),
          logo: flagged(pokemonLogos),
        }),
      ),
    ).toStrictEqual({ candidates: [], externalIds: matched(34971) })
  })

  test("lists a game with no hero without one: Anguna", () => {
    // Observed: Anguna has two posters, two logos and an empty hero list.
    // No 512x512 list was recorded; the observed empty list stands in for it.
    const output = call("Anguna: Warriors of Virtue", [
      ok(angunaSearch),
      ok(angunaHeroes),
      ok(angunaPosters),
      ok(angunaHeroes),
      ok(angunaLogos),
    ])
    expect(output).toStrictEqual({
      candidates: [
        {
          kind: "picture",
          width: 600,
          height: 900,
          source: {
            id: "582961",
            url: "https://cdn2.steamgriddb.com/grid/2fedaac8ebf4bb793a8e06b2ff9bf9ac.png",
          },
        },
        {
          kind: "picture",
          width: 600,
          height: 900,
          source: {
            id: "692516",
            url: "https://cdn2.steamgriddb.com/grid/b275be65d4e421e3568be1ef6a8e2455.png",
          },
        },
        {
          kind: "logo",
          width: 1936,
          height: 1243,
          source: {
            id: "151230",
            url: "https://cdn2.steamgriddb.com/logo/9e4002b5735e8ada36a039c0741aafd4.png",
          },
        },
        {
          kind: "logo",
          width: 3067,
          height: 1893,
          source: {
            id: "151225",
            url: "https://cdn2.steamgriddb.com/logo/9d3a60e4e2ea458b1a1b3ab3ced35125.png",
          },
        },
      ],
      externalIds: matched(5490981),
    })
    expect(idsOf(output, "hero")).toEqual([])
  })

  test("leaves out a width or height that is not a positive whole number", () => {
    const logo = edited(pokemonLogos, assets => [
      { ...assets[0], id: 1, width: 0, height: 0 },
      { ...assets[0], id: 2, width: "512", height: 12.5 },
      { ...assets[0], id: 3, width: 640, height: null },
    ])
    const url = (JSON.parse(pokemonLogos) as { data: Asset[] }).data[0].url
    expect(
      candidatesOf(call(POKEMON, pokemonArt({ logo }))).filter(candidate => candidate.kind === "logo"),
    ).toStrictEqual([
      // The one logo known to be 480 to 1024 px wide comes first.
      { kind: "logo", width: 640, source: { id: "3", url } },
      { kind: "logo", source: { id: "1", url } },
      { kind: "logo", source: { id: "2", url } },
    ] as Candidate[])
  })

  test("names only the image host that plugin.nix declares", () => {
    for (const candidate of candidatesOf(call(POKEMON, pokemonArt()))) {
      expect(candidate.source.url.startsWith("https://cdn2.steamgriddb.com/")).toBe(true)
    }
  })
})

describe("kinds (Core ADR 0091)", () => {
  test("grids and heroes are pictures, logos are logos, and no icon is sent", () => {
    const output = call(POKEMON, pokemonArt({ tile: superMetroidTiles }))
    const kinds = kindsOf(output)
    expect(new Set(kinds)).toEqual(new Set(["picture", "logo"]))
    for (const list of ["tile", "poster", "hero"] as const) {
      for (const id of idsOf(output, list)) {
        expect(candidatesOf(output).find(candidate => candidate.source.id === id)?.kind).toBe("picture")
      }
    }
    // Pictures first, then logos; no candidate has a role.
    expect(kinds.indexOf("logo")).toBe(kinds.lastIndexOf("picture") + 1)
    for (const candidate of candidatesOf(output)) expect(candidate).not.toHaveProperty("role")
  })

  test("the first four pictures hold the best hero, poster and tile", () => {
    const output = call(POKEMON, pokemonArt({ tile: superMetroidTiles }))
    const firstFour = candidatesOf(output)
      .filter(candidate => candidate.kind === "picture")
      .slice(0, 4)
      .map(candidate => candidate.source.id)
    expect(firstFour).toEqual([
      idsOf(output, "hero")[0],
      idsOf(output, "poster")[0],
      idsOf(output, "tile")[0],
      idsOf(output, "hero")[1],
    ])
  })
})

describe("a failed response", () => {
  test("fails the operation when the search is refused or broken", () => {
    const unauthorized = '{"success":false,"errors":["Authentication Required"]}'
    expect(() => call("Super Metroid", [status(401, unauthorized)])).toThrow("search returned HTTP 401")
    expect(() => call("Super Metroid", [status(429)])).toThrow("search returned HTTP 429")
    expect(() => call("Super Metroid", [status(503)])).toThrow("search returned HTTP 503")
    expect(() => call("Super Metroid", [ok("<html>")])).toThrow("search is not JSON")
    expect(() => call("Super Metroid", [ok('{"success":false,"data":[]}')])).toThrow(
      "search has no data list",
    )
    expect(() => call("Super Metroid", [ok('{"success":true}')])).toThrow("search has no data list")
    expect(() => call("Super Metroid", [ok('{"success":true,"data":[{"name":"Super Metroid"}]}')])).toThrow(
      "unexpected game",
    )
  })

  test("fails the whole operation when one art list fails, so korrid asks again later", () => {
    const notFound = '{"success":false,"status":404,"errors":["Game not found"]}'
    const responses = pokemonArt()
    for (const [index, role] of ["tile", "poster", "hero", "logo"].entries()) {
      const failed = [...responses]
      failed[index + 1] = status(404, notFound)
      expect(() => call(POKEMON, failed)).toThrow(`${role} list returned HTTP 404`)
      failed[index + 1] = status(500)
      expect(() => call(POKEMON, failed)).toThrow(`${role} list returned HTTP 500`)
      failed[index + 1] = ok("")
      expect(() => call(POKEMON, failed)).toThrow(`${role} list is not JSON`)
    }
  })

  test("fails on an asset without an id or a url, and on a missing list", () => {
    const { url, ...withoutUrl } = (JSON.parse(pokemonHeroes) as { data: Asset[] }).data[0]
    const hero = edited(pokemonHeroes, assets => [withoutUrl, ...assets])
    expect(() => call(POKEMON, pokemonArt({ hero }))).toThrow("hero list returned an unexpected asset")
    expect(() => call(POKEMON, pokemonArt().slice(0, 4))).toThrow("expected 4 responses, got 3")
  })
})

// The fixture's own `url` for an asset: the plugin passes it through as it is.
function assetUrl(list: string, id: string): string {
  const asset = (JSON.parse(list) as { data: Asset[] }).data.find(entry => String(entry.id) === id)
  if (typeof asset?.url !== "string") throw new Error(`fixture has no asset ${id}`)
  return asset.url
}

function poster(id: string): Candidate {
  return { kind: "picture", width: 600, height: 900, source: { id, url: assetUrl(pokemonPosters, id) } }
}

function hero(id: string, width: number, height: number): Candidate {
  return { kind: "picture", width, height, source: { id, url: assetUrl(pokemonHeroes, id) } }
}

function superMetroidHero(id: string, width: number, height: number): Candidate {
  return { kind: "picture", width, height, source: { id, url: assetUrl(superMetroidHeroes, id) } }
}

function logo(id: string, width: number, height: number): Candidate {
  return { kind: "logo", width, height, source: { id, url: assetUrl(pokemonLogos, id) } }
}

// Core ADR 0090 and the match eval of 2026-11-20 (strategy f).
const SNES = {
  id: "snes",
  title: "Super Nintendo",
  externalIds: { wikidata: ["Q183259"], igdb: ["19", "58"] },
}
const STEAM = { id: "steam", title: "Steam", externalIds: {} }
const callWith = (title: string, input: Record<string, unknown>, responses: unknown[] = []) =>
  plugin.handlers["game-assets.candidates"]({ title, responses, externalIds: {}, ...input } as never)
type StoreGame = { id: number; name: string; verified: boolean; types: string[] }
const searchOf = (games: StoreGame[]) => editedSearch(emptySearch, () => games as never)

describe("id first", () => {
  test("a stored SteamGridDB id skips the search and asks for its art lists", () => {
    const stored = { externalIds: { steamgriddb: ["38157"], igdb: ["1"] } }
    expect(callWith("Anything at all", stored)).toStrictEqual(artRequests(38157))
    // Even a title that could match nothing is looked up by its id.
    expect(callWith("???", stored)).toStrictEqual(artRequests(38157))
    const output = callWith("Super Metroid", stored, [
      ok(superMetroidTiles),
      ok(superMetroidPosters),
      ok(superMetroidHeroes),
      ok(superMetroidLogos),
    ])
    expect(candidatesOf(output).length).toBe(15)
    expect((output as { externalIds: unknown }).externalIds).toStrictEqual(matched(38157))
  })

  test("a value that is not a game id is not used, and the search runs", () => {
    for (const steamgriddb of [[], [""], ["abc"], ["-1"], [7]]) {
      const [request] = requestsOf(callWith("Super Metroid", { externalIds: { steamgriddb } }))
      expect(request.url).toContain("/search/autocomplete/")
    }
  })

  test("a new match returns its id for korrid to store", () => {
    const output = callWith("Super Metroid", { system: SNES }, [
      ok(superMetroidSearch),
      ok(superMetroidTiles),
      ok(superMetroidPosters),
      ok(superMetroidHeroes),
      ok(superMetroidLogos),
    ])
    expect((output as { externalIds: unknown }).externalIds).toStrictEqual(matched(38157))
  })
})

describe("the store-type guard and the tie-break", () => {
  const celeste = searchOf([
    { id: 13136, name: "Celeste", verified: true, types: ["steam", "egs"] },
    { id: 5253956, name: "Celeste", verified: true, types: [] },
  ])

  test("a console system drops a game listed only under PC stores", () => {
    // Observed in the eval: PICO-8 Celeste matched the Steam game.
    const pico8 = { id: "pico8", externalIds: { wikidata: ["Q28456260"] } }
    expect(callWith("Celeste", { system: pico8 }, [ok(celeste)])).toStrictEqual(artRequests(5253956))
    const onlyPc = searchOf([{ id: 13136, name: "Celeste", verified: true, types: ["steam"] }])
    expect(callWith("Celeste", { system: pico8 }, [ok(onlyPc)])).toStrictEqual({ candidates: [] })
    // A system with no declared ids is still a console unless it is a PC system.
    const eggshell = { id: "eggshell", externalIds: {} }
    expect(callWith("Celeste", { system: eggshell }, [ok(onlyPc)])).toStrictEqual({ candidates: [] })
  })

  test("a game listed under a console store or no store passes the guard", () => {
    // Observed: Super Metroid is listed under eshop.
    expect(callWith("Super Metroid", { system: SNES }, [ok(superMetroidSearch)])).toStrictEqual(
      artRequests(38157),
    )
  })

  test("a PC system and a game with no system are not guarded", () => {
    const onlyPc = searchOf([{ id: 13136, name: "Celeste", verified: true, types: ["steam"] }])
    expect(callWith("Celeste", { system: STEAM }, [ok(onlyPc)])).toStrictEqual(artRequests(13136))
    expect(callWith("Celeste", {}, [ok(onlyPc)])).toStrictEqual(artRequests(13136))
  })

  test("a tie is broken by system, and a tie that remains is no match", () => {
    // A PC system keeps the one game listed under a PC store.
    expect(callWith("Celeste", { system: STEAM }, [ok(celeste)])).toStrictEqual(artRequests(13136))
    // With no system nothing separates them; korrid passes no release year.
    expect(callWith("Celeste", {}, [ok(celeste)])).toStrictEqual({ candidates: [] })
    const twoConsole = searchOf([
      { id: 1, name: "Ocarina of Time", verified: true, types: [] },
      { id: 2, name: "Ocarina of Time", verified: true, types: [] },
    ])
    expect(callWith("Ocarina of Time", { system: SNES }, [ok(twoConsole)])).toStrictEqual({
      candidates: [],
    })
  })
})

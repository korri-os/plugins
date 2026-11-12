import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import * as plugin from "./plugin"

// Excerpts of SteamGridDB API v2 responses observed on 2026-11-11 (README,
// "Fixtures"): `author` removed, `notes` blanked, lists cut to the assets
// named in the README, in the API's order. No image and no key is committed.
// `constructed-tiles.json` is not an observed response: no
// `dimensions=512x512` list was recorded, so it is written by hand in the
// observed asset shape, and its ids and URLs name nothing real.
const fixture = (name: string) =>
  readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8")

// The search answered "Super Metroid" and "Super Metroid Redesign" with the
// same ten names, byte for byte.
const superMetroidSearch = fixture("search-super-metroid.json")
const pokemonSearch = fixture("search-pokemon-emerald.json")
const angunaSearch = fixture("search-anguna.json")
const emptySearch = fixture("search-empty.json")
const tiles = fixture("constructed-tiles.json")
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
  role: string
  width?: number
  height?: number
  source: { id?: string; url: string }
}
type Request = { url: string; query?: Record<string, unknown>; headers?: Record<string, string> }

const call = (title: string, responses: unknown[] = []) =>
  plugin.handlers["game-assets.candidates"]({ title, responses } as never)
const requestsOf = (output: unknown) => {
  expect(output).toHaveProperty("_tag", "HttpRequests")
  return (output as { requests: Request[] }).requests
}
const candidatesOf = (output: unknown) => {
  expect(Object.keys(output as object)).toEqual(["candidates"])
  return (output as { candidates: Candidate[] }).candidates
}
const idsOf = (output: unknown, role: string) =>
  candidatesOf(output)
    .filter(candidate => candidate.role === role)
    .map(candidate => candidate.source.id)

// Turn 2's responses, in request order: tile, poster, hero, logo.
const pokemonArt = (lists: { tile?: string; poster?: string; hero?: string; logo?: string } = {}) => [
  ok(pokemonSearch),
  ok(lists.tile ?? tiles),
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

const artRequest = (endpoint: string, id: number, query: Record<string, string>) => ({
  url: `https://www.steamgriddb.com/api/v2/${endpoint}/game/${id}`,
  query: { ...query, types: "static", nsfw: "false", humor: "false" },
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

  test("yields no candidates when only an accent differs", () => {
    // Observed: "Pokemon Emerald" answers ten "Pokémon Emerald …" names.
    expect(call("Pokemon Emerald Version", [ok(pokemonSearch)])).toStrictEqual({ candidates: [] })
    expect(call("Pokemon Emerald", [ok(pokemonSearch)])).toStrictEqual({ candidates: [] })
    // An accented letter is a letter, not a word break.
    expect(call("Pok mon Emerald Version", [ok(pokemonSearch)])).toStrictEqual({ candidates: [] })
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
  test("lists every role in order of preference, with the asset's id, size and url", () => {
    expect(call(POKEMON, pokemonArt())).toStrictEqual({
      candidates: [
        // tile (constructed list): main keeps alternate, blurred and
        // material only; `no_logo` (1) and `white_logo` (5) are dropped.
        tile(4),
        tile(3),
        tile(2),
        tile(6),
        // poster: alternate in English, alternate in other languages,
        // material, then white_logo and no_logo in the API's order.
        {
          role: "poster",
          width: 600,
          height: 900,
          source: {
            id: "169090",
            url: "https://cdn2.steamgriddb.com/grid/052938e7b425df3acdd9dc4be44404ef.png",
          },
        },
        poster("370856"),
        poster("772444"),
        poster("772442"),
        poster("772440"),
        poster("341136"),
        poster("274559"),
        poster("858678"),
        // hero: no wider than 1920 px first (alternate, then material), then
        // the wider one.
        hero("2748", 1920, 620),
        hero("15907", 1920, 620),
        hero("142599", 1920, 620),
        hero("145705", 3840, 1240),
        // logo: no wider than 1024 px first (official with English first,
        // then white), then the wider ones in the same order.
        logo("122408", 830, 355),
        logo("151629", 1000, 616),
        logo("80111", 231, 84),
        logo("185519", 654, 343),
        logo("6894", 3611, 1877),
        logo("163959", 1596, 886),
        logo("123823", 7682, 1922),
        logo("146694", 1088, 735),
        logo("163962", 1596, 958),
      ],
    })
  })

  test("orders by preferred size, then style, then English, then the API's order", () => {
    const output = call(POKEMON, pokemonArt())
    expect(idsOf(output, "tile")).toEqual(["4", "3", "2", "6"])
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
      "122408", // official en 830x355
      "151629", // official es 1000x616
      "80111", // official zh 231x84
      "185519", // white en 654x343
      "6894", // official en 3611x1877
      "163959", // official en 1596x886
      "123823", // official ja 7682x1922
      "146694", // custom en 1088x735
      "163962", // custom it 1596x958
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
      role: "hero",
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

  test("puts a logo no wider than 1024 px before a 3611x1877 one: Pokémon Emerald", () => {
    // Observed: the API lists the 3611x1877 logo first. It is 27 MB once
    // decoded, more than the shell keeps for a whole surface.
    const logos = candidatesOf(call(POKEMON, pokemonArt())).filter(
      candidate => candidate.role === "logo",
    )
    expect((JSON.parse(pokemonLogos) as { data: Asset[] }).data[0]).toMatchObject({
      id: 6894,
      width: 3611,
      height: 1877,
    })
    expect(logos[0]).toStrictEqual({
      role: "logo",
      width: 830,
      height: 355,
      source: {
        id: "122408",
        url: "https://cdn2.steamgriddb.com/logo/5fc6bba3b49d8765a27712ef46444a54.png",
      },
    })
    const widths = logos.map(candidate => candidate.width ?? Infinity)
    const firstWide = widths.findIndex(width => width > 1024)
    expect(firstWide).toBe(4)
    expect(widths.slice(firstWide).every(width => width > 1024)).toBe(true)
    expect(logos[firstWide].source.id).toBe("6894")
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
    expect(candidatesOf(output).map(({ role, width, source }) => [role, width, source.id])).toEqual([
      ["logo", 1936, "151230"],
      ["logo", 3067, "151225"],
    ])
  })

  test("puts a logo of unknown width after one known to be no wider than 1024 px", () => {
    const logos = edited(pokemonLogos, assets => [
      { ...assets[0], id: 1, width: null },
      { ...assets[0], id: 2, width: 1025 },
      { ...assets[0], id: 3, width: 1024 },
    ])
    expect(idsOf(call(POKEMON, pokemonArt({ logo: logos })), "logo")).toEqual(["3", "1", "2"])
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
    const unstyled = edited(tiles, assets => {
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

  test("drops an asset flagged nsfw, humor or epilepsy, in every role", () => {
    const first = { tile: 4, poster: 169090, hero: 2748, logo: 122408 }
    const lists = { tile: tiles, poster: pokemonPosters, hero: pokemonHeroes, logo: pokemonLogos }
    const all = call(POKEMON, pokemonArt())
    for (const role of ["tile", "poster", "hero", "logo"] as const) {
      for (const flag of ["nsfw", "humor", "epilepsy"]) {
        const flagged = editedAsset(lists[role], first[role], { [flag]: true })
        const output = call(POKEMON, pokemonArt({ [role]: flagged }))
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
          tile: flagged(tiles),
          poster: flagged(pokemonPosters),
          hero: flagged(pokemonHeroes),
          logo: flagged(pokemonLogos),
        }),
      ),
    ).toStrictEqual({ candidates: [] })
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
          role: "poster",
          width: 600,
          height: 900,
          source: {
            id: "582961",
            url: "https://cdn2.steamgriddb.com/grid/2fedaac8ebf4bb793a8e06b2ff9bf9ac.png",
          },
        },
        {
          role: "poster",
          width: 600,
          height: 900,
          source: {
            id: "692516",
            url: "https://cdn2.steamgriddb.com/grid/b275be65d4e421e3568be1ef6a8e2455.png",
          },
        },
        {
          role: "logo",
          width: 1936,
          height: 1243,
          source: {
            id: "151230",
            url: "https://cdn2.steamgriddb.com/logo/9e4002b5735e8ada36a039c0741aafd4.png",
          },
        },
        {
          role: "logo",
          width: 3067,
          height: 1893,
          source: {
            id: "151225",
            url: "https://cdn2.steamgriddb.com/logo/9d3a60e4e2ea458b1a1b3ab3ced35125.png",
          },
        },
      ],
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
      candidatesOf(call(POKEMON, pokemonArt({ logo }))).filter(candidate => candidate.role === "logo"),
    ).toStrictEqual([
      // The one logo known to be no wider than 1024 px comes first.
      { role: "logo", width: 640, source: { id: "3", url } },
      { role: "logo", source: { id: "1", url } },
      { role: "logo", source: { id: "2", url } },
    ] as Candidate[])
  })

  test("names only the image host that plugin.nix declares", () => {
    for (const candidate of candidatesOf(call(POKEMON, pokemonArt()))) {
      expect(candidate.source.url.startsWith("https://cdn2.steamgriddb.com/")).toBe(true)
    }
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

function tile(id: number): Candidate {
  return {
    role: "tile",
    width: 512,
    height: 512,
    source: {
      id: String(id),
      url: `https://cdn2.steamgriddb.com/grid/${String(id).padStart(32, "0")}.png`,
    },
  }
}

// The fixture's own `url` for an asset: the plugin passes it through as it is.
function assetUrl(list: string, id: string): string {
  const asset = (JSON.parse(list) as { data: Asset[] }).data.find(entry => String(entry.id) === id)
  if (typeof asset?.url !== "string") throw new Error(`fixture has no asset ${id}`)
  return asset.url
}

function poster(id: string): Candidate {
  return { role: "poster", width: 600, height: 900, source: { id, url: assetUrl(pokemonPosters, id) } }
}

function hero(id: string, width: number, height: number): Candidate {
  return { role: "hero", width, height, source: { id, url: assetUrl(pokemonHeroes, id) } }
}

function superMetroidHero(id: string, width: number, height: number): Candidate {
  return { role: "hero", width, height, source: { id, url: assetUrl(superMetroidHeroes, id) } }
}

function logo(id: string, width: number, height: number): Candidate {
  return { role: "logo", width, height, source: { id, url: assetUrl(pokemonLogos, id) } }
}

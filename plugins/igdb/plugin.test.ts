import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import * as plugin from "./plugin"

// Responses shaped as IGDB's documentation shows them (README, "Fixtures").
// No live IGDB answer is committed: a live call needs a person's own Twitch
// client ID and secret. The game ids are made up. The image ids `co1wyy`,
// `co1x7g`, `ar5l8` and `ar1bpe` are real images whose stored size was
// measured on images.igdb.com on 2026-11-20; which game they belong to is
// not claimed. Every other image id is made up.
const fixture = (name: string) =>
  readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8")

const superMetroidSearch = fixture("search-super-metroid.json")
const pokemonSearch = fixture("search-pokemon-emerald.json")
const tetrisSearch = fixture("search-tetris.json")
const emptySearch = fixture("search-empty.json")
const superMetroidArt = fixture("art-super-metroid.json")
const emptyArt = fixture("art-empty.json")

const SNES = { id: "snes", title: "Super Nintendo", externalIds: { igdb: ["19", "58"], wikidata: ["Q183259"] } }
const GBA = { id: "gba", externalIds: { igdb: ["24"] } }

const ok = (text: string, url = "https://api.igdb.com/v4/games") => ({
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
type Request = {
  url: string
  method?: string
  body?: unknown
  query?: unknown
  headers?: Record<string, string>
}

const call = (input: Record<string, unknown>, responses: unknown[] = []) =>
  plugin.handlers["game-assets.candidates"]({ externalIds: {}, ...input, responses } as never)
const requestsOf = (output: unknown) => {
  expect(output).toHaveProperty("_tag", "HttpRequests")
  return (output as { requests: Request[] }).requests
}
const resultOf = (output: unknown) =>
  output as { candidates: Candidate[]; externalIds?: Record<string, string[]> }
const urlsOf = (output: unknown, kind: string) =>
  resultOf(output)
    .candidates.filter(candidate => candidate.kind === kind)
    .map(candidate => candidate.source.url)

const IMAGE = "https://images.igdb.com/igdb/image/upload"

describe("declaration", () => {
  test("names one artwork handler and no providers", () => {
    expect(plugin.name).toBe("igdb")
    expect(Object.keys(plugin.handlers)).toEqual(["game-assets.candidates"])
    expect("providers" in plugin).toBe(false)
  })

  test("the plugin never sets a credential header and holds no key", () => {
    const source = readFileSync(new URL("./plugin.ts", import.meta.url), "utf8")
    expect(source.toLowerCase()).not.toMatch(/["']authorization["']\s*:/)
    expect(source.toLowerCase()).not.toMatch(/["']client-id["']\s*:/)
    expect(source).not.toMatch(/client_secret|access_token/)
  })
})

describe("requests", () => {
  test("a title search is one raw Apicalypse POST, filtered by the system's IGDB platforms", () => {
    const [search, ...rest] = requestsOf(call({ title: "Super Metroid", system: SNES }))
    expect(rest).toEqual([])
    expect(search).toEqual({
      url: "https://api.igdb.com/v4/games",
      method: "POST",
      headers: { accept: "application/json" },
      body: 'search "Super Metroid"; fields id,name; where platforms = (19,58) & version_parent = null; limit 50;',
    })
    // No query string: korrid's image and API rules both refuse none, but the
    // whole query is in the body.
    expect(search.query).toBeUndefined()
  })

  test("a quote or a backslash in a title cannot end the Apicalypse string", () => {
    const [search] = requestsOf(call({ title: 'Ys "Book" \\ I\n& II', system: SNES }))
    expect(search.body).toBe(
      'search "Ys Book I & II"; fields id,name; where platforms = (19,58) & version_parent = null; limit 50;',
    )
  })

  test("the art of a match is one multiquery POST of covers, artworks and logos where game = id", () => {
    const [art] = requestsOf(call({ title: "Super Metroid", system: SNES }, [ok(superMetroidSearch)]))
    expect(art.url).toBe("https://api.igdb.com/v4/multiquery")
    expect(art.method).toBe("POST")
    expect(art.body).toBe(
      [
        'query covers "covers" { fields image_id,width,height,alpha_channel,animated; where game = 900101; limit 50; };',
        'query artworks "artworks" { fields image_id,width,height,alpha_channel,animated; where game = 900101; limit 50; };',
        'query logos "logos" { fields image_id,width,height,alpha_channel,animated; where game = 900101; limit 50; };',
      ].join("\n"),
    )
  })

  test("a stored IGDB id skips the search, also with no platform and no title", () => {
    for (const input of [
      { title: "Super Metroid", system: SNES, externalIds: { igdb: ["1103"] } },
      { title: "", externalIds: { steamgriddb: ["38157"], igdb: ["not-an-id", "1103"] } },
    ]) {
      const [art] = requestsOf(call(input))
      expect(art.url).toBe("https://api.igdb.com/v4/multiquery")
      expect(art.body).toContain("where game = 1103;")
    }
    const output = resultOf(call({ title: "x", externalIds: { igdb: ["1103"] } }, [ok(superMetroidArt)]))
    expect(output.externalIds).toEqual({ igdb: ["1103"] })
  })

  test("no platform to filter by, or no letter in the title, asks nothing", () => {
    for (const input of [
      { title: "Super Metroid" },
      { title: "Super Metroid", system: { id: "snes", externalIds: {} } },
      { title: "Super Metroid", system: { id: "snes", externalIds: { igdb: ["SNES"] } } },
      { title: "!!!", system: SNES },
    ]) {
      expect(call(input)).toEqual({ candidates: [] })
    }
  })
})

describe("match", () => {
  test("the one equal name is the match, and its id is returned", () => {
    const output = resultOf(call({ title: "Super Metroid", system: SNES }, [ok(superMetroidSearch), ok(superMetroidArt)]))
    expect(output.externalIds).toEqual({ igdb: ["900101"] })
  })

  test("names match with accents folded, case, punctuation and a trailing version word", () => {
    for (const title of ["Pokemon Emerald", "POKÉMON: Emerald Version", "pokemon-emerald"]) {
      const [art] = requestsOf(call({ title, system: GBA }, [ok(pokemonSearch)]))
      expect(art.body).toContain("where game = 900201;")
    }
  })

  test("a near name is no match: no fuzzy matching", () => {
    for (const title of ["Super Metroid Redesign X", "Super Metro", "Metroid Fusion"]) {
      expect(call({ title, system: SNES }, [ok(superMetroidSearch)])).toEqual({ candidates: [] })
    }
    expect(call({ title: "Super Metroid", system: SNES }, [ok(emptySearch)])).toEqual({ candidates: [] })
  })

  test("two equal names on the system's platforms are a tie and no match", () => {
    expect(call({ title: "Tetris", system: { id: "nes", externalIds: { igdb: ["18", "99"] } } }, [ok(tetrisSearch)])).toEqual({
      candidates: [],
    })
  })
})

describe("candidates", () => {
  const output = resultOf(call({ title: "Super Metroid", system: SNES }, [ok(superMetroidSearch), ok(superMetroidArt)]))

  test("covers and artworks are pictures with the measured size of the IGDB size served", () => {
    expect(output.candidates.filter(c => c.kind === "picture")).toEqual([
      // The first cover first. 1170x1559 fits 1920x1080 at 811x1080, as
      // images.igdb.com served t_1080p/co1wyy.jpg on 2026-11-20.
      { kind: "picture", width: 811, height: 1080, source: { id: "co1wyy", url: `${IMAGE}/t_1080p/co1wyy.jpg` } },
      // Then every artwork, the largest first, whatever its ratio.
      { kind: "picture", width: 1920, height: 1080, source: { id: "ar5l8", url: `${IMAGE}/t_1080p/ar5l8.jpg` } },
      { kind: "picture", width: 1920, height: 620, source: { id: "arwide0001", url: `${IMAGE}/t_1080p/arwide0001.jpg` } },
      // 1600x190 would be scaled up at 1080p; 720p serves 1280x152.
      { kind: "picture", width: 1280, height: 152, source: { id: "ar1bpe", url: `${IMAGE}/t_720p/ar1bpe.jpg` } },
      // Then the other covers. 800x1148 at 753x1080, as served.
      { kind: "picture", width: 753, height: 1080, source: { id: "co1x7g", url: `${IMAGE}/t_1080p/co1x7g.jpg` } },
    ])
  })

  test("logos are logos with alpha, as PNG, the largest first", () => {
    expect(output.candidates.filter(c => c.kind === "logo")).toEqual([
      { kind: "logo", width: 1280, height: 665, source: { id: "lgalpha001", url: `${IMAGE}/t_720p/lgalpha001.png` } },
      { kind: "logo", width: 528, height: 264, source: { id: "lgalpha002", url: `${IMAGE}/t_cover_big_2x/lgalpha002.png` } },
    ])
  })

  test("an animated image, a logo without alpha and an image smaller than every size are not offered", () => {
    const ids = output.candidates.map(c => c.source.id)
    expect(ids).not.toContain("aranim0001")
    expect(ids).not.toContain("lgopaque01")
    expect(ids).not.toContain("artiny0001")
  })

  test("only the kinds of the contract, and URLs korrid admits: https, images.igdb.com, no query", () => {
    for (const candidate of output.candidates) {
      expect(["logo", "picture"]).toContain(candidate.kind)
      expect("role" in candidate).toBe(false)
      const url = new URL(candidate.source.url)
      expect(url.protocol).toBe("https:")
      expect(url.host).toBe("images.igdb.com")
      expect(url.search).toBe("")
      expect(url.hash).toBe("")
    }
  })

  test("a matched game with no art still names its id", () => {
    expect(call({ title: "Super Metroid", system: SNES }, [ok(superMetroidSearch), ok(emptyArt)])).toEqual({
      candidates: [],
      externalIds: { igdb: ["900101"] },
    })
  })

  test("the served size follows the Fit rule measured on images.igdb.com", () => {
    // Stored size, served size: t_720p, t_cover_big and t_cover_big_2x of
    // these images measured on 2026-11-20 (README, "Sizes").
    const art = (width: number, height: number) =>
      JSON.stringify([
        { name: "covers", result: [{ image_id: "x1", width, height, alpha_channel: false, animated: false }] },
        { name: "artworks", result: [] },
        { name: "logos", result: [] },
      ])
    const served = (width: number, height: number) =>
      resultOf(call({ title: "x", externalIds: { igdb: ["1"] } }, [ok(art(width, height))])).candidates[0]
    expect(served(1200, 1128)).toMatchObject({ width: 1149, height: 1080, source: { url: `${IMAGE}/t_1080p/x1.jpg` } })
    expect(served(600, 800)).toMatchObject({ width: 540, height: 720, source: { url: `${IMAGE}/t_720p/x1.jpg` } })
    expect(served(342, 456)).toMatchObject({ width: 264, height: 352, source: { url: `${IMAGE}/t_cover_big/x1.jpg` } })
    expect(served(1920, 1080)).toMatchObject({ width: 1920, height: 1080, source: { url: `${IMAGE}/t_1080p/x1.jpg` } })
  })
})

describe("failures", () => {
  test("a response that is not 2xx JSON fails the lookup, so korrid asks again later", () => {
    const input = { title: "Super Metroid", system: SNES }
    expect(() => call(input, [status(429, "Too Many Requests")])).toThrow("HTTP 429")
    expect(() => call(input, [ok("<html>")])).toThrow("not JSON")
    expect(() => call(input, [ok("{}")])).toThrow("did not answer a list")
    expect(() => call(input, [ok(superMetroidSearch), status(500)])).toThrow("HTTP 500")
    expect(() => call(input, [ok(superMetroidSearch), ok('[{"name":"covers","result":[]}]')])).toThrow(
      "no artworks list",
    )
    expect(() => call(input, [ok(superMetroidSearch), ok(superMetroidArt), ok(superMetroidArt)])).toThrow(
      "expected 1 response",
    )
  })
})

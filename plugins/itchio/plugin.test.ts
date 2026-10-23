import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { handlers, providers } from "./plugin"

const providerId = "@korri:itchio"
const pageUrl = "https://0neforgetfulbug.itch.io/average-day-in-america"
const id = "0neforgetfulbug/average-day-in-america"
const page = readFileSync(
  new URL("./fixtures/average-day-in-america.html", import.meta.url),
  "utf8",
)
const artifactHost =
  "itchio-mirror.cb031a832f44726753d6267436f3b414.r2.cloudflarestorage.com"
// Synthetic URL, not a recorded signed download URL.
const artifactUrl = `https://${artifactHost}/fixture/adia.bitsy`
const response = (text: string, url = pageUrl, status = 200) => ({
  text,
  url,
  status,
  ok: status >= 200 && status < 300,
  headers: {},
})
const search = (query: string, responses: ReturnType<typeof response>[] = []) =>
  handlers["claims.search"]({ providerId, query, responses })
const details = (claimId = id, responses: ReturnType<typeof response>[] = []) =>
  handlers["claims.details"]({ providerId, id: claimId, responses })
const resolve = (
  responses: ReturnType<typeof response>[] = [],
  fileName?: string,
  candidateUrl = pageUrl,
) =>
  handlers["artifact.resolve-download"]({
    providerId,
    candidateUrl,
    fileName,
    responses,
  })
const notFinal = {
  _tag: "NonFinalDownload",
  providerId,
  reason: "requires-user-action",
}
const fileRequest = {
  _tag: "HttpRequests",
  requests: [
    {
      url: `${pageUrl}/file/13245378`,
      query: {
        source: "view_game",
        as_props: "1",
        after_download_lightbox: "true",
      },
      method: "POST",
      body: { csrf_token: "fixture-csrf" },
    },
  ],
}
const otherUpload = `<div class="upload"><a class="download_btn" data-upload_id="2">Download</a><div class="info_column"><div class="upload_name"><strong class="name">other.bitsy</strong></div></div></div>`
const feed = `<rss><channel><item><guid>${pageUrl}</guid><link>${pageUrl}</link><plainTitle>Average Day in America</plainTitle></item><item><link>https://unsupported.itch.io/game</link><plainTitle>Other</plainTitle></item></channel></rss>`
const listing = `<div class="game_cell"><div class="game_title"><a class="title game_link" href="${pageUrl}">Average Day in America</a></div></div><div class="game_cell"><a class="title game_link" href="https://unsupported.itch.io/game">Other</a></div>`

describe("itch.io supported-creator Bitsy attachment provider", () => {
  test("declares the legacy provider identity and only acquisition operations", () => {
    expect(providers[providerId].id).toBe(providerId)
    expect(providers[providerId].title).toContain("supported Bitsy attachments")
    expect(Object.keys(handlers).sort()).toEqual([
      "artifact.resolve-download",
      "claims.details",
      "claims.search",
    ])
  })

  test("searches live RSS then search-page markup, but claims no system from a tag", () => {
    expect(search("bitsy")).toEqual({
      _tag: "HttpRequests",
      requests: [{ url: "https://itch.io/games/tag-bitsy.xml" }],
    })
    const claims = search("bitsy", [
      response(feed, "https://itch.io/games/tag-bitsy.xml"),
    ])
    expect(claims).toEqual([
      {
        _tag: "ProviderClaim",
        providerId,
        id,
        title: "Average Day in America",
        url: pageUrl,
      },
    ])
    expect(
      search("average day", [
        response("", "https://itch.io/games/tag-average-day.xml", 404),
      ]),
    ).toEqual({
      _tag: "HttpRequests",
      requests: [
        {
          url: "https://itch.io/search",
          query: { q: "average day", type: "games" },
        },
      ],
    })
    expect(
      search("average day", [
        response("", "https://itch.io/games/tag-average-day.xml", 404),
        response(listing, "https://itch.io/search"),
      ]),
    ).toEqual(claims)
  })

  test("accepts a supported creator page URL as a live search, without pinned catalog entries", () => {
    expect(search(pageUrl)).toEqual({
      _tag: "HttpRequests",
      requests: [{ url: pageUrl }],
    })
    expect(search(pageUrl, [response(page)])).toMatchObject([
      {
        id,
        title: "Average Day in America by Bug",
        artifact: { system: "bitsy", file: { name: "adia.bitsy" } },
      },
    ])
  })

  test("parses the recorded live search and excludes its other creator", () => {
    const liveSearch = readFileSync(
      new URL("./fixtures/search-average-day-in-america.html", import.meta.url),
      "utf8",
    )
    expect(
      search("average day in america", [
        response(
          "",
          "https://itch.io/games/tag-average-day-in-america.xml",
          404,
        ),
        response(
          liveSearch,
          "https://itch.io/search?q=average+day+in+america&type=games",
        ),
      ]),
    ).toEqual([
      {
        _tag: "ProviderClaim",
        providerId,
        id,
        title: "Average Day in America",
        url: pageUrl,
      },
    ])
  })

  test("blank and unsupported URL queries perform no request", () => {
    expect(search(" ")).toEqual([])
    expect(search("https://unsupported.itch.io/game")).toEqual([])
  })

  test("recognizes actual empty search pages and feeds", () => {
    expect(
      search("empty", [
        response(
          "<rss><channel></channel></rss>",
          "https://itch.io/games/tag-empty.xml",
        ),
      ]),
    ).toEqual({
      _tag: "HttpRequests",
      requests: [
        { url: "https://itch.io/search", query: { q: "empty", type: "games" } },
      ],
    })
    expect(
      search("empty", [
        response("<rss><channel></channel></rss>"),
        response('<div class="no_results">No results found</div>'),
      ]),
    ).toEqual([])
  })

  test("malformed and refused search responses fail instead of synthesizing claims", () => {
    expect(() =>
      search("bitsy", [response("<html>unexpected</html>")]),
    ).toThrow("markup")
    expect(() =>
      search("bitsy", [
        response("<rss><channel><item>changed</item></channel></rss>"),
      ]),
    ).toThrow("markup")
    expect(() =>
      search("bitsy", [
        response("", "https://itch.io/games/tag-bitsy.xml", 404),
        response('<div class="game_cell">changed</div>'),
      ]),
    ).toThrow("markup")
    expect(() =>
      search("bitsy", [
        response("", "https://itch.io/games/tag-bitsy.xml", 403),
      ]),
    ).toThrow("403")
    expect(() =>
      search("bitsy", [
        response("", "https://itch.io/games/tag-bitsy.xml", 404),
        response("changed", "https://itch.io/search"),
      ]),
    ).toThrow("markup")
    expect(() =>
      search("bitsy", [
        response("", "https://itch.io/games/tag-bitsy.xml", 404),
        response("", "https://itch.io/search", 500),
      ]),
    ).toThrow("500")
  })

  test("search filters unsupported creators rather than fetching them", () => {
    expect(
      search("bitsy", [
        response(
          feed.replaceAll(pageUrl, "https://elsewhere.itch.io/game"),
          "https://itch.io/games/tag-bitsy.xml",
        ),
      ]),
    ).toEqual([])
  })

  test("details fetch the actual page and enable Get only from explicit zero price and raw upload", () => {
    expect(details()).toEqual({
      _tag: "HttpRequests",
      requests: [{ url: pageUrl }],
    })
    expect(details(id, [response(page)])).toEqual({
      _tag: "ProviderClaimDetails",
      providerId,
      id,
      title: "Average Day in America by Bug",
      url: pageUrl,
      artifact: {
        kind: "content",
        system: "bitsy",
        format: { id: "bitsy" },
        file: { name: "adia.bitsy", extension: "bitsy" },
      },
    })
  })

  test("does not assume absent data.json prices mean free", () => {
    const missing = page.replace('"actual_price":0,"min_price":0,', "")
    expect(details(id, [response(missing)])).not.toHaveProperty("artifact")
    expect(resolve([response(missing)])).toMatchObject(notFinal)
    expect(
      resolve([response('{"id":3425263,"title":"Average Day in America"}')]),
    ).toMatchObject(notFinal)
  })

  test("only literal numeric zero prices in static JSON qualify", () => {
    for (const html of [
      page.replace('"actual_price":0', '"actual_price":1'),
      page.replace('"min_price":0', '"min_price":100'),
      page.replace('"actual_price":0,', ""),
      page.replace('"min_price":0,', ""),
      page.replace('"min_price":0', '"min_price":"0"'),
      page.replace('"min_price":0', '"min_price":null'),
      page.replace('"min_price":0', '"min_price":0+sideEffect()'),
      page.replace('"type_name":"html"', '"type_name":"default"'),
      page + page,
    ]) {
      expect(details(id, [response(html)])).not.toHaveProperty("artifact")
      expect(resolve([response(html)])).toMatchObject(notFinal)
    }
  })

  test("browser-only pages and non-bitsy attachments stay unavailable", () => {
    for (const html of [
      page.replace(/<div class="upload">[\s\S]*/, ""),
      page.replaceAll("adia.bitsy", "game.html"),
      page.replaceAll("adia.bitsy", "game.zip"),
    ]) {
      expect(details(id, [response(html)])).not.toHaveProperty("artifact")
      expect(resolve([response(html)])).toMatchObject(notFinal)
    }
  })

  test("does not invent details for upstream or unsupported creator errors", () => {
    expect(() => details("other/game")).toThrow("Unsupported")
    expect(() => details(id, [response("", pageUrl, 404)])).toThrow("404")
    expect(() => details(id, [response("<html></html>")])).toThrow("title")
    expect(() => search(pageUrl, [response("", pageUrl, 500)])).toThrow("500")
  })

  test("resolves the direct upload in three calls with no cookie request", () => {
    expect(resolve()).toEqual({
      _tag: "HttpRequests",
      requests: [{ url: pageUrl }],
    })
    expect(resolve([response(page)])).toEqual(fileRequest)
    expect(
      resolve([response(page), response(JSON.stringify({ url: artifactUrl }))]),
    ).toEqual({
      _tag: "FinalDownload",
      providerId,
      url: artifactUrl,
      filename: "adia.bitsy",
    })
    expect(resolve([response(page)], "ADIA.BITSY")).toEqual(fileRequest)
  })

  test("uses a uniquely matching filename; ambiguous choices do not POST", () => {
    const ambiguous = page + otherUpload
    expect(resolve([response(ambiguous)])).toMatchObject({
      ...notFinal,
      choices: [
        { id: "13245378", fileName: "adia.bitsy" },
        { id: "2", fileName: "other.bitsy" },
      ],
    })
    expect(resolve([response(ambiguous)], "adia.bitsy")).toEqual(fileRequest)
    expect(resolve([response(ambiguous)], "missing.bitsy")).toMatchObject(
      notFinal,
    )
    expect(
      resolve(
        [response(ambiguous.replaceAll("other.bitsy", "adia.bitsy"))],
        "adia.bitsy",
      ),
    ).toMatchObject(notFinal)
  })

  test("missing CSRF and malformed or unsafe upload controls stay non-final", () => {
    for (const html of [
      page.replace('<meta name="csrf_token" value="fixture-csrf">', ""),
      page.replaceAll("adia.bitsy", "../adia.bitsy"),
      page.replaceAll("adia.bitsy", "bad&#10;.bitsy"),
      page.replace('data-upload_id="13245378"', 'data-upload_id="1/../../x"'),
      page.replace('class="button download_btn"', 'class="unrelated"'),
    ])
      expect(resolve([response(html)])).toMatchObject(notFinal)
  })

  test("candidate URLs cannot escape the supported literal path", () => {
    for (const url of [
      "https://0neforgetfulbug.itch.io.evil.test/game",
      "https://evil@0neforgetfulbug.itch.io/game",
      "http://0neforgetfulbug.itch.io/game",
      "https://0neforgetfulbug.itch.io:443/game",
      `${pageUrl}/download/key`,
      `${pageUrl}?a=1`,
      `${pageUrl}#fragment`,
      "https://0neforgetfulbug.itch.io/%2e%2e",
      "https://0neforgetfulbug.itch.io/a'quote",
      "https://0neforgetfulbug.itch.io/a\\path",
      "https://elsewhere.itch.io/game",
    ])
      expect(resolve([], undefined, url)).toMatchObject({
        _tag: "NonFinalDownload",
        reason: "unsupported",
      })
  })

  test("upstream file/page refusals are honest and do not request a session", () => {
    for (const code of [403, 404, 429, 500]) {
      expect(resolve([response("", pageUrl, code)])).toMatchObject({
        _tag: "FailedDownload",
        reason: code === 404 ? "not-found" : "provider-error",
      })
      expect(
        resolve([
          response(page),
          response("", `${pageUrl}/file/13245378`, code),
        ]),
      ).toMatchObject({
        _tag: "FailedDownload",
        reason: code === 404 ? "not-found" : "provider-error",
      })
    }
  })

  test("malformed or unapproved final URLs stay non-final", () => {
    for (const text of [
      "not JSON",
      "{}",
      '{"url":null}',
      JSON.stringify({ url: "https://other.test/adia.bitsy" }),
      JSON.stringify({ url: `https://u:p@${artifactHost}/adia.bitsy` }),
      JSON.stringify({ url: `http://${artifactHost}/adia.bitsy` }),
    ]) {
      expect(resolve([response(page), response(text)])).toMatchObject(notFinal)
    }
  })
})

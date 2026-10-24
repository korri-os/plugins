import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import type { PluginHttpResponse } from "../../contracts/generated/korrid"
import { handlers, providers } from "./plugin"

// All committed fixture text is original test data. Live catalogs are not bundled.
const fixture = (name: string) =>
  readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8")
const providerId = "@korri:puzzlescript"
const candidateUrl = "https://www.puzzlescript.net/play.html?p=6994394"
const catalog = fixture("catalog.js")
const ok = (text: string): PluginHttpResponse => ({
  status: 200,
  ok: true,
  url: candidateUrl,
  headers: {},
  text,
})
const unavailable = { ...ok(""), status: 503, ok: false }
const search = (query = "panda", responses: PluginHttpResponse[] = []) =>
  handlers["claims.search"]({ providerId, query, responses })
const details = (responses: PluginHttpResponse[] = [], id = "6994394") =>
  handlers["claims.details"]({ providerId, id, responses })
const resolve = (responses: PluginHttpResponse[] = [], url = candidateUrl) =>
  handlers["artifact.resolve-download"]({ providerId, candidateUrl: url, responses })

function found(query: string, responses: PluginHttpResponse[]) {
  const output = search(query, responses)
  if (!Array.isArray(output)) throw new Error("Expected claims, not HTTP requests")
  return output
}

describe("puzzlescript pure provider turns", () => {
  test("declares the explicit provider and three handlers", () => {
    expect(providers[providerId].id).toBe(providerId)
    expect(Object.keys(handlers).sort()).toEqual([
      "artifact.resolve-download",
      "claims.details",
      "claims.search",
    ])
  })
  test("blank search needs no network; nonempty search asks for real upstream data", () => {
    expect(search("  ")).toEqual([])
    expect(search()).toEqual({
      _tag: "HttpRequests",
      requests: [{ url: "https://www.puzzlescript.net/games_dat.js" }],
    })
  })
  test("filters or searches actual response rows and returns the grounded id", () => {
    const claims = found("panda", [ok(catalog)])
    expect(claims).toHaveLength(1)
    expect(claims[0]).toMatchObject({
      _tag: "ProviderClaim",
      providerId,
      id: "6994394",
      platform: "puzzlescript",
    })
  })
  test("HTTP and parser failures are not empty results", () => {
    expect(() => search("panda", [unavailable])).toThrow("HTTP 503")
    expect(() => search("panda", [ok("<html>upstream changed</html>")])).toThrow()
  })
  test("rejects malformed candidate URLs without network or final downloads", () => {
    for (const url of [
      `${candidateUrl}#bad`,
      `${candidateUrl}\n`,
      `${candidateUrl}&duplicate=1`,
      candidateUrl.replace("https://", "http://"),
      candidateUrl.replace("https://", "https://user@"),
      candidateUrl.replace("https://", "https://evil.invalid/"),
      candidateUrl.replace("https://", "https://\\"),
      "https://evil.invalid/cart.nx",
    ]) {
      expect(resolve([], url)).toMatchObject({ _tag: "NonFinalDownload", reason: "unsupported" })
    }
    expect(() => details([], "../bad")).toThrow()
    expect(() => details([], "6994394\n")).toThrow()
  })
  test("details and resolution name a real supported file, without transformations", () => {
    const responses = [ok(catalog), ok(fixture("source.txt"))]
    expect(details(responses)).toMatchObject({
      _tag: "ProviderClaimDetails",
      artifact: {
        system: "puzzlescript",
        format: { id: "pz" },
        file: { name: "6994394.pz", extension: "pz" },
      },
    })
    expect(resolve(responses)).toMatchObject({
      _tag: "FinalDownload",
      providerId,
      filename: "6994394.pz",
    })
  })
  test("resolution reports upstream failures explicitly", () => {
    expect(resolve([unavailable])).toMatchObject({
      _tag: "FailedDownload",
      reason: "provider-error",
    })
    expect(resolve([{ ...ok(""), status: 404, ok: false }])).toMatchObject({
      _tag: "FailedDownload",
      reason: "not-found",
    })
  })
  test("a valid catalog with no matching title is genuinely empty", () => {
    expect(search("no-such-original-title", [ok(catalog)])).toEqual([])
  })
  test("accepts inert JSON data with a trailing comma, never JavaScript expressions", () => {
    for (const text of [
      `${catalog}; globalThis.compromised = true`,
      catalog.replace('"Korri Panda"', "(globalThis.compromised = true)"),
      catalog.replace('"Korri Panda"', "`template`"),
    ]) {
      expect(() => search("panda", [ok(text)])).toThrow()
    }
    expect(globalThis).not.toHaveProperty("compromised")
  })
  test("never renames HTML or a missing source to .pz", () => {
    expect(resolve([ok(catalog), ok("<!doctype html><html>Not source</html>")])).toMatchObject({
      _tag: "NonFinalDownload",
      reason: "unsupported",
    })
    expect(details([ok(catalog), { ...ok(""), status: 404, ok: false }])).not.toHaveProperty(
      "artifact",
    )
  })
  test("preserves quoted commas and escaped quotes as inert title text", () => {
    const title = 'Original ,] "Panda"'
    const modified = catalog.replace('"Korri Panda"', JSON.stringify(title))
    expect(found("panda", [ok(modified)])[0].title).toBe(title)
  })
  test("uses at most three turns with cumulative responses", () => {
    expect(details()).toEqual({
      _tag: "HttpRequests",
      requests: [{ url: "https://www.puzzlescript.net/games_dat.js" }],
    })
    expect(details([ok(catalog)])).toEqual({
      _tag: "HttpRequests",
      requests: [{ url: "https://gist.githubusercontent.com/anonymous/6994394/raw/script.txt" }],
    })
    expect(resolve([ok(catalog)])).toEqual(details([ok(catalog)]))
    expect(resolve([ok(catalog), unavailable])).toMatchObject({
      _tag: "FailedDownload",
      reason: "provider-error",
    })
    expect(
      resolve([
        ok(catalog),
        { ...ok(fixture("source.txt")), headers: { "content-type": "text/html" } },
      ]),
    ).toMatchObject({ _tag: "NonFinalDownload", reason: "unsupported" })
  })
})

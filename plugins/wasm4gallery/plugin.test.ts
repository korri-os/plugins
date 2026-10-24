import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import type { PluginHttpResponse } from "../../contracts/generated/korrid"
import { handlers, providers } from "./plugin"

// All committed fixture text is original test data. Live catalogs are not bundled.
const fixture = (name: string) =>
  readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8")
const providerId = "@korri:wasm4gallery"
const candidateUrl = "https://wasm4.org/play/korri-snake/"
const catalog = fixture("catalog.html")
const ok = (text: string): PluginHttpResponse => ({
  status: 200,
  ok: true,
  url: candidateUrl,
  headers: {},
  text,
})
const unavailable = { ...ok(""), status: 503, ok: false }
const search = (query = "snake", responses: PluginHttpResponse[] = []) =>
  handlers["claims.search"]({ providerId, query, responses })
const details = (responses: PluginHttpResponse[] = [], id = "korri-snake") =>
  handlers["claims.details"]({ providerId, id, responses })
const resolve = (responses: PluginHttpResponse[] = [], url = candidateUrl) =>
  handlers["artifact.resolve-download"]({ providerId, candidateUrl: url, responses })

function found(query: string, responses: PluginHttpResponse[]) {
  const output = search(query, responses)
  if (!Array.isArray(output)) throw new Error("Expected claims, not HTTP requests")
  return output
}

describe("wasm4gallery pure provider turns", () => {
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
      requests: [{ url: "https://wasm4.org/play/" }],
    })
  })
  test("filters or searches actual response rows and returns the grounded id", () => {
    const claims = found("snake", [ok(catalog)])
    expect(claims).toHaveLength(1)
    expect(claims[0]).toMatchObject({
      _tag: "ProviderClaim",
      providerId,
      id: "korri-snake",
      platform: "wasm4",
    })
  })
  test("HTTP and parser failures are not empty results", () => {
    expect(() => search("snake", [unavailable])).toThrow("HTTP 503")
    expect(() => search("snake", [ok("<html>upstream changed</html>")])).toThrow()
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
    expect(() => details([], "korri-snake\n")).toThrow()
  })
  test("details and resolution name a real supported file, without transformations", () => {
    const responses = [ok(fixture("details.html"))]
    expect(details(responses)).toMatchObject({
      _tag: "ProviderClaimDetails",
      artifact: {
        system: "wasm4",
        format: { id: "wasm" },
        file: { name: "korri-snake.wasm", extension: "wasm" },
      },
    })
    expect(resolve(responses)).toMatchObject({
      _tag: "FinalDownload",
      providerId,
      filename: "korri-snake.wasm",
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
  test("requires an offered exact cart link, not a guessed or external download", () => {
    for (const bad of [
      fixture("details.html").replace(
        "/carts/korri-snake.wasm",
        "https://evil.invalid/carts/korri-snake.wasm",
      ),
      fixture("details.html").replace(".wasm", ".html"),
    ]) {
      expect(resolve([ok(bad)])).toMatchObject({ _tag: "NonFinalDownload", reason: "unsupported" })
      expect(details([ok(bad)])).not.toHaveProperty("artifact")
    }
    expect(details([ok(fixture("details.html"))])).toMatchObject({
      description: expect.stringContaining("By Test Author."),
    })
    expect(() => search("snake", [ok(catalog.replace("avatar__name", "changed-name"))])).toThrow()
  })
})

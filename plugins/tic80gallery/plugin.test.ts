import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import type { PluginHttpResponse } from "../../contracts/generated/korrid"
import { handlers, providers } from "./plugin"

// All committed fixture text is original test data. Live catalogs are not bundled.
const fixture = (name: string) =>
  readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8")
const providerId = "@korri:tic80gallery"
const candidateUrl = "https://tic80.com/play?cart=188"
const catalog = fixture("catalog.json")
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
const details = (responses: PluginHttpResponse[] = [], id = "188") =>
  handlers["claims.details"]({ providerId, id, responses })
const resolve = (responses: PluginHttpResponse[] = [], url = candidateUrl) =>
  handlers["artifact.resolve-download"]({ providerId, candidateUrl: url, responses })

function found(query: string, responses: PluginHttpResponse[]) {
  const output = search(query, responses)
  if (!Array.isArray(output)) throw new Error("Expected claims, not HTTP requests")
  return output
}

describe("tic80gallery pure provider turns", () => {
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
      requests: [{ url: "https://tic80.com/json", query: { fn: "dir", path: "Play/Games" } }],
    })
  })
  test("filters or searches actual response rows and returns the grounded id", () => {
    const claims = found("panda", [ok(catalog)])
    expect(claims).toHaveLength(1)
    expect(claims[0]).toMatchObject({
      _tag: "ProviderClaim",
      providerId,
      id: "188",
      platform: "tic80",
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
    expect(() => details([], "188\n")).toThrow()
  })
  test("details and resolution name a real supported file, without transformations", () => {
    const responses = [ok(catalog)]
    expect(details(responses)).toMatchObject({
      _tag: "ProviderClaimDetails",
      artifact: {
        system: "tic80",
        format: { id: "tic" },
        file: { name: "korri_panda.tic", extension: "tic" },
      },
    })
    expect(resolve(responses)).toMatchObject({
      _tag: "FinalDownload",
      providerId,
      filename: "korri_panda.tic",
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
  test("rejects corrupt directory rows rather than inventing a cart URL", () => {
    for (const bad of [
      catalog.replace("0123456789abcdef0123456789abcdef", "../bad"),
      catalog.replace("korri_panda.tic", "../panda.tic"),
      catalog.replace('"id":188', '"id":"188"'),
    ]) {
      expect(() => search("panda", [ok(bad)])).toThrow()
      expect(resolve([ok(bad)])).toMatchObject({ _tag: "FailedDownload", reason: "provider-error" })
    }
    expect(() => details([ok('{"files":[]}')])).toThrow("Unknown")
    expect(resolve([ok('{"files":[]}')])).toMatchObject({
      _tag: "FailedDownload",
      reason: "not-found",
    })
  })
})

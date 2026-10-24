import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import type { PluginHttpResponse } from "../../contracts/generated/korrid"
import { handlers, providers } from "./plugin"

// All committed fixture text is original test data. Live catalogs are not bundled.
const fixture = (name: string) =>
  readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8")
const providerId = "@korri:pyxelgallery"
const candidateUrl =
  "https://github.com/kitao/pyxel/blob/v2.9.9/python/pyxel/examples/apps/korri_panda.pyxapp"
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
const details = (responses: PluginHttpResponse[] = [], id = "korri_panda.pyxapp") =>
  handlers["claims.details"]({ providerId, id, responses })
const resolve = (responses: PluginHttpResponse[] = [], url = candidateUrl) =>
  handlers["artifact.resolve-download"]({ providerId, candidateUrl: url, responses })

function found(query: string, responses: PluginHttpResponse[]) {
  const output = search(query, responses)
  if (!Array.isArray(output)) throw new Error("Expected claims, not HTTP requests")
  return output
}

describe("pyxelgallery pure provider turns", () => {
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
      requests: [
        {
          url: "https://api.github.com/repos/kitao/pyxel/contents/python/pyxel/examples/apps",
          query: { ref: "v2.9.9" },
          headers: { accept: "application/vnd.github+json" },
        },
      ],
    })
  })
  test("filters or searches actual response rows and returns the grounded id", () => {
    const claims = found("panda", [ok(catalog)])
    expect(claims).toHaveLength(1)
    expect(claims[0]).toMatchObject({
      _tag: "ProviderClaim",
      providerId,
      id: "korri_panda.pyxapp",
      platform: "pyxel",
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
    expect(() => details([], "korri_panda.pyxapp\n")).toThrow()
  })
  test("describes and resolves official native apps without executing Python", () => {
    expect(details([ok(catalog)])).toMatchObject({
      _tag: "ProviderClaimDetails",
      title: "korri panda",
      artifact: {
        system: "pyxel",
        format: { id: "pyxapp" },
        file: { name: "korri_panda.pyxapp", extension: "pyxapp", sizeBytes: 42 },
      },
    })
    expect(resolve([ok(catalog)])).toMatchObject({
      _tag: "FinalDownload",
      filename: "korri_panda.pyxapp",
      url: "https://raw.githubusercontent.com/kitao/pyxel/v2.9.9/python/pyxel/examples/apps/korri_panda.pyxapp",
    })
    expect(resolve([unavailable])).toMatchObject({
      _tag: "FailedDownload",
      reason: "provider-error",
    })
  })
  test("a valid catalog with no matching title is genuinely empty", () => {
    expect(search("no-such-original-title", [ok(catalog)])).toEqual([])
  })
  test("never follows a catalog row outside the fixed official version and paths", () => {
    for (const bad of [
      catalog.replace("raw.githubusercontent.com", "evil.invalid"),
      catalog.replace('"path":"python/pyxel/examples/apps/', '"path":"other/'),
      catalog.replaceAll("v2.9.9", "main"),
    ]) {
      expect(() => search("panda", [ok(bad)])).toThrow()
      expect(resolve([ok(bad)])).toMatchObject({ _tag: "FailedDownload", reason: "provider-error" })
    }
    expect(resolve([ok("[]")])).toMatchObject({ _tag: "FailedDownload", reason: "not-found" })
  })
})

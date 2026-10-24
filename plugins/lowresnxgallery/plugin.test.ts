import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import type { PluginHttpResponse } from "../../contracts/generated/korrid"
import { handlers, providers } from "./plugin"

// All committed fixture text is original test data. Live catalogs are not bundled.
const fixture = (name: string) =>
  readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8")
const providerId = "@korri:lowresnxgallery"
const candidateUrl = "https://lowresnx.inutilis.com/topic.php?id=3873"
const catalog = fixture("catalog.html")
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
const details = (responses: PluginHttpResponse[] = [], id = "3873") =>
  handlers["claims.details"]({ providerId, id, responses })
const resolve = (responses: PluginHttpResponse[] = [], url = candidateUrl) =>
  handlers["artifact.resolve-download"]({ providerId, candidateUrl: url, responses })

function found(query: string, responses: PluginHttpResponse[]) {
  const output = search(query, responses)
  if (!Array.isArray(output)) throw new Error("Expected claims, not HTTP requests")
  return output
}

describe("lowresnxgallery pure provider turns", () => {
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
      requests: [{ url: "https://lowresnx.inutilis.com/programs.php", query: { search: "panda" } }],
    })
  })
  test("filters or searches actual response rows and returns the grounded id", () => {
    const claims = found("panda", [ok(catalog)])
    expect(claims).toHaveLength(1)
    expect(claims[0]).toMatchObject({
      _tag: "ProviderClaim",
      providerId,
      id: "3873",
      platform: "lowresnx",
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
    expect(() => details([], "3873\n")).toThrow()
  })
  test("details and resolution name a real supported file, without transformations", () => {
    const responses = [ok(fixture("details.html"))]
    expect(details(responses)).toMatchObject({
      _tag: "ProviderClaimDetails",
      artifact: {
        system: "lowresnx",
        format: { id: "nx" },
        file: { name: "korri_panda.nx", extension: "nx" },
      },
    })
    expect(resolve(responses)).toMatchObject({
      _tag: "FinalDownload",
      providerId,
      filename: "korri_panda.nx",
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
  test("uses the primary player attachment, not an older comment upload", () => {
    expect(resolve([ok(fixture("details.html"))])).toMatchObject({ filename: "korri_panda.nx" })
    expect(
      search("absent", [
        ok(
          '<h1>Programs named "absent"</h1><div class="grid"><p>No search results for "absent"</p></div>',
        ),
      ]),
    ).toEqual([])
  })
  test("requires the player's primary filename to have an offered same-host link", () => {
    const bad = fixture("details.html").replace(
      'href="uploads/korri_panda.nx"',
      'href="https://evil.invalid/korri_panda.nx"',
    )
    expect(resolve([ok(bad)])).toMatchObject({ _tag: "NonFinalDownload", reason: "unsupported" })
    expect(details([ok(bad)])).not.toHaveProperty("artifact")
    expect(details([ok(fixture("details.html"))])).toMatchObject({
      description: expect.stringContaining("By Test Author."),
    })
    expect(() =>
      search("panda", [
        ok(catalog.replace("program-info", "changed-info").replace("<h3>", "<h4>")),
      ]),
    ).toThrow()
  })
})

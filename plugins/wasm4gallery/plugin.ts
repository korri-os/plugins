import type {
  ArtifactAcquisitionHint,
  PluginDetailsInput,
  PluginDetailsOutput,
  PluginHttpRequests,
  PluginHttpResponse,
  PluginResolveDownloadInput,
  PluginResolveDownloadOutput,
  PluginSearchInput,
  PluginSearchOutput,
  ProviderClaim,
  ProviderClaimDetails,
} from "../../contracts/generated/korrid"

export const name = "wasm4gallery"
export const title = "WASM-4 Gallery"
export const description =
  "Searches the upstream WASM-4 play catalog. Runtime compatibility is untested."
const providerId = "@korri:wasm4gallery"
export const providers = { [providerId]: { id: providerId, title } }
const base = "https://wasm4.org"
interface Entry {
  id: string
  title: string
  author?: string
  license?: string
  download?: string
}
function idField(id: string): string {
  if (id.trim() !== id || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id))
    throw new Error("Invalid WASM-4 slug")
  return id
}
const pageUrl = (id: string) => `${base}/play/${id}/`
const request = (url: string): PluginHttpRequests => ({ _tag: "HttpRequests", requests: [{ url }] })
function body(response: PluginHttpResponse): string {
  if (!response.ok) throw new Error(`WASM-4 returned HTTP ${response.status}`)
  return response.text
}
function text(html: string): string {
  const named: Record<string, string> = {
    amp: "&",
    lt: "<",
    gt: ">",
    quot: '"',
    apos: "'",
    nbsp: " ",
  }
  return html
    .replace(/<[^>]*>/g, "")
    .replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (match, entity: string) => {
      if (!entity.startsWith("#")) return named[entity] ?? match
      const code =
        entity[1].toLowerCase() === "x"
          ? Number.parseInt(entity.slice(2), 16)
          : Number(entity.slice(1))
      return code <= 0x10ffff ? String.fromCodePoint(code) : match
    })
    .trim()
}
function catalog(html: string): Entry[] {
  if (!/<h1>Newest Games<\/h1>/.test(html)) throw new Error("WASM-4 catalog heading missing")
  const entries = [
    ...html.matchAll(/<div class="cart card"><a href="\/play\/([a-z0-9-]+)"[^>]*>([\s\S]*?)<\/a>/g),
  ].map(match => {
    const title = match[2].match(/<div class="avatar__name">([\s\S]*?)<\/div>/)?.[1]
    const author = match[2].match(/<small class="avatar__subtitle">([\s\S]*?)<\/small>/)?.[1]
    if (!title || !text(title)) throw new Error("WASM-4 cart title missing")
    return {
      id: idField(match[1]),
      title: text(title),
      ...(author ? { author: text(author) } : {}),
    }
  })
  if (!entries.length || entries.length !== [...html.matchAll(/<div class="cart card">/g)].length)
    throw new Error("WASM-4 catalog cards missing or malformed")
  return entries
}
function parseDetails(html: string, id: string): Entry {
  const heading = html.match(/<h1>([\s\S]*?)(?:<span\b|<\/h1>)/)?.[1]
  if (!html.includes('class="container game-container"') || !heading || !text(heading))
    throw new Error("WASM-4 game page missing")
  const download = [...html.matchAll(/<a\b[^>]*\bhref="([^"]+)"/g)]
    .map(match => match[1])
    .find(href => href === `/carts/${id}.wasm` || href === `${base}/carts/${id}.wasm`)
  const author = html.match(/<div class="avatar__name">([\s\S]*?)<\/div>/)?.[1]
  const license = html.match(/<small>License:\s*([\s\S]*?)<\/small>/)?.[1]
  return {
    id,
    title: text(heading),
    ...(author ? { author: text(author) } : {}),
    ...(license ? { license: text(license) } : {}),
    ...(download ? { download: `${base}/carts/${id}.wasm` } : {}),
  }
}
function artifact(id: string): ArtifactAcquisitionHint {
  return {
    kind: "content",
    system: "wasm4",
    format: { id: "wasm" },
    file: { name: `${id}.wasm`, extension: "wasm", mediaType: "application/wasm" },
  }
}
function claim(entry: Entry): ProviderClaim {
  return {
    _tag: "ProviderClaim",
    providerId,
    id: entry.id,
    title: entry.title,
    url: pageUrl(entry.id),
    platform: "wasm4",
    thumbnailUrl: `${base}/carts/${entry.id}.png`,
    artifact: { kind: "content", system: "wasm4", format: { id: "wasm" } },
  }
}
function details(entry: Entry): ProviderClaimDetails {
  return {
    _tag: "ProviderClaimDetails",
    providerId,
    id: entry.id,
    title: entry.title,
    url: pageUrl(entry.id),
    description: [
      "WASM-4 gallery cartridge.",
      entry.author ? `By ${entry.author}.` : "",
      entry.license
        ? `License: ${entry.license}.`
        : "Refer to the upstream page for cartridge rights.",
      "Runtime compatibility untested.",
    ]
      .filter(Boolean)
      .join(" "),
    ...(entry.download ? { downloadPageUrl: entry.download, artifact: artifact(entry.id) } : {}),
  }
}
function search(input: PluginSearchInput): PluginSearchOutput {
  const query = input.query.trim().toLowerCase()
  if (!query) return []
  const response = input.responses[0]
  if (!response) return request(`${base}/play/`)
  return catalog(body(response))
    .filter(entry => `${entry.title} ${entry.author ?? ""}`.toLowerCase().includes(query))
    .slice(0, 50)
    .map(claim)
}
function describe(input: PluginDetailsInput): PluginDetailsOutput {
  const id = idField(input.id)
  const response = input.responses[0]
  if (!response) return request(pageUrl(id))
  return details(parseDetails(body(response), id))
}
function resolve(input: PluginResolveDownloadInput): PluginResolveDownloadOutput {
  const match = /^https:\/\/wasm4\.org\/play\/([a-z0-9]+(?:-[a-z0-9]+)*)\/?$/.exec(
    input.candidateUrl,
  )
  if (!match || match[0] !== input.candidateUrl)
    return { _tag: "NonFinalDownload", providerId, reason: "unsupported", url: input.candidateUrl }
  const response = input.responses[0]
  if (!response) return request(pageUrl(match[1]))
  if (response.status === 404)
    return {
      _tag: "FailedDownload",
      providerId,
      reason: "not-found",
      message: "WASM-4 game not found",
    }
  try {
    const entry = parseDetails(body(response), match[1])
    if (!entry.download)
      return {
        _tag: "NonFinalDownload",
        providerId,
        reason: "unsupported",
        url: input.candidateUrl,
      }
    return {
      _tag: "FinalDownload",
      providerId,
      url: entry.download,
      filename: `${entry.id}.wasm`,
      contentType: "application/wasm",
    }
  } catch (error) {
    return { _tag: "FailedDownload", providerId, reason: "provider-error", message: String(error) }
  }
}
export const handlers = {
  "claims.search": search,
  "claims.details": describe,
  "artifact.resolve-download": resolve,
}

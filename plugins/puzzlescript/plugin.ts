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
} from "../../contracts/generated/korrid"

export const name = "puzzlescript"
export const title = "PuzzleScript Gallery"
export const description =
  "Searches upstream gallery data for original PuzzleScript gist sources. Runtime compatibility is untested."
const providerId = "@korri:puzzlescript"
export const providers = { [providerId]: { id: providerId, title } }
interface Entry {
  id: string
  title: string
  author: string
}
const catalogUrl = "https://www.puzzlescript.net/games_dat.js"
const pageUrl = (id: string) => `https://www.puzzlescript.net/play.html?p=${id}`
const sourceUrl = (id: string) =>
  `https://gist.githubusercontent.com/anonymous/${id}/raw/script.txt`
const request = (url: string): PluginHttpRequests => ({ _tag: "HttpRequests", requests: [{ url }] })
const gistPattern = "(?:[0-9]{7,8}|[a-f0-9]{20}|[a-f0-9]{32})"
const pagePattern = new RegExp(
  `^https://www\\.puzzlescript\\.net/play\\.html\\?p=(${gistPattern})$`,
)
function idField(id: string): string {
  if (id.trim() !== id || !new RegExp(`^${gistPattern}$`).test(id))
    throw new Error("Invalid PuzzleScript gist id")
  return id
}
function body(response: PluginHttpResponse): string {
  if (!response.ok) throw new Error(`PuzzleScript returned HTTP ${response.status}`)
  return response.text
}
// games_dat.js is observed as a single let assignment to JSON objects with
// trailing commas. Accept that inert grammar only. No eval, Function, script
// import, expression parsing, or substitutions inside quoted strings.
function inertGallery(source: string): unknown {
  const match = /^(?:\s|\/\/[^\n]*(?:\n|$))*let\s+games_gallery\s*=\s*(\[[\s\S]*\])\s*;?\s*$/.exec(
    source,
  )
  if (!match) throw new Error("PuzzleScript gallery assignment missing")
  const data = match[1]
  let json = ""
  let quoted = false
  let escaped = false
  for (let i = 0; i < data.length; i++) {
    const char = data[i]
    if (quoted) {
      json += char
      if (escaped) escaped = false
      else if (char === "\\") escaped = true
      else if (char === '"') quoted = false
      continue
    }
    if (char === '"') quoted = true
    if (char === ",") {
      let next = i + 1
      while (/\s/.test(data[next] ?? "") && next < data.length) next++
      if (data[next] === "]" || data[next] === "}") continue
    }
    json += char
  }
  return JSON.parse(json)
}
function catalog(response: PluginHttpResponse): Entry[] {
  const data = inertGallery(body(response))
  if (!Array.isArray(data)) throw new Error("Invalid PuzzleScript gallery")
  return data.flatMap((row: unknown) => {
    if (
      !row ||
      typeof row !== "object" ||
      !("url" in row) ||
      typeof row.url !== "string" ||
      !("title" in row) ||
      typeof row.title !== "string" ||
      !row.title.trim() ||
      !("author" in row) ||
      typeof row.author !== "string"
    )
      throw new Error("Invalid PuzzleScript gallery row")
    const match = pagePattern.exec(row.url)
    // The gallery also links to external sites/forks/HTML exports. They are
    // discovery exclusions, not permission to follow arbitrary creator hosts.
    return match && match[0] === row.url
      ? [{ id: match[1], title: row.title, author: row.author }]
      : []
  })
}
function artifact(id: string): ArtifactAcquisitionHint {
  return {
    kind: "content",
    system: "puzzlescript",
    format: { id: "pz" },
    file: { name: `${id}.pz`, extension: "pz", mediaType: "text/plain" },
  }
}
function isSource(response: PluginHttpResponse): boolean {
  const source = response.text
  const mediaType = response.headers["content-type"]
  return (
    response.ok &&
    (!mediaType || /^text\/plain(?:;|$)/i.test(mediaType)) &&
    !/<(?:!doctype|html|head|body|script)(?:\s|>)/i.test(source) &&
    !/^\s*</.test(source) &&
    ["objects", "legend", "collisionlayers", "rules", "winconditions", "levels"].every(section =>
      new RegExp(`^\\s*${section}\\s*$`, "im").test(source),
    )
  )
}
function search(input: PluginSearchInput): PluginSearchOutput {
  const query = input.query.trim().toLowerCase()
  if (!query) return []
  const response = input.responses[0]
  if (!response) return request(catalogUrl)
  return catalog(response)
    .filter(entry => `${entry.title} ${entry.author}`.toLowerCase().includes(query))
    .slice(0, 50)
    .map(
      (entry): ProviderClaim => ({
        _tag: "ProviderClaim",
        providerId,
        id: entry.id,
        title: entry.title,
        url: pageUrl(entry.id),
        platform: "puzzlescript",
        artifact: { kind: "content", system: "puzzlescript", format: { id: "pz" } },
      }),
    )
}
function describe(input: PluginDetailsInput): PluginDetailsOutput {
  const id = idField(input.id)
  if (!input.responses[0]) return request(catalogUrl)
  const entry = catalog(input.responses[0]).find(entry => entry.id === id)
  if (!entry) throw new Error(`Unknown PuzzleScript gallery gist: ${id}`)
  const response = input.responses[1]
  if (!response) return request(sourceUrl(id))
  if (!response.ok && response.status !== 404) body(response)
  const available = isSource(response)
  return {
    _tag: "ProviderClaimDetails",
    providerId,
    id,
    title: entry.title,
    url: pageUrl(id),
    description: `By ${entry.author}. ${available ? "Raw PuzzleScript source is available." : "No supported raw script.txt source is available."} Runtime compatibility untested; forks are not promised. Public gist visibility does not grant redistribution rights.`,
    ...(available ? { downloadPageUrl: sourceUrl(id), artifact: artifact(id) } : {}),
  }
}
function resolve(input: PluginResolveDownloadInput): PluginResolveDownloadOutput {
  const match = pagePattern.exec(input.candidateUrl)
  if (!match || match[0] !== input.candidateUrl)
    return { _tag: "NonFinalDownload", providerId, reason: "unsupported", url: input.candidateUrl }
  const id = match[1]
  if (!input.responses[0]) return request(catalogUrl)
  try {
    if (input.responses[0].status === 404)
      return {
        _tag: "FailedDownload",
        providerId,
        reason: "not-found",
        message: "PuzzleScript gallery not found",
      }
    if (!catalog(input.responses[0]).some(entry => entry.id === id))
      return {
        _tag: "FailedDownload",
        providerId,
        reason: "not-found",
        message: "Gist no longer in PuzzleScript gallery",
      }
    const response = input.responses[1]
    if (!response) return request(sourceUrl(id))
    if (response.status === 404)
      return {
        _tag: "FailedDownload",
        providerId,
        reason: "not-found",
        message: "Raw PuzzleScript source not found",
      }
    body(response)
    if (!isSource(response))
      return {
        _tag: "NonFinalDownload",
        providerId,
        reason: "unsupported",
        url: input.candidateUrl,
      }
    // Rename raw text only. Nothing extracts a script from HTML or evaluates JS.
    return {
      _tag: "FinalDownload",
      providerId,
      url: sourceUrl(id),
      filename: `${id}.pz`,
      contentType: "text/plain",
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

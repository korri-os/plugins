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

export const name = "lowresnxgallery"
export const title = "LowRes NX Programs"
export const description =
  "Searches author uploads on the LowRes NX community site. Runtime compatibility is untested."
const providerId = "@korri:lowresnxgallery"
export const providers = { [providerId]: { id: providerId, title } }
const base = "https://lowresnx.inutilis.com"
interface Entry {
  id: string
  title: string
  author?: string
  filename?: string
}
const pageUrl = (id: string) => `${base}/topic.php?id=${id}`
function idField(id: string): string {
  if (id.trim() !== id || !/^[1-9][0-9]*$/.test(id)) throw new Error("Invalid LowRes NX topic id")
  return id
}
const request = (id: string): PluginHttpRequests => ({
  _tag: "HttpRequests",
  requests: [{ url: `${base}/topic.php`, query: { id } }],
})
function body(response: PluginHttpResponse): string {
  if (!response.ok) throw new Error(`LowRes NX returned HTTP ${response.status}`)
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
function artifact(filename?: string): ArtifactAcquisitionHint {
  return {
    kind: "content",
    system: "lowresnx",
    format: { id: "nx" },
    ...(filename
      ? { file: { name: filename, extension: "nx", mediaType: "application/octet-stream" } }
      : {}),
  }
}
function parseDetails(html: string, id: string): Entry {
  const heading = html.match(/<h1>([\s\S]*?)<\/h1>/)?.[1]
  // Unknown topics must not become the site's landing page under a guessed id.
  if (
    !html.includes(`<meta property="og:url" content="${pageUrl(id)}">`) ||
    !heading ||
    !text(heading)
  )
    throw new Error("LowRes NX topic page missing")
  // The player points at the primary author attachment. Later replies can carry
  // older versions or unrelated .nx files; never pick the first arbitrary link.
  const player = html.match(/<iframe\b[^>]*\bid="player"[^>]*>/)?.[0]
  const filename = player?.match(/\bvalue="([A-Za-z0-9_-]+\.nx)"/)?.[1]
  const offered =
    filename &&
    [...html.matchAll(/<a\b[^>]*\bhref="([^"]+)"/g)].some(
      match => match[1] === `uploads/${filename}` || match[1] === `${base}/uploads/${filename}`,
    )
  const author = html.match(/<meta name="author" content="([^"]+)"/)?.[1]
  return {
    id,
    title: text(heading),
    ...(author ? { author: text(author) } : {}),
    ...(offered ? { filename } : {}),
  }
}
function search(input: PluginSearchInput): PluginSearchOutput {
  const query = input.query.trim()
  if (!query) return []
  const response = input.responses[0]
  if (!response)
    return {
      _tag: "HttpRequests",
      requests: [{ url: `${base}/programs.php`, query: { search: query } }],
    }
  const html = body(response)
  if (!/<h1>Programs named [\s\S]*?<\/h1>/.test(html) || !html.includes('class="grid"'))
    throw new Error("LowRes NX search page missing")
  const cards = [
    ...html.matchAll(
      /<div class="program">\s*<a href="topic\.php\?id=([1-9][0-9]*)">([\s\S]*?)<\/a>/g,
    ),
  ]
  if (
    cards.length !== [...html.matchAll(/<div class="program">/g)].length ||
    (!cards.length && !/<p>No search results for [\s\S]*?<\/p>/.test(html))
  )
    throw new Error("LowRes NX program cards missing or malformed")
  return cards.slice(0, 50).map((match): ProviderClaim => {
    const heading = match[2].match(/<h3>([\s\S]*?)<\/h3>/)?.[1]
    if (!heading || !text(heading)) throw new Error("LowRes NX program title missing")
    return {
      _tag: "ProviderClaim",
      providerId,
      id: match[1],
      title: text(heading),
      url: pageUrl(match[1]),
      platform: "lowresnx",
      artifact: artifact(),
    }
  })
}
function describe(input: PluginDetailsInput): PluginDetailsOutput {
  const id = idField(input.id)
  const response = input.responses[0]
  if (!response) return request(id)
  const entry = parseDetails(body(response), id)
  return {
    _tag: "ProviderClaimDetails",
    providerId,
    id,
    title: entry.title,
    url: pageUrl(id),
    description: `${entry.author ? `By ${entry.author}. ` : ""}LowRes NX community program. Runtime compatibility untested. Author upload does not establish an open-source licence.`,
    ...(entry.filename
      ? { downloadPageUrl: `${base}/uploads/${entry.filename}`, artifact: artifact(entry.filename) }
      : {}),
  }
}
function resolve(input: PluginResolveDownloadInput): PluginResolveDownloadOutput {
  const match = /^https:\/\/lowresnx\.inutilis\.com\/topic\.php\?id=([1-9][0-9]*)$/.exec(
    input.candidateUrl,
  )
  if (!match || match[0] !== input.candidateUrl)
    return { _tag: "NonFinalDownload", providerId, reason: "unsupported", url: input.candidateUrl }
  const response = input.responses[0]
  if (!response) return request(match[1])
  if (response.status === 404)
    return {
      _tag: "FailedDownload",
      providerId,
      reason: "not-found",
      message: "LowRes NX topic not found",
    }
  try {
    const entry = parseDetails(body(response), match[1])
    if (!entry.filename)
      return {
        _tag: "NonFinalDownload",
        providerId,
        reason: "unsupported",
        url: input.candidateUrl,
      }
    return {
      _tag: "FinalDownload",
      providerId,
      url: `${base}/uploads/${entry.filename}`,
      filename: entry.filename,
      contentType: "application/octet-stream",
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

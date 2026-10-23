// Public discovery/upload parsing comes from legacy @korri:itchio, revision
// 0e4cec9da3d77e6578b8a01a5d83420ba0d98e62, definition.ts. This slice only
// resolves author-offered raw .bitsy attachments on approved creator hosts.
// Unlike legacy's session path, the observed HTML-game variant exposes its
// zero prices, CSRF and uploads on the public page. No JavaScript is executed.
import type {
  ArtifactAcquisitionHint,
  DownloadChoice,
  DownloadResolution,
  PluginDetailsInput,
  PluginDetailsOutput,
  PluginHttpRequest,
  PluginHttpRequests,
  PluginHttpResponse,
  PluginResolveDownloadInput,
  PluginResolveDownloadOutput,
  PluginSearchInput,
  PluginSearchOutput,
  ProviderClaim,
  ProviderClaimDetails,
} from "../../contracts/generated/korrid"

export const name = "itchio"
export const title = "itch.io (supported Bitsy attachments)"
export const description =
  "Searches itch.io for supported creators. Only explicit free raw Bitsy attachments can be acquired; browser games and paid uploads are not supported."
const PROVIDER_ID = "@korri:itchio"
// Existing exact-host approval, not an engine-tag promise or a curated game list.
const CREATOR_HOST = "0neforgetfulbug.itch.io"
const ARTIFACT_HOST =
  "itchio-mirror.cb031a832f44726753d6267436f3b414.r2.cloudflarestorage.com"
export const providers = { [PROVIDER_ID]: { id: PROVIDER_ID, title } }

function requests(...values: PluginHttpRequest[]): PluginHttpRequests {
  return { _tag: "HttpRequests", requests: values }
}

function searchClaims(input: PluginSearchInput): PluginSearchOutput {
  const query = input.query.trim()
  if (!query) return []
  const candidate = gameUrl(query)
  if (candidate) {
    if (!supported(candidate)) return []
    if (!input.responses.length) return requests({ url: candidate.url })
    const details = pageDetails(candidate, input.responses[0])
    return [
      {
        _tag: "ProviderClaim",
        providerId: PROVIDER_ID,
        id: details.id,
        title: details.title,
        url: details.url,
        ...(details.artifact ? { artifact: details.artifact } : {}),
      },
    ]
  }
  if (/^https?:/i.test(query)) return []
  // Legacy public RSS discovery, then its real natural-language search URL.
  // An engine category's ?q is not a search endpoint.
  const normalized = query.toLowerCase().replaceAll(/\s+/g, "-")
  const feedUrl = /^[a-z0-9][a-z0-9-]*$/.test(normalized)
    ? `https://itch.io/games/${normalized === "free" ? "free" : `tag-${encodeURIComponent(normalized)}`}.xml`
    : undefined
  if (!input.responses.length)
    return feedUrl ? requests({ url: feedUrl }) : searchRequest(query)
  let entries: Entry[]
  if (feedUrl) {
    const feed = input.responses[0]
    if (feed.status !== 404) {
      checkResponse(feed, "feed")
      const parsed = rssEntries(feed.text)
      if (!parsed) throw new Error("itch.io feed markup is not recognized")
      if (parsed.length > 0) return parsed.filter(supported).map(claimFor)
    }
    if (input.responses.length === 1) return searchRequest(query)
    checkResponse(input.responses[1], "search")
    entries = searchEntries(input.responses[1].text)
  } else {
    checkResponse(input.responses[0], "search")
    entries = searchEntries(input.responses[0].text)
  }
  return entries.filter(supported).map(claimFor)
}

function searchRequest(query: string): PluginHttpRequests {
  return requests({
    url: "https://itch.io/search",
    query: { q: query, type: "games" },
  })
}

function claimDetails(input: PluginDetailsInput): PluginDetailsOutput {
  const candidate = gameUrl(`https://${input.id.replace("/", ".itch.io/")}`)
  if (!candidate || !supported(candidate) || candidate.id !== input.id)
    throw new Error("Unsupported itch.io creator or game id")
  if (!input.responses.length) return requests({ url: candidate.url })
  return pageDetails(candidate, input.responses[0])
}

function pageDetails(
  candidate: GameUrl,
  page: PluginHttpResponse,
): ProviderClaimDetails {
  checkResponse(page, "page")
  const pageTitle =
    metaContent(page.text, "og:title") ??
    cleanText(page.text.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1])
  if (!pageTitle) throw new Error("itch.io page has no title")
  const description =
    metaContent(page.text, "og:description") ??
    metaContent(page.text, "description")
  const uploads = rawUploads(page.text)
  const artifact =
    explicitlyFreeHtmlGame(page.text) &&
    csrfToken(page.text) &&
    uploads.length > 0
      ? artifactHint(uploads.length === 1 ? uploads[0].filename : undefined)
      : undefined
  return {
    _tag: "ProviderClaimDetails",
    providerId: PROVIDER_ID,
    id: candidate.id,
    title: pageTitle,
    url: candidate.url,
    ...(description ? { description } : {}),
    ...(artifact ? { artifact } : {}),
  }
}

function resolveDownload(
  input: PluginResolveDownloadInput,
): PluginResolveDownloadOutput {
  const candidate = gameUrl(input.candidateUrl)
  if (!candidate || !supported(candidate)) return nonFinal("unsupported")
  if (!input.responses.length) return requests({ url: candidate.url })
  const page = input.responses[0]
  if (!page.ok) return upstreamFailure(page)
  // Missing data.json prices are not free. These numeric prices are the
  // existing public init_ViewHtmlGame JSON, observed on the author's page.
  if (!explicitlyFreeHtmlGame(page.text))
    return nonFinal("requires-user-action")
  const csrf = csrfToken(page.text)
  const uploads = rawUploads(page.text)
  if (!csrf) return nonFinal("requires-user-action")
  const matching = input.fileName
    ? uploads.filter(
        (upload) =>
          upload.filename.toLowerCase() ===
          input.fileName?.trim().toLowerCase(),
      )
    : uploads
  const upload = matching.length === 1 ? matching[0] : undefined
  if (!upload)
    return nonFinal(
      "requires-user-action",
      uploads.map(({ id, filename }) => ({ id, fileName: filename })),
    )
  if (input.responses.length === 1)
    return requests({
      url: `${candidate.url}/file/${upload.id}`,
      query: {
        source: "view_game",
        as_props: "1",
        after_download_lightbox: "true",
      },
      method: "POST",
      body: { csrf_token: csrf },
    })
  const file = input.responses[1]
  if (!file.ok) return upstreamFailure(file)
  const value = record(parseJson(file.text))
  if (typeof value?.url !== "string" || !artifactUrl(value.url))
    return nonFinal("requires-user-action")
  return {
    _tag: "FinalDownload",
    providerId: PROVIDER_ID,
    url: value.url,
    filename: upload.filename,
  }
}

export const handlers = {
  "claims.search": searchClaims,
  "claims.details": claimDetails,
  "artifact.resolve-download": resolveDownload,
}

function artifactHint(filename?: string): ArtifactAcquisitionHint {
  return {
    kind: "content",
    system: "bitsy",
    format: { id: "bitsy" },
    ...(filename ? { file: { name: filename, extension: "bitsy" } } : {}),
  }
}
function nonFinal(
  reason: "unsupported" | "requires-user-action",
  choices?: DownloadChoice[],
): DownloadResolution {
  return {
    _tag: "NonFinalDownload",
    providerId: PROVIDER_ID,
    reason,
    ...(choices?.length ? { choices } : {}),
  }
}
function upstreamFailure(response: PluginHttpResponse): DownloadResolution {
  return {
    _tag: "FailedDownload",
    providerId: PROVIDER_ID,
    reason: response.status === 404 ? "not-found" : "provider-error",
    message: `itch.io returned HTTP ${response.status}`,
  }
}
function checkResponse(response: PluginHttpResponse, context: string): void {
  if (!response.ok)
    throw new Error(`itch.io ${context} returned HTTP ${response.status}`)
}

// Strict literal URLs: the sandbox has no URL global. Never interpolate an
// arbitrary candidate, upload id or search query into executable source/path.
interface GameUrl {
  readonly id: string
  readonly url: string
  readonly host: string
}
function gameUrl(input: string): GameUrl | undefined {
  const match =
    /^https:\/\/([a-z0-9][a-z0-9-]*)\.itch\.io\/([a-z0-9][a-z0-9-]*)\/?$/.exec(
      input,
    )
  if (!match) return undefined
  return {
    id: `${match[1]}/${match[2]}`,
    host: `${match[1]}.itch.io`,
    url: `https://${match[1]}.itch.io/${match[2]}`,
  }
}
function supported(candidate: GameUrl): boolean {
  return candidate.host === CREATOR_HOST
}
function artifactUrl(input: string): boolean {
  const match = /^https:\/\/([^/?#]+)(\/[^\s"'<>\\]*)$/.exec(input)
  return match?.[1] === ARTIFACT_HOST
}

// Legacy public feed and search-row parsers. Listings do not establish the
// attachment format; details() re-holds the verified artifact in korrid.
interface Entry extends GameUrl {
  readonly title: string
  readonly thumbnailUrl?: string
}
function claimFor(entry: Entry): ProviderClaim {
  return {
    _tag: "ProviderClaim",
    providerId: PROVIDER_ID,
    id: entry.id,
    title: entry.title,
    url: entry.url,
    ...(entry.thumbnailUrl ? { thumbnailUrl: entry.thumbnailUrl } : {}),
  }
}
function rssEntries(xml: string): Entry[] | undefined {
  if (!/<rss\b/i.test(xml) || !/<channel\b/i.test(xml)) return undefined
  const items = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/gi)]
  const entries = items.flatMap((match) => {
    const item = match[1]
    const candidate = gameUrl(
      elementText(item, "link") ?? elementText(item, "guid") ?? "",
    )
    const title = elementText(item, "plainTitle") ?? elementText(item, "title")
    return candidate && title ? [{ ...candidate, title }] : []
  })
  if (items.length > 0 && entries.length === 0)
    throw new Error("itch.io feed markup is not recognized")
  return entries
}
function searchEntries(html: string): Entry[] {
  if (!/\bgame_cell\b/.test(html)) {
    if (/No results found|\bno_results\b/i.test(html)) return []
    throw new Error("itch.io search markup is not recognized")
  }
  const entries = html
    .split(/(?=<div\s+[^>]*class=["'][^"']*\bgame_cell\b)/gi)
    .flatMap((cell) => {
      for (const link of cell.matchAll(/<a\s+[^>]*>[\s\S]*?<\/a>/gi)) {
        const attributes = attributesFor(
          link[0].match(/^<a\s+[^>]*>/i)?.[0] ?? "",
        )
        if (!classes(attributes).includes("title")) continue
        const candidate = gameUrl(attributes.get("href") ?? "")
        const title = cleanText(link[0])
        if (candidate && title) return [{ ...candidate, title }]
      }
      return []
    })
  if (entries.length === 0)
    throw new Error("itch.io search markup is not recognized")
  return entries
}
function elementText(xml: string, tag: string): string | undefined {
  const text = xml.match(
    new RegExp(`<${tag}>([\\s\\S]*?)<\\/${tag}>`, "i"),
  )?.[1]
  return text
    ? cleanText(text.replace(/^<!\[CDATA\[/, "").replace(/\]\]>$/, ""))
    : undefined
}

// JSON.parse only. Never eval the page's init call, browser export or scripts.
function explicitlyFreeHtmlGame(html: string): boolean {
  const calls = [...html.matchAll(/\binit_ViewHtmlGame\s*\(/g)]
  if (calls.length !== 1) return false
  const start = html.indexOf("{", (calls[0].index ?? 0) + calls[0][0].length)
  if (start < 0) return false
  const value = record(parseJson(jsonObjectAt(html, start)))
  const game = record(value?.game)
  return (
    game?.actual_price === 0 &&
    game.min_price === 0 &&
    game.type === 5 &&
    game.type_name === "html" &&
    typeof game.id === "number" &&
    Number.isSafeInteger(game.id) &&
    game.id > 0
  )
}
function jsonObjectAt(text: string, start: number): string {
  let depth = 0
  let quoted = false
  let escaped = false
  for (let index = start; index < text.length; index += 1) {
    const char = text[index]
    if (quoted) {
      if (escaped) escaped = false
      else if (char === "\\") escaped = true
      else if (char === '"') quoted = false
    } else if (char === '"') quoted = true
    else if (char === "{") depth += 1
    else if (char === "}" && --depth === 0) return text.slice(start, index + 1)
  }
  return ""
}
function parseJson(text: string): unknown {
  try {
    return JSON.parse(text) as unknown
  } catch {
    return undefined
  }
}
function record(value: unknown): Record<string, unknown> | undefined {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined
}

interface Upload {
  readonly id: string
  readonly filename: string
}
function rawUploads(html: string): Upload[] {
  return [
    ...html.matchAll(
      /<div\s+[^>]*class=["'][^"']*\bupload\b[^"']*["'][\s\S]*?<\/div>\s*<\/div>/gi,
    ),
  ].flatMap((match) => {
    const upload = match[0]
    const controls = [...upload.matchAll(/<a\s+[^>]*>/gi)]
      .map((tag) => attributesFor(tag[0]))
      .filter((attributes) => classes(attributes).includes("download_btn"))
    if (controls.length !== 1) return []
    const id = controls[0].get("data-upload_id")
    const filename = [
      ...upload.matchAll(/<strong\b[^>]*>[\s\S]*?<\/strong>/gi),
    ].flatMap((tag) => {
      const attributes = attributesFor(
        tag[0].match(/^<strong\b[^>]*>/i)?.[0] ?? "",
      )
      const text = cleanText(tag[0])
      return classes(attributes).includes("name") && text ? [text] : []
    })
    if (
      !id ||
      !/^\d+$/.test(id) ||
      filename.length !== 1 ||
      !/^[^/\\\x00-\x1f\x7f]+\.bitsy$/i.test(filename[0])
    )
      return []
    return [{ id, filename: filename[0] }]
  })
}
function csrfToken(html: string): string | undefined {
  for (const tag of html.matchAll(/<meta\s+[^>]*>/gi)) {
    const attributes = attributesFor(tag[0])
    if (attributes.get("name") === "csrf_token")
      return attributes.get("value") || undefined
  }
  return undefined
}
function metaContent(html: string, name: string): string | undefined {
  for (const tag of html.matchAll(/<meta\s+[^>]*>/gi)) {
    const attributes = attributesFor(tag[0])
    if ((attributes.get("property") ?? attributes.get("name")) === name)
      return cleanText(attributes.get("content"))
  }
  return undefined
}
function attributesFor(tag: string): Map<string, string> {
  return new Map(
    [
      ...tag.matchAll(/([a-z_:][a-z0-9_:.-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')/gi),
    ].map((match) => [
      match[1].toLowerCase(),
      decodeHtml(match[2] ?? match[3]),
    ]),
  )
}
function classes(attributes: Map<string, string>): string[] {
  return (attributes.get("class") ?? "").split(/\s+/)
}
function cleanText(value: string | undefined): string | undefined {
  const text = value ? decodeHtml(value.replaceAll(/<[^>]*>/g, "")).trim() : ""
  return text || undefined
}
function decodeHtml(value: string): string {
  const named: Record<string, string> = {
    amp: "&",
    gt: ">",
    lt: "<",
    quot: '"',
    apos: "'",
    nbsp: " ",
  }
  const point = (match: string, number: number) =>
    number <= 0x10ffff ? String.fromCodePoint(number) : match
  return value
    .replaceAll(/&#(\d+);/g, (match, code: string) =>
      point(match, Number(code)),
    )
    .replaceAll(/&#x([0-9a-f]+);/gi, (match, code: string) =>
      point(match, Number.parseInt(code, 16)),
    )
    .replaceAll(/&([a-z]+);/gi, (match, name: string) => named[name] ?? match)
}

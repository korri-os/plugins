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

export const name = "tic80gallery"
export const title = "TIC-80 Gallery"
export const description =
  "Searches TIC-80's bounded Play/Games directory. Runtime compatibility is untested."
const providerId = "@korri:tic80gallery"
export const providers = { [providerId]: { id: providerId, title } }

interface Cart {
  id: string
  title: string
  filename: string
  url: string
  lang: string
}
const pageUrl = (id: string) => `https://tic80.com/play?cart=${id}`
const request = (): PluginHttpRequests => ({
  _tag: "HttpRequests",
  requests: [{ url: "https://tic80.com/json", query: { fn: "dir", path: "Play/Games" } }],
})
function idField(id: string): string {
  if (id.trim() !== id || !/^[1-9][0-9]*$/.test(id)) throw new Error("Invalid TIC-80 cart id")
  return id
}
function catalog(response: PluginHttpResponse): Cart[] {
  if (!response.ok) throw new Error(`TIC-80 directory returned HTTP ${response.status}`)
  const data: unknown = JSON.parse(response.text)
  if (!data || typeof data !== "object" || !("files" in data) || !Array.isArray(data.files)) {
    throw new Error("Invalid TIC-80 directory")
  }
  return data.files.map((row: unknown) => {
    if (
      !row ||
      typeof row !== "object" ||
      !("id" in row) ||
      !Number.isSafeInteger(row.id) ||
      Number(row.id) <= 0 ||
      !("name" in row) ||
      typeof row.name !== "string" ||
      !row.name.trim() ||
      !("hash" in row) ||
      typeof row.hash !== "string" ||
      row.hash.length !== 32 ||
      !/^[a-f0-9]{32}$/.test(row.hash) ||
      !("filename" in row) ||
      typeof row.filename !== "string" ||
      row.filename.trim() !== row.filename ||
      !/^[A-Za-z0-9_-]+\.tic$/.test(row.filename) ||
      !("lang" in row) ||
      typeof row.lang !== "string"
    )
      throw new Error("Invalid TIC-80 cart row")
    return {
      id: String(row.id),
      title: row.name.replace(/\.tic$/, ""),
      filename: row.filename,
      url: `https://tic80.com/cart/${row.hash}/${row.filename}`,
      lang: row.lang,
    }
  })
}
function artifact(cart: Cart): ArtifactAcquisitionHint {
  return {
    kind: "content",
    system: "tic80",
    format: { id: "tic" },
    file: { name: cart.filename, extension: "tic", mediaType: "application/octet-stream" },
  }
}
function claim(cart: Cart): ProviderClaim {
  return {
    _tag: "ProviderClaim",
    providerId,
    id: cart.id,
    title: cart.title,
    url: pageUrl(cart.id),
    platform: "tic80",
    artifact: artifact(cart),
  }
}
function details(cart: Cart): ProviderClaimDetails {
  return {
    _tag: "ProviderClaimDetails",
    providerId,
    id: cart.id,
    title: cart.title,
    url: pageUrl(cart.id),
    description: `TIC-80 Play/Games cartridge. Language: ${cart.lang}. Runtime compatibility untested. Cartridge rights remain with its author.`,
    downloadPageUrl: cart.url,
    artifact: artifact(cart),
  }
}
function search(input: PluginSearchInput): PluginSearchOutput {
  const query = input.query.trim().toLowerCase()
  if (!query) return []
  const response = input.responses[0]
  if (!response) return request()
  return catalog(response)
    .filter(cart => `${cart.title} ${cart.filename}`.toLowerCase().includes(query))
    .slice(0, 50)
    .map(claim)
}
function describe(input: PluginDetailsInput): PluginDetailsOutput {
  const id = idField(input.id)
  const response = input.responses[0]
  if (!response) return request()
  const cart = catalog(response).find(cart => cart.id === id)
  if (!cart) throw new Error(`Unknown TIC-80 cart: ${id}`)
  return details(cart)
}
function resolve(input: PluginResolveDownloadInput): PluginResolveDownloadOutput {
  const match = /^https:\/\/tic80\.com\/play\?cart=([1-9][0-9]*)$/.exec(input.candidateUrl)
  if (!match || match[0] !== input.candidateUrl)
    return { _tag: "NonFinalDownload", providerId, reason: "unsupported", url: input.candidateUrl }
  const response = input.responses[0]
  if (!response) return request()
  if (response.status === 404)
    return {
      _tag: "FailedDownload",
      providerId,
      reason: "not-found",
      message: "TIC-80 directory not found",
    }
  try {
    const cart = catalog(response).find(cart => cart.id === match[1])
    if (!cart)
      return {
        _tag: "FailedDownload",
        providerId,
        reason: "not-found",
        message: "Cart no longer in TIC-80 Play/Games",
      }
    return {
      _tag: "FinalDownload",
      providerId,
      url: cart.url,
      filename: cart.filename,
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

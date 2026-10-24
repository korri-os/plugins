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

// Separate from the native pyxel runner, following tic80gallery/wasm4gallery.
export const name = "pyxelgallery"
export const title = "Pyxel Official Examples"
export const description =
  "Searches only the official v2.9.9 example apps, not external showcases. Runtime compatibility is untested."
const providerId = "@korri:pyxelgallery"
export const providers = { [providerId]: { id: providerId, title } }
const path = "python/pyxel/examples/apps"
const ref = "v2.9.9"
const htmlBase = `https://github.com/kitao/pyxel/blob/${ref}/${path}/`
const rawBase = `https://raw.githubusercontent.com/kitao/pyxel/${ref}/${path}/`
interface Entry {
  id: string
  title: string
  bytes: number
}
function idField(id: string): string {
  if (id.trim() !== id || !/^[A-Za-z0-9_-]+\.pyxapp$/.test(id))
    throw new Error("Invalid official Pyxel app filename")
  return id
}
const request = (): PluginHttpRequests => ({
  _tag: "HttpRequests",
  requests: [
    {
      url: `https://api.github.com/repos/kitao/pyxel/contents/${path}`,
      query: { ref },
      headers: { accept: "application/vnd.github+json" },
    },
  ],
})
function catalog(response: PluginHttpResponse): Entry[] {
  if (!response.ok) throw new Error(`Pyxel GitHub contents returned HTTP ${response.status}`)
  const data: unknown = JSON.parse(response.text)
  if (!Array.isArray(data)) throw new Error("Invalid Pyxel contents catalog")
  return data.flatMap((row: unknown) => {
    if (
      !row ||
      typeof row !== "object" ||
      !("type" in row) ||
      typeof row.type !== "string" ||
      !("name" in row) ||
      typeof row.name !== "string"
    )
      throw new Error("Invalid Pyxel contents row")
    if (row.type !== "file" || !row.name.endsWith(".pyxapp")) return []
    const id = idField(row.name)
    if (
      !("path" in row) ||
      row.path !== `${path}/${id}` ||
      !("html_url" in row) ||
      row.html_url !== `${htmlBase}${id}` ||
      !("download_url" in row) ||
      row.download_url !== `${rawBase}${id}` ||
      !("size" in row) ||
      !Number.isSafeInteger(row.size) ||
      Number(row.size) <= 0
    )
      throw new Error("Invalid official Pyxel app metadata")
    return [
      { id, title: id.replace(/\.pyxapp$/, "").replace(/[_-]/g, " "), bytes: Number(row.size) },
    ]
  })
}
function artifact(entry: Entry): ArtifactAcquisitionHint {
  return {
    kind: "content",
    system: "pyxel",
    format: { id: "pyxapp" },
    file: {
      name: entry.id,
      extension: "pyxapp",
      mediaType: "application/octet-stream",
      sizeBytes: entry.bytes,
    },
  }
}
function search(input: PluginSearchInput): PluginSearchOutput {
  const query = input.query.trim().toLowerCase()
  if (!query) return []
  const response = input.responses[0]
  if (!response) return request()
  return catalog(response)
    .filter(entry => `${entry.title} ${entry.id}`.toLowerCase().includes(query))
    .slice(0, 50)
    .map(
      (entry): ProviderClaim => ({
        _tag: "ProviderClaim",
        providerId,
        id: entry.id,
        title: entry.title,
        url: `${htmlBase}${entry.id}`,
        platform: "pyxel",
        artifact: artifact(entry),
      }),
    )
}
function describe(input: PluginDetailsInput): PluginDetailsOutput {
  const id = idField(input.id)
  const response = input.responses[0]
  if (!response) return request()
  const entry = catalog(response).find(entry => entry.id === id)
  if (!entry) throw new Error(`Unknown official Pyxel app: ${id}`)
  return {
    _tag: "ProviderClaimDetails",
    providerId,
    id,
    title: entry.title,
    url: `${htmlBase}${id}`,
    description: `Official Pyxel ${ref} example app (${entry.id}, ${entry.bytes} bytes). Title is derived from its upstream filename. Native .pyxapp acquisition requires Core's byte-evidence native-container handling. Runtime compatibility and dependencies are untested. Python executes with the native game's permissions; review and trust the author code before running. Refer to the app's own licence, not the engine licence.`,
    downloadPageUrl: `${rawBase}${id}`,
    artifact: artifact(entry),
  }
}
function resolve(input: PluginResolveDownloadInput): PluginResolveDownloadOutput {
  const match =
    /^https:\/\/github\.com\/kitao\/pyxel\/blob\/v2\.9\.9\/python\/pyxel\/examples\/apps\/([A-Za-z0-9_-]+\.pyxapp)$/.exec(
      input.candidateUrl,
    )
  if (!match || match[0] !== input.candidateUrl)
    return { _tag: "NonFinalDownload", providerId, reason: "unsupported", url: input.candidateUrl }
  const response = input.responses[0]
  if (!response) return request()
  if (response.status === 404)
    return {
      _tag: "FailedDownload",
      providerId,
      reason: "not-found",
      message: "Official Pyxel catalog not found",
    }
  try {
    const entry = catalog(response).find(entry => entry.id === match[1])
    if (!entry)
      return {
        _tag: "FailedDownload",
        providerId,
        reason: "not-found",
        message: "App not in official Pyxel catalog",
      }
    return {
      _tag: "FinalDownload",
      providerId,
      url: `${rawBase}${entry.id}`,
      filename: entry.id,
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

#!/usr/bin/env -S nix shell nixpkgs#bun --command bun
// Opt-in cohort probe. This file and its imports are never packaged.
// --live replays pure turns in Bun (transport/parser smoke, NOT Core acceptance).
// --rpc uses a separately started, approved local Core instance. --acquire
// additionally imports one cart into that instance. Nothing launches a game.
import { createHash } from "node:crypto"
import type {
  DownloadResolution,
  PluginHttpRequest,
  PluginHttpRequests,
  PluginHttpResponse,
  ProviderClaim,
  ProviderClaimDetails,
  RpcRequest,
} from "../../contracts/generated/korrid"
import { handlers as tic80 } from "./plugin"
import { handlers as wasm4 } from "../wasm4gallery/plugin"
import { handlers as lowresnx } from "../lowresnxgallery/plugin"
import { handlers as puzzlescript } from "../puzzlescript/plugin"
import { handlers as pyxel } from "../pyxelgallery/plugin"

const sources = {
  tic80gallery: { handlers: tic80, query: "panda", id: "188", hosts: ["tic80.com"] },
  wasm4gallery: { handlers: wasm4, query: "snake", id: "snake", hosts: ["wasm4.org"] },
  lowresnxgallery: {
    handlers: lowresnx,
    query: "burger",
    id: "3873",
    hosts: ["lowresnx.inutilis.com"],
  },
  puzzlescript: {
    handlers: puzzlescript,
    query: "atlas shrank",
    id: "6994394",
    hosts: ["www.puzzlescript.net", "gist.githubusercontent.com"],
  },
  pyxelgallery: {
    handlers: pyxel,
    query: "space rescue",
    id: "space_rescue.pyxapp",
    hosts: ["api.github.com", "raw.githubusercontent.com"],
  },
}
const args = process.argv.slice(2)
const selected = args.find(arg => Object.hasOwn(sources, arg))
if (!selected || (!args.includes("--live") && !args.includes("--rpc"))) {
  throw new Error(
    "Usage: bun plugins/tic80gallery/live-probe.ts <tic80gallery|wasm4gallery|lowresnxgallery|puzzlescript|pyxelgallery> <--live|--rpc> [--acquire --isolated]",
  )
}
function sourceFor(name: string) {
  if (name === "tic80gallery") return sources.tic80gallery
  if (name === "wasm4gallery") return sources.wasm4gallery
  if (name === "lowresnxgallery") return sources.lowresnxgallery
  if (name === "puzzlescript") return sources.puzzlescript
  if (name === "pyxelgallery") return sources.pyxelgallery
  throw new Error("Unknown provider")
}
const source = sourceFor(selected)
const providerId = `@korri:${selected}`
const log = (message: string) => console.log(`${new Date().toISOString()} ${providerId} ${message}`)

async function get(
  url: URL,
  headers: Record<string, string> = {},
): Promise<{ response: Response; bytes: Uint8Array }> {
  for (let hop = 0; hop <= 5; hop++) {
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      url.port ||
      !source.hosts.includes(url.hostname)
    )
      throw new Error("Unapproved probe URL")
    const response = await fetch(url, {
      redirect: "manual",
      headers: { "user-agent": "Korri-provider-probe", ...headers },
      signal: AbortSignal.timeout(30_000),
    })
    if ([301, 302, 303, 307, 308].includes(response.status)) {
      await response.body?.cancel()
      const location = response.headers.get("location")
      if (!location) throw new Error("Redirect has no location")
      url = new URL(location, url)
      continue
    }
    const chunks: Uint8Array[] = []
    let size = 0
    const reader = response.body?.getReader()
    if (reader) {
      for (;;) {
        const chunk = await reader.read()
        if (chunk.done) break
        size += chunk.value.length
        if (size > 512 * 1024) {
          await reader.cancel()
          throw new Error("Probe response exceeds Core's 512 KiB text bound")
        }
        chunks.push(chunk.value)
      }
    }
    const bytes = new Uint8Array(size)
    let offset = 0
    for (const chunk of chunks) {
      bytes.set(chunk, offset)
      offset += chunk.length
    }
    log(`GET ${url} -> ${response.status} ${size} bytes`)
    return { response, bytes }
  }
  throw new Error("Too many redirects")
}
async function fetchTurn(request: PluginHttpRequest): Promise<PluginHttpResponse> {
  if (request.method || request.body) throw new Error("This cohort expects GET turns only")
  const url = new URL(request.url)
  for (const [key, value] of Object.entries(request.query ?? {}))
    url.searchParams.set(key, String(value))
  const { response, bytes } = await get(url, request.headers)
  return {
    status: response.status,
    ok: response.ok,
    url: response.url || url.href,
    headers: Object.fromEntries(response.headers),
    text: new TextDecoder().decode(bytes),
  }
}
function isRequests(value: unknown): value is PluginHttpRequests {
  return record(value) && value._tag === "HttpRequests"
}
async function turns<Result>(
  call: (responses: PluginHttpResponse[]) => PluginHttpRequests | Result,
): Promise<Result> {
  const responses: PluginHttpResponse[] = []
  for (let i = 0; i < 4; i++) {
    const result = call(responses)
    if (!isRequests(result)) return result
    if (result.requests.length > 8) throw new Error("Request budget exceeded")
    for (const request of result.requests) responses.push(await fetchTurn(request))
  }
  throw new Error("Turn budget exceeded")
}
function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

async function rpc(request: RpcRequest): Promise<unknown> {
  const endpoint = process.env.KORRI_PROBE_RPC
  const token = process.env.KORRI_PROBE_CAPABILITY
  if (!endpoint || !/^http:\/\/127\.0\.0\.1:[0-9]+\/rpc$/.test(endpoint) || !token)
    throw new Error(
      "Set KORRI_PROBE_RPC=http://127.0.0.1:<port>/rpc and KORRI_PROBE_CAPABILITY for the isolated instance",
    )
  const response = await fetch(endpoint, {
    method: "POST",
    redirect: "error",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${token}`,
      ...(process.env.KORRI_PROBE_ORIGIN ? { origin: process.env.KORRI_PROBE_ORIGIN } : {}),
    },
    body: JSON.stringify(request),
    signal: AbortSignal.timeout(120_000),
  })
  const decoded: unknown = await response.json()
  if (
    !response.ok ||
    !record(decoded) ||
    decoded._tag !== request._tag ||
    !record(decoded.outcome) ||
    decoded.outcome._tag !== "Ok"
  )
    throw new Error(`Core RPC failed: ${request._tag}`)
  return decoded.outcome.payload
}

if (args.includes("--rpc")) {
  const listed = await rpc({ _tag: "app.acquisition.providers", payload: {} })
  if (
    !record(listed) ||
    !Array.isArray(listed.providers) ||
    !listed.providers.some(item => record(item) && item.id === providerId)
  )
    throw new Error("Provider is not enabled in Core")
  const found = await rpc({
    _tag: "app.acquisition.search",
    payload: { query: source.query, providerIds: [providerId] },
  })
  if (
    !record(found) ||
    !Array.isArray(found.claims) ||
    !found.claims.some(item => record(item) && item.id === source.id)
  )
    throw new Error("Core search missed acceptance specimen")
  const details = await rpc({
    _tag: "app.acquisition.details",
    payload: { providerId, id: source.id },
  })
  if (!record(details) || details.id !== source.id || !record(details.artifact))
    throw new Error("Core details has no supported artifact")
  log(`Core search/details passed for ${source.id}`)
  if (args.includes("--acquire")) {
    if (!args.includes("--isolated"))
      throw new Error(
        "--acquire requires --isolated: approve import into a disposable Core instance, never shared data",
      )
    const started = await rpc({
      _tag: "app.acquisition.acquire",
      payload: { providerId, id: source.id },
    })
    if (!record(started) || typeof started.jobId !== "string")
      throw new Error("Core did not return an acquire job")
    log(`Core acquisition started job ${started.jobId}`)
    const deadline = Date.now() + 120_000
    let imported = false
    while (Date.now() < deadline) {
      const status = await rpc({
        _tag: "app.acquisition.acquire-status",
        payload: { jobId: started.jobId },
      })
      if (!record(status) || !record(status.state)) throw new Error("Invalid Core acquire status")
      if (status.state._tag === "Imported") {
        log(`Core imported ${String(status.state.gameId)}; no game was executed`)
        imported = true
        break
      }
      if (status.state._tag === "Failed" || status.state._tag === "Cancelled")
        throw new Error(`Core acquisition ${JSON.stringify(status.state)}`)
      await Bun.sleep(250)
    }
    if (!imported)
      throw new Error(
        `Core job ${started.jobId} exceeded probe deadline; inspect or cancel explicitly`,
      )
  }
} else {
  if (args.includes("--acquire")) throw new Error("--acquire needs --rpc")
  const claims = await turns<ProviderClaim[]>(responses =>
    source.handlers["claims.search"]({ providerId, query: source.query, responses }),
  )
  const claim = claims.find(item => item.id === source.id)
  if (!claim) throw new Error("Live upstream search missed acceptance specimen")
  log(`search returned ${claims.length} claims; specimen ${claim.id} ${claim.title}`)
  const empty = await turns<ProviderClaim[]>(responses =>
    source.handlers["claims.search"]({ providerId, query: "zzqxjvkw", responses }),
  )
  if (empty.length) throw new Error("Expected no results for probe's unmatched query")
  const details = await turns<ProviderClaimDetails>(responses =>
    source.handlers["claims.details"]({ providerId, id: claim.id, responses }),
  )
  if (!details.artifact?.file) throw new Error("Live details has no supported file")
  const resolution = await turns<DownloadResolution>(responses =>
    source.handlers["artifact.resolve-download"]({
      providerId,
      candidateUrl: claim.url,
      responses,
    }),
  )
  if (resolution._tag !== "FinalDownload") throw new Error(`Live resolution was ${resolution._tag}`)
  const { response, bytes } = await get(new URL(resolution.url))
  if (!response.ok || !bytes.length) throw new Error("Cart download failed")
  const hex = Buffer.from(bytes.subarray(0, 4)).toString("hex")
  if (selected === "wasm4gallery" && hex !== "0061736d") throw new Error("Not WASM bytes")
  if (selected === "pyxelgallery" && hex !== "504b0304")
    throw new Error("Not native Pyxel ZIP bytes")
  log(
    `resolved ${resolution.filename}: ${bytes.length} bytes sha256=${createHash("sha256").update(bytes).digest("hex")}; not executed, not imported`,
  )
  if (selected === "pyxelgallery") {
    const first = source.handlers["claims.search"]({ providerId, query: ".pyxapp", responses: [] })
    if (!isRequests(first)) throw new Error("Expected official catalog request")
    const catalog = await fetchTurn(first.requests[0])
    const all = source.handlers["claims.search"]({
      providerId,
      query: ".pyxapp",
      responses: [catalog],
    })
    if (!Array.isArray(all) || all.length !== 7)
      throw new Error(
        "Official example catalog no longer has the seven observed apps; review scope",
      )
    for (const app of all) {
      const detail = source.handlers["claims.details"]({
        providerId,
        id: app.id,
        responses: [catalog],
      })
      const download = source.handlers["artifact.resolve-download"]({
        providerId,
        candidateUrl: app.url,
        responses: [catalog],
      })
      if (
        detail._tag !== "ProviderClaimDetails" ||
        detail.artifact?.file?.name !== app.id ||
        download._tag !== "FinalDownload" ||
        download.filename !== app.id
      )
        throw new Error(`Official app metadata did not resolve: ${app.id}`)
    }
    log(
      `all seven official app rows passed discovery/details/download resolution: ${all.map(app => app.id).join(", ")}; only Space Rescue bytes were downloaded`,
    )
  }
  log("transport/parser smoke passed; Core --rpc --acquire acceptance is separate")
}

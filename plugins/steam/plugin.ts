import type {
  PluginLaunchInput,
  PluginLaunchOutput,
  ReleaseDiscoveryInput,
  ProviderRefReleaseObservation,
} from "../../contracts/generated/korrid"

export const name = "steam"
export const title = "Steam"
export const description = "Runs Steam content through the native session program."

// This plugin's id. Declarations use full ids, as the published @korri:fex
// and @korri:proton do. A sideloaded test build under another publisher
// rewrites this one string in its scratch copy; the repository keeps @korri.
const PLUGIN_ID = "@korri:steam"

export const discovery = [
  { id: `${PLUGIN_ID}/installed-apps`, title: "Steam installed apps" },
]

export const systems = {
  steam: { title: "Steam" },
}

// Korri ADR 0083: this plugin is also the Steam provider, under its own id.
// korrid serves its search and listing from korri-steam-host's `list-apps`
// for the current person, and runs Get and Remove download as host jobs.

// Korri ADR 0083: Valve's engine package, by its fixed name on Valve's update
// servers and its `sha2vz`, for the pinned client 1792618285 (steamdeck_stable
// linuxarm64; the package's linuxarm64/steamclient.so has sha256
// 33ae8d62d122d1fb6a653598259beed34117d09ca4ce87a1d6e31a9af3eb170e). The name
// ends in the file's size. korrid recognises the VZ format and unpacks it
// itself; the runner uses only linuxarm64/steamclient.so. Grounding: the
// spike's results/pin-age (engines.tsv, retention.tsv: HTTP 200, sha2vz
// verified) and results/min-home/pkg-contents.txt.
/** This plugin's engine artifact, by its local key. */
const ENGINE_PACKAGE_KEY = "engine-package"
const ENGINE_PACKAGE =
  "bins_sdk_linuxarm64_linuxarm64.zip.vz.1424aaa33c34c7aa1b6f356fcda3678c210a62d6_10044409"
// korri#589: Valve's `legacycompat/` folder (steamclient.dll,
// steamclient64.dll, Steam.dll, ...), which Proton copies into every prefix
// from the Steam folder. A Steamworks game loads that steamclient(64).dll, and
// Proton points its exports at lsteamclient and the engine's steamclient.so.
// The engine package does not ship it; Valve's `bins_misc_linuxarm64` package
// of the same manifest (`steam_client_steamdeck_stable_linuxarm64`, version
// 1792618285) does, by name and `sha2vz`. Its legacycompat entries are links,
// which korrid's own reader refuses, so the plugin's unpack program writes the
// folder.
const LEGACYCOMPAT_KEY = "legacycompat"
const LEGACYCOMPAT_PACKAGE =
  "bins_misc_linuxarm64.zip.vz.c1fe69f2ddbbfd3d89ae14f20185fcf878df5cc8_19812282"
export const artifacts = {
  "engine-package": {
    id: `${PLUGIN_ID}/engine-package`,
    title: "Steam engine (Valve)",
    platforms: {
      "aarch64-linux": {
        version: "1792618285",
        files: [
          {
            url: `https://client-update.steamstatic.com/${ENGINE_PACKAGE}`,
            sha256: "sha256:e043d05b4e7bcc43e22cc2be3e8872ed1132e79e989cbbe181eb3a5d3f849df7",
            bytes: 10044409,
          },
        ],
      },
    },
  },
  legacycompat: {
    id: `${PLUGIN_ID}/${LEGACYCOMPAT_KEY}`,
    title: "Steam Windows client files (Valve)",
    platforms: {
      "aarch64-linux": {
        version: "1792618285",
        files: [
          {
            url: `https://client-update.steamstatic.com/${LEGACYCOMPAT_PACKAGE}`,
            sha256: "sha256:8888138451bc088adb1ce222a22d63214c1d3b249a06604c844634dfd9a004b3",
            bytes: 19812282,
          },
        ],
      },
    },
    unpack: "steam-legacycompat-unpack",
  },
}

export const runners = {
  steam: {
    program: "steam-session",
    systems: ["steam"],
    steps: [
      { key: "start-steam", label: "Starting Steam" },
      { key: "update", label: "Updating Steam" },
      { key: "sign-in", label: "Signing in" },
      { key: "install", label: "Installing the game" },
      { key: "answer", label: "Waiting for your answer in Steam" },
      { key: "game", label: "Starting the game" },
    ],
    // korrid downloads these before it starts the runner and passes the
    // ready directories in `artifacts`. An x86_64 device skips the FEX rootfs,
    // which has no x86_64 build (Core ADR 0052).
    artifacts: ["@korri:fex/rootfs", "@korri:proton/cachyos"],
  },
  // Korri ADR 0083: Steam games on Valve's engine with no Steam client. Opt-in;
  // the client runner above stays the default. korrid runs korri-steam-host
  // beside the game; steam-engine-session plays the game through Proton.
  engine: {
    program: "steam-engine-session",
    systems: ["steam"],
    platforms: ["aarch64-linux"],
    steps: [
      { key: "update", label: "Updating" },
      { key: "sync", label: "Syncing saves" },
      { key: "game", label: "Starting the game" },
    ],
    artifacts: [
      "@korri:fex/rootfs",
      "@korri:proton/cachyos",
      `${PLUGIN_ID}/${ENGINE_PACKAGE_KEY}`,
      `${PLUGIN_ID}/${LEGACYCOMPAT_KEY}`,
    ],
  },
}

/** The person's engine-only Steam folder, beside the client runner's `steam`. */
const ENGINE_FOLDER = "steam-engine"

function requiredPath(paths: Record<string, string>, key: string): string {
  const path = paths[key]
  if (!path) {
    throw new Error(`Steam requires ${key} from its required plugin`)
  }
  return path
}

/**
 * Both runners: the selected app id, the person's Steam folder for this
 * runner (`homeVariable` = `home` under the account root), and the ready
 * Proton and FEX directories of the exact required builds, as korrid passes
 * them under `<pluginId>/<key>`. korrid adds KORRI_STEAM_ENGINE_CHANNEL for
 * the engine runner's game unit.
 */
function steamLaunch(
  input: PluginLaunchInput,
  homeVariable: string,
  home: string,
): PluginLaunchOutput {
  if (!input.ref || !/^[1-9][0-9]*$/.test(input.ref)) {
    throw new Error("Steam requires a provider ref")
  }
  const overrides = input.overrides
  if (overrides?.config !== undefined) {
    throw new Error("Steam takes no raw config override")
  }
  if (overrides?.settings !== undefined && Object.keys(overrides.settings).length > 0) {
    throw new Error("Steam runner does not implement typed settings yet")
  }
  const folder = `${input.accountRoot}/${home}`
  const env: Record<string, string> = {
    [homeVariable]: folder,
    KORRI_PROTON_CACHYOS: requiredPath(input.artifacts, "@korri:proton/cachyos"),
  }
  // korrid passes the FEX rootfs only on a device whose platform has it. The
  // ARM64 session program refuses to start without it; the x86_64 one needs
  // no FEX.
  if (input.artifacts["@korri:fex/rootfs"]) {
    env.KORRI_FEX_CONFIG = requiredPath(input.files, "@korri:fex/config")
    env.KORRI_FEX_ROOTFS = input.artifacts["@korri:fex/rootfs"]
  }
  return { command: input.program, args: [input.ref], env, directories: [folder], envUnset: [] }
}

function prepareLaunch(input: PluginLaunchInput): PluginLaunchOutput {
  if (input.runnerId !== `${PLUGIN_ID}/engine`) {
    return steamLaunch(input, "STEAM_HOME", "steam")
  }
  // korrid passes this plugin's own artifacts under their local keys.
  requiredPath(input.artifacts, ENGINE_PACKAGE_KEY)
  const launch = steamLaunch(input, "STEAM_ENGINE_HOME", ENGINE_FOLDER)
  launch.env.KORRI_STEAM_LEGACYCOMPAT = requiredPath(input.artifacts, LEGACYCOMPAT_KEY)
  return launch
}

// Ported from legacy product/plugins/steam/src/discovery.ts and
// state-materializer.ts. korrid reads only the declared first-party manifests.
type VdfObject = { [key: string]: string | VdfObject }

function parseVdf(content: string): VdfObject {
  const tokens: string[] = []
  let index = 0
  while (index < content.length) {
    const char = content[index]
    if (/\s/.test(char)) {
      index += 1
      continue
    }
    if (char === "/" && content[index + 1] === "/") {
      while (index < content.length && content[index] !== "\n") index += 1
      continue
    }
    if (char === "{" || char === "}") {
      tokens.push(char)
      index += 1
      continue
    }
    if (char !== '"') throw new Error("invalid VDF token")
    index += 1
    let value = ""
    let closed = false
    while (index < content.length) {
      const next = content[index++]
      if (next === "\\") {
        value += content[index++] ?? ""
        continue
      }
      if (next === '"') {
        closed = true
        break
      }
      value += next
    }
    if (!closed) throw new Error("unterminated VDF string")
    tokens.push(value)
  }
  index = 0
  const object = (nested: boolean, depth: number): VdfObject => {
    if (depth > 64) throw new Error("VDF nesting limit")
    const result: VdfObject = Object.create(null)
    while (index < tokens.length) {
      const key = tokens[index++]
      if (key === "}") {
        if (nested) return result
        throw new Error("unexpected closing brace")
      }
      if (key === "{") throw new Error("unexpected opening brace")
      const value = tokens[index++]
      if (value === undefined || value === "}") throw new Error("missing VDF value")
      result[key] = value === "{" ? object(true, depth + 1) : value
    }
    if (nested) throw new Error("missing closing brace")
    return result
  }
  return object(false, 0)
}

// korrid passes the plugin's own id in the discovery input (ADR 0045: no
// namespace in plugin source).
// Only the manifest files are read, so the handler works with the discovery
// input of every korrid contract (with or without its later fields).
function discoverInstalledApps(
  input: Pick<ReleaseDiscoveryInput, "files">,
): ProviderRefReleaseObservation[] {
  const observations: ProviderRefReleaseObservation[] = []
  for (const file of input.files) {
    const match = /^steamapps\/appmanifest_(\d+)\.acf$/.exec(file.relativePath)
    if (!match) continue
    try {
      const parsed = parseVdf(file.text)
      const state = typeof parsed.AppState === "object" ? parsed.AppState : parsed
      const appid = state.appid ?? match[1]
      if (appid !== match[1]) continue
      if (
        typeof state.StateFlags !== "string" ||
        !/^\d+$/.test(state.StateFlags) ||
        Number(state.StateFlags) !== 4
      ) continue
      // Legacy excludes every explicit non-Game type, including Tool, Proton,
      // Steam Runtime and Steamworks redistributables. Missing type is valid.
      if (
        typeof state.type === "string" && state.type.toLowerCase() !== "game"
      ) continue
      const title = typeof state.name === "string" ? state.name.trim() : ""
      if (!title) continue
      observations.push({
        kind: "provider-ref-release",
        confidence: "high",
        source: { relativePath: file.relativePath },
        target: { provider: PLUGIN_ID, ref: appid },
        release: { id: "steam", title, system: "steam" },
        launch: { use: `${PLUGIN_ID}/steam` },
      })
    } catch {
      // A partial manifest is not an installed game.
      continue
    }
  }
  return observations
}

export const handlers = {
  "discovery.discover": discoverInstalledApps,
  "launch.prepare": prepareLaunch,
}

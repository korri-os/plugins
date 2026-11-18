import type {
  PluginLaunchInput,
  PluginLaunchOutput,
  ReleaseDiscoveryInput,
  ProviderRefReleaseObservation,
} from "../../contracts/generated/korrid"

export const name = "steam"
export const title = "Steam"
export const description = "Runs Steam content through the native session program."

// Ids in this file are local (ADR 0045): korrid prefixes them with this
// plugin's own id P, whatever its publisher namespace. The discovery provider
// is P/installed-apps, the runners P/steam and P/engine, the engine package
// P/engine-package, and the Steam provider is P itself.
export const discovery = [
  { id: "installed-apps", title: "Steam installed apps" },
]

export const systems = {
  steam: { title: "Steam" },
}

// Korri ADR 0083: this plugin is also the Steam provider. korrid derives its
// id from the plugin's own id, serves its search and listing from
// korri-steam-host's `list-apps` for the current person, and runs Get and
// Remove download as host jobs. Nothing is declared for it here.

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
export const artifacts = {
  "engine-package": {
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
    // Required plugins' artifacts by full id; this plugin's own by its key.
    artifacts: ["@korri:fex/rootfs", "@korri:proton/cachyos", ENGINE_PACKAGE_KEY],
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

/** The plugin id P of a runner id P/<key>, as korrid passes it. */
function pluginIdOf(runnerId: string): string {
  const slash = runnerId.lastIndexOf("/")
  if (slash <= 0) throw new Error("Steam requires its runner id")
  return runnerId.slice(0, slash)
}

function prepareLaunch(input: PluginLaunchInput): PluginLaunchOutput {
  if (input.runnerId === `${pluginIdOf(input.runnerId)}/engine`) return prepareEngineLaunch(input)
  if (!input.ref) {
    throw new Error("Steam requires a provider ref")
  }
  const overrides = input.overrides
  if (overrides?.config !== undefined) {
    throw new Error("Steam takes no raw config override")
  }
  if (
    overrides?.settings !== undefined &&
    Object.keys(overrides.settings).length > 0
  ) {
    throw new Error("Steam runner does not implement typed settings yet")
  }
  const steamHome = `${input.accountRoot}/steam`
  // The exact required @korri:fex and @korri:proton builds: their files and
  // ready artifacts, as korrid passes them under `<pluginId>/<key>`.
  const env: Record<string, string> = {
    STEAM_HOME: steamHome,
    KORRI_PROTON_CACHYOS: requiredPath(input.artifacts, "@korri:proton/cachyos"),
  }
  // korrid passes the FEX rootfs only on a device whose platform has it. The
  // ARM64 session program refuses to start without it; the x86_64 one needs
  // no FEX.
  if (input.artifacts["@korri:fex/rootfs"]) {
    env.KORRI_FEX_CONFIG = requiredPath(input.files, "@korri:fex/config")
    env.KORRI_FEX_ROOTFS = input.artifacts["@korri:fex/rootfs"]
  }
  return {
    command: input.program,
    args: [input.ref],
    env,
    directories: [steamHome],
    envUnset: [],
  }
}

// The engine runner's game unit. korrid adds KORRI_STEAM_ENGINE_CHANNEL (the
// launch channel it shares with korri-steam-host); this declaration gives the
// person's engine folder and the ready Proton and FEX directories.
function prepareEngineLaunch(input: PluginLaunchInput): PluginLaunchOutput {
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
  // korrid passes this plugin's own artifacts under their local keys.
  requiredPath(input.artifacts, ENGINE_PACKAGE_KEY)
  const engineHome = `${input.accountRoot}/${ENGINE_FOLDER}`
  const env: Record<string, string> = {
    STEAM_ENGINE_HOME: engineHome,
    KORRI_PROTON_CACHYOS: requiredPath(input.artifacts, "@korri:proton/cachyos"),
  }
  if (input.artifacts["@korri:fex/rootfs"]) {
    env.KORRI_FEX_CONFIG = requiredPath(input.files, "@korri:fex/config")
    env.KORRI_FEX_ROOTFS = input.artifacts["@korri:fex/rootfs"]
  }
  return {
    command: input.program,
    args: [input.ref],
    env,
    directories: [engineHome],
    envUnset: [],
  }
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

// korrid adds the plugin's own id to the discovery input (ADR 0045: no
// namespace in plugin source). The intersection keeps this file valid against
// contracts generated before that field.
type DiscoveryInput = ReleaseDiscoveryInput & { pluginId: string }

function discoverInstalledApps(
  input: DiscoveryInput,
): ProviderRefReleaseObservation[] {
  const pluginId = input.pluginId
  if (typeof pluginId !== "string" || !/^@[^/:\s]+:[^/:\s]+$/.test(pluginId)) {
    throw new Error("Steam discovery requires the plugin id")
  }
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
        target: { provider: pluginId, ref: appid },
        release: { id: "steam", title, system: "steam" },
        launch: { use: `${pluginId}/steam` },
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

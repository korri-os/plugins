import type {
  PluginLaunchInput,
  PluginLaunchOutput,
  SaveKind,
  SaveLocation,
} from "../../contracts/generated/korrid"

// The wire enum is type-only: the sandbox cannot import generated Rust code.
type LaunchOutput = Omit<PluginLaunchOutput, "saveLocations"> & {
  saveLocations: (Omit<SaveLocation, "kind"> & { kind: `${SaveKind}` })[]
}

export const name = "cemu"
export const title = "Cemu"
export const description = "Runs Wii U games with account-local Cemu data and game saves."
export const systems = {
  wiiu: {
    id: "wiiu", title: "Wii U",
    content: { extensions: ["wua", "wud", "wux", "rpx", "wuhb"] },
  },
}
export const runners = {
  cemu: { id: "@korri:cemu/cemu", program: "cemu", systems: ["wiiu"] },
}

function prepareLaunch(input: PluginLaunchInput): LaunchOutput {
  if (input.runnerId !== runners.cemu.id) throw new Error("Unknown Cemu runner")
  if (input.corePath !== undefined || input.ref !== undefined) {
    throw new Error("Cemu requires a game file, not a core or provider reference")
  }
  if (input.overrides?.config !== undefined || Object.keys(input.overrides?.settings ?? {}).length > 0) {
    throw new Error("Configure Cemu through its native settings")
  }
  const { contentPath, accountRoot, saveRoot } = input
  if (contentPath === undefined || [contentPath, accountRoot, saveRoot].some(
    path => !path.startsWith("/") || path.includes("\0"),
  )) throw new Error("Cemu requires absolute content, account and save paths without NUL bytes")

  // CemuApp::DeterminePaths uses XDG; LaunchSettings offers --mlc but no
  // user-data CLI option. Retain Cemu's own Linux and MLC directory names.
  const mlc = `${saveRoot}/mlc01`
  const saves = `${mlc}/usr/save`
  return {
    command: input.program,
    args: ["-f", "-g", contentPath, "--mlc", mlc],
    env: {
      HOME: accountRoot,
      XDG_CONFIG_HOME: `${accountRoot}/.config`,
      XDG_DATA_HOME: `${accountRoot}/.local/share`,
      XDG_CACHE_HOME: `${accountRoot}/.cache`,
    },
    cwd: accountRoot,
    directories: [accountRoot, saves],
    saveLocations: [{ key: "saves", kind: "save", path: saves }],
  }
}
export const handlers = { "launch.prepare": prepareLaunch }

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

export const name = "eden"
export const title = "Eden"
export const description = "Runs Nintendo Switch games with account-local Eden data and game saves."
export const systems = {
  switch: {
    id: "switch", title: "Nintendo Switch",
    content: { extensions: ["nsp", "xci"] },
  },
}
export const runners = {
  eden: { id: "@korri:eden/eden", program: "eden", systems: ["switch"] },
}

function prepareLaunch(input: PluginLaunchInput): LaunchOutput {
  if (input.runnerId !== runners.eden.id) throw new Error("Unknown Eden runner")
  if (input.corePath !== undefined || input.ref !== undefined) {
    throw new Error("Eden requires a game file, not a core or provider reference")
  }
  if (input.overrides?.config !== undefined || Object.keys(input.overrides?.settings ?? {}).length > 0) {
    throw new Error("Configure Eden through its native settings")
  }
  const { contentPath, accountRoot, saveRoot } = input
  if (contentPath === undefined || [input.program, contentPath, accountRoot, saveRoot].some(
    path => !path.startsWith("/") || path.includes("\0"),
  )) throw new Error("Eden requires absolute program, content, account and save paths without NUL bytes")

  // SimpleIni treats line breaks as records; Eden strips double quotes from paths.
  if ([accountRoot, saveRoot].some(path => /[\x00-\x1f\x7f"]/.test(path))) {
    throw new Error("Eden account and save paths cannot contain controls or double quotes")
  }

  // Eden's native save_directory is a separate NAND save root. Keep firmware
  // in account-local NAND while game saves use korrid's session save root.
  const saves = `${saveRoot}/nand/user/save`
  return {
    command: input.program,
    args: ["-f", "-g", contentPath],
    env: {
      HOME: accountRoot,
      EDEN_SAVE_ROOT: saveRoot,
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

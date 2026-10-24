import type {
  PluginLaunchInput,
  PluginLaunchOutput,
  SaveKind,
  SaveLocation,
} from "../../contracts/generated/korrid"

export const name = "pyxel"
export const title = "Pyxel"
export const description = "Runs local Pyxel application cartridges natively."

// v2.9.9 cli.py produces ZIP .pyxapp containers. Plain .py projects are
// deliberately not identified or routed by this plugin.
// ZIP magic is format evidence, not evidence of trust or safe Python execution.
export const systems = {
  pyxel: {
    id: "pyxel",
    title: "Pyxel",
    content: {
      extensions: ["pyxapp"],
      evidence: { bytes: [{ offset: 0, hex: "504b0304" }] },
    },
  },
}

export const runners = {
  pyxel: {
    id: "@korri:pyxel/pyxel",
    program: "pyxel",
    systems: ["pyxel"],
  },
}

type LaunchOutput = Omit<PluginLaunchOutput, "saveLocations"> & {
  saveLocations: (Omit<SaveLocation, "kind"> & { kind: `${SaveKind}` })[]
}

function prepareLaunch(input: PluginLaunchInput): LaunchOutput {
  if (input.runnerId !== runners.pyxel.id) throw new Error("Unknown Pyxel runner")
  if (input.corePath !== undefined) throw new Error("Pyxel loads no emulator core")
  if (
    input.overrides?.config !== undefined ||
    Object.keys(input.overrides?.settings ?? {}).length > 0
  ) throw new Error("Pyxel does not support launch overrides")
  const content = input.contentPath
  if (
    content === undefined ||
    [content, input.accountRoot, input.saveRoot].some(
      path => !path.startsWith("/") || path.includes("\0"),
    )
  ) throw new Error("Pyxel requires absolute content, account and save paths without NUL bytes")
  if (!/\.pyxapp$/i.test(content)) throw new Error("Pyxel requires .pyxapp content")
  // v2.9.9 user_data_dir writes HOME/.pyxel/<vendor>/<app>. init changes
  // cwd to extracted source for resources; relative saves are not durable.
  // This is a save convention, NOT a Python security sandbox.
  return {
    command: input.program,
    args: [content],
    env: {
      HOME: input.saveRoot,
      PYTHONDONTWRITEBYTECODE: "1",
    },
    cwd: input.saveRoot,
    directories: [input.accountRoot, input.saveRoot],
    saveLocations: [{ key: "saves", kind: "save", path: input.saveRoot }],
  }
}

export const handlers = { "launch.prepare": prepareLaunch }

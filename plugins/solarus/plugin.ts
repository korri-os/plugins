import type {
  PluginLaunchInput,
  PluginLaunchOutput,
} from "../../contracts/generated/korrid"

export const name = "solarus"
export const title = "Solarus"
export const description = "Runs Solarus quests with saves in Korri account storage."

// Retain the Solarus identity from legacy's app integration and system example.
export const systems = {
  solarus: {
    title: "Solarus",
    // Upstream's quest archive suffix. Do not claim every general ZIP file.
    content: { extensions: ["solarus"] },
  },
}

export const runners = {
  solarus: {
    program: "solarus",
    systems: ["solarus"],
  },
}

function prepareLaunch(input: PluginLaunchInput): PluginLaunchOutput {
  if (input.runnerId !== "@korri:solarus/solarus") {
    throw new Error("Unknown Solarus runner")
  }
  if (input.corePath !== undefined) {
    throw new Error("Solarus is a standalone engine and loads no emulator core")
  }
  if (
    input.overrides?.config !== undefined ||
    Object.keys(input.overrides?.settings ?? {}).length > 0
  ) {
    throw new Error("Configure Solarus through the quest's native settings")
  }
  // Provider-ref routes carry no file. Solarus always loads one quest.
  const contentPath = input.contentPath
  if (
    contentPath === undefined ||
    !contentPath.startsWith("/") ||
    !input.accountRoot.startsWith("/") ||
    contentPath.includes("\0") ||
    input.accountRoot.includes("\0")
  ) {
    throw new Error("Solarus requires absolute quest and account paths without NUL bytes")
  }
  // Upstream uses PhysFS's user home, not XDG_STATE_HOME. The owner chose
  // accountRoot as HOME, retaining .solarus/<quest write_dir> without migration.
  return {
    command: input.program,
    args: [contentPath],
    env: { HOME: input.accountRoot },
    // Upstream can write error.txt relative to cwd. Keep it off the media folder.
    cwd: input.accountRoot,
    directories: [input.accountRoot],
  }
}

export const handlers = {
  "launch.prepare": prepareLaunch,
}

import type {
  PluginLaunchInput,
  PluginLaunchOutput,
} from "../../contracts/generated/korrid"

export const name = "bitsybox"
export const title = "Bitsybox"
export const description =
  "Runs native Bitsy game data with SDL keyboard and gamepad controls."

// doc/MANUAL.txt names Bitsy and its native text-data extension.
export const systems = {
  bitsy: {
    id: "bitsy",
    title: "Bitsy",
    content: { extensions: ["bitsy"] },
  },
}

export const runners = {
  bitsybox: {
    id: "@korri:bitsybox/bitsybox",
    program: "bitsybox",
    systems: ["bitsy"],
  },
}

function prepareLaunch(input: PluginLaunchInput): PluginLaunchOutput {
  if (input.runnerId !== runners.bitsybox.id) {
    throw new Error("Unknown Bitsybox runner")
  }
  if (input.corePath !== undefined) {
    throw new Error(
      "Bitsybox is a standalone engine and loads no emulator core",
    )
  }
  if (
    input.overrides?.config !== undefined ||
    Object.keys(input.overrides?.settings ?? {}).length > 0
  ) {
    throw new Error("Bitsybox does not support Korri launch overrides")
  }
  const contentPath = input.contentPath
  if (
    contentPath === undefined ||
    !contentPath.startsWith("/") ||
    !input.accountRoot.startsWith("/") ||
    contentPath.includes("\0") ||
    input.accountRoot.includes("\0")
  ) {
    throw new Error(
      "Bitsybox requires absolute content and account paths without NUL bytes",
    )
  }
  return {
    command: input.program,
    args: [contentPath],
    env: {},
    // Follow Solarus: never make the media directory the process working directory.
    cwd: input.accountRoot,
    directories: [input.accountRoot],
  }
}

export const handlers = {
  "launch.prepare": prepareLaunch,
}

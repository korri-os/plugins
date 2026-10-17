import type {
  PluginLaunchInput,
  PluginLaunchOutput,
} from "../../contracts/generated/korrid"

export const name = "zquest-classic"
export const title = "ZQuest Classic"
export const description =
  "Plays Zelda Classic .qst quests with account-owned saves."

// Retain the system and runner names from Korri legacy's producer.
export const systems = {
  "zelda-classic": {
    id: "zelda-classic",
    title: "Zelda Classic Quest",
    // Native unpacked quest files only; packed quest archives are not claimed.
    content: { extensions: ["qst"] },
  },
}
export const runners = {
  zplayer: {
    id: "@korri:zquest-classic/zplayer",
    program: "zplayer",
    systems: ["zelda-classic"],
  },
}

function prepareLaunch(input: PluginLaunchInput): PluginLaunchOutput {
  if (input.corePath !== undefined) {
    throw new Error("ZQuest Classic is standalone and loads no core")
  }
  if (
    input.overrides?.config !== undefined ||
    Object.keys(input.overrides?.settings ?? {}).length > 0
  ) {
    throw new Error("ZQuest Classic does not implement Korri launch overrides")
  }
  // Account-owned storage follows Zelda3. The launcher owns native state files.
  return {
    command: input.program,
    args: ["--", input.contentPath, `${input.accountRoot}/zquest-classic`],
    env: {},
  }
}

export const handlers = { "launch.prepare": prepareLaunch }

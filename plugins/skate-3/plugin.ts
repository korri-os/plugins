import type {
  PluginLaunchInput,
  PluginLaunchOutput,
} from "../../contracts/generated/korrid"

export const name = "skate-3"
export const title = "Skate 3"
export const description =
  "Runs the native Skate 3 recompilation on your own Xbox 360 disc image."

export const systems = {
  "xbox-360": { id: "xbox-360", title: "Xbox 360" },
}

export const runners = {
  skate3: {
    id: "@korri:skate-3/skate3",
    program: "skate3",
    releases: [
      // Whole bare ISO, measured from the owner's archive on aka.
      // Skate 3 (USA, Europe) (En,Fr,De,Es,It,Nl), 7,838,695,424 bytes.
      "sha256:bd8d430188aa61b0ebf2e33e5672822dd7e59c9080fc09e802195e1ee75ebff0",
    ],
  },
}

export const discovery = {
  fileReleases: {
    "xbox-360-discs": {
      id: "@korri:skate-3/xbox-360-discs",
      title: "Xbox 360 disc images",
      extensions: ["iso"],
      system: "xbox-360",
      runners: ["@korri:skate-3/skate3"],
    },
  },
}

function prepareLaunch(input: PluginLaunchInput): PluginLaunchOutput {
  return {
    command: input.program,
    args: [],
    env: {
      SKATE3_INSTALL_ISO: input.contentPath,
      SKATE3_INSTALL_TU: "download",
    },
  }
}

export const handlers = {
  "launch.prepare": prepareLaunch,
}

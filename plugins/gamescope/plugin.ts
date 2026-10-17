import type {
  LaunchSettingValue,
  PluginLaunchOutput,
} from "../../contracts/generated/korrid"
import { composeLaunch } from "./compose"

// Mirrors the launch.compose treaty. Move this type to the generated import
// when the pinned Korri input includes PluginComposeInput; do not pin a branch.
export interface PluginComposeInput {
  modifierId: string
  runnerId: string
  familyId?: string
  plan: PluginLaunchOutput
  settings: Record<string, LaunchSettingValue>
  config: { append?: string }
  files: Record<string, string>
  display?: { width: number; height: number }
}

export const name = "gamescope"
export const title = "Gamescope"
export const description = "Runs a game in nested Gamescope with scaling and a frame-rate limit."

export const modifiers = {
  gamescope: { id: "@korri:gamescope/gamescope" },
}
export const handlers = { "launch.compose": composeLaunch }

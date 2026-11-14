// The settings are Moonlight's, rendered for this runner: nix/default.nix
// builds ./settings from plugins/moonlight/settings.ts (ADR 0061, #435).
import { describeSettings, validateSettings, renderSettings } from "./settings"

export const name = "viewer"
export const title = "Korri viewer"
export const services = ["korri-viewer-setup"]

export const runners = {
  viewer: { program: "viewer" },
}

export const handlers = {
  "settings.describe": describeSettings,
  "settings.validate": validateSettings,
  "settings.render": renderSettings,
}

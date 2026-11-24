// Settings belong to the Rust viewer (ADRs 0061 and 0099 in Core).
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

import { describeSettings, validateSettings, renderSettings } from "./settings"

export const name = "sunshine"
export const title = "Sunshine streaming host"
export const services = [
  "korri-sunshine",
  "korri-sunshine-certificate-control.socket",
  "korri-sunshine-input-setup",
]

export const handlers = {
  "settings.describe": describeSettings,
  "settings.validate": validateSettings,
  "settings.render": renderSettings,
}

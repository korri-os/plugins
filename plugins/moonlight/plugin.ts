import { describeSettings, validateSettings, renderSettings } from "./settings"

export const name = "moonlight"
export const title = "Moonlight stream viewer"
export const services = ["korri-moonlight-setup"]

export const runners = {
  moonlight: { program: "moonlight" },
}

export const handlers = {
  "settings.describe": describeSettings,
  "settings.validate": validateSettings,
  "settings.render": renderSettings,
}

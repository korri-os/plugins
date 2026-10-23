import type { PluginLaunchOutput } from "../../contracts/generated/korrid"
import type { PluginComposeInput } from "./plugin"

class ComposeError extends Error {
  readonly retryable = false
  constructor(readonly code: string, message: string) {
    super(message)
    this.name = "PluginError"
  }
  toJSON() {
    return { code: this.code, message: this.message, retryable: this.retryable }
  }
}

// Korri passes --force-composition unless the merged settings set
// force-composition to false. Change this one constant to change the default;
// README.md records why it is on (RG353M frame pacing).
const forceCompositionDefault = true

// Limits come from the parsers in Gamescope 3.16.31. parse_integer
// (src/main.cpp:455) is std::from_chars into int; parse_float (main.cpp:469)
// is std::from_chars into float and refuses values that underflow. atoi/atof
// options (src/steamcompmgr.cpp:9814 loop) never fail, so Korri bounds them.
const intMax = 2_147_483_647
const floatMin = 1.1754943508222875e-38 // FLT_MIN
const floatMax = 3.4028234663852886e38 // FLT_MAX

export type SettingRule =
  | { kind: "integer"; minimum: number; maximum: number }
  | { kind: "float"; minimum: number; maximum: number }
  | { kind: "choice"; choices: readonly string[] }
  | { kind: "boolean" }
  | { kind: "path" }
  | { kind: "string"; accepts: string; example: string; valid: (value: string) => boolean }

function hotspot(value: string): boolean {
  const match = /^(\d{1,10}),(\d{1,10})$/.exec(value)
  return match !== null && Number(match[1]) <= intMax && Number(match[2]) <= intMax
}
function shaderName(value: string): boolean {
  return value !== "" && !value.includes("\0") &&
    value.split("/").every(part => part !== "" && part !== "." && part !== "..")
}

// Each key is the exact Gamescope long option (src/main.cpp:58 table; line
// numbers in README.md). This order is also the argv order. steam precedes
// virtual-connector-strategy: --steam replaces the default strategy
// (main.cpp:766), so an explicit strategy must be parsed after it.
export const settingsRules: Record<string, SettingRule> = {
  "output-width": { kind: "integer", minimum: 1, maximum: intMax },
  "output-height": { kind: "integer", minimum: 1, maximum: intMax },
  "nested-width": { kind: "integer", minimum: 1, maximum: intMax },
  "nested-height": { kind: "integer", minimum: 1, maximum: intMax },
  // ConvertHztomHz multiplies the int by 1000 (src/refresh_rate.h:7).
  "nested-refresh": { kind: "integer", minimum: 1, maximum: Math.floor(intMax / 1000) },
  scaler: { kind: "choice", choices: ["auto", "integer", "fit", "fill", "stretch"] },
  filter: { kind: "choice", choices: ["linear", "nearest", "fsr", "nis", "pixel"] },
  sharpness: { kind: "integer", minimum: 0, maximum: 20 },
  "framerate-limit": { kind: "integer", minimum: 0, maximum: intMax },
  "max-scale": { kind: "float", minimum: floatMin, maximum: floatMax },
  "force-composition": { kind: "boolean" },
  "adaptive-sync": { kind: "boolean" },
  rt: { kind: "boolean" },
  "fade-out-duration": { kind: "integer", minimum: 0, maximum: intMax },
  "force-windows-fullscreen": { kind: "boolean" },
  "hdr-enabled": { kind: "boolean" },
  // The atom path treats < 1 as unset (set_sdr_on_hdr_brightness,
  // steamcompmgr.cpp:565); 10000 nits is the PQ ceiling.
  "hdr-sdr-content-nits": { kind: "float", minimum: 1, maximum: 10000 },
  "hdr-itm-enabled": { kind: "boolean" },
  // The atom path clamps these to 1..1000 and 1..10000 (steamcompmgr.cpp:6225).
  "hdr-itm-sdr-nits": { kind: "float", minimum: 1, maximum: 1000 },
  "hdr-itm-target-nits": { kind: "float", minimum: 1, maximum: 10000 },
  "sdr-gamut-wideness": { kind: "float", minimum: 0, maximum: 1 },
  "disable-color-management": { kind: "boolean" },
  "force-grab-cursor": { kind: "boolean" },
  "mouse-sensitivity": { kind: "float", minimum: floatMin, maximum: floatMax },
  // TouchClickModes: Hover..Trackpad (src/backend.h:100).
  "default-touch-mode": { kind: "integer", minimum: 0, maximum: 6 },
  cursor: { kind: "path" },
  "cursor-hotspot": {
    kind: "string", accepts: "X,Y with integers 0..2147483647", example: "0,0", valid: hotspot,
  },
  "cursor-scale-height": { kind: "integer", minimum: 1, maximum: intMax },
  "hide-cursor-delay": { kind: "integer", minimum: 0, maximum: intMax },
  "prefer-vk-device": {
    kind: "string", accepts: "VENDOR:DEVICE with 1..8 hex digits each", example: "13b5:74021000",
    valid: value => /^[0-9A-Fa-f]{1,8}:[0-9A-Fa-f]{1,8}$/.test(value),
  },
  "reshade-effect": {
    kind: "string", accepts: "a relative file name under reshade/Shaders without . or .. segments",
    example: "Example.fx", valid: shaderName,
  },
  "reshade-technique-idx": { kind: "integer", minimum: 0, maximum: intMax },
  "xwayland-count": { kind: "integer", minimum: 1, maximum: intMax },
  steam: { kind: "boolean" },
  "virtual-connector-strategy": {
    kind: "choice", choices: ["SingleApplication", "SteamControlled", "PerAppId", "PerWindow"],
  },
  borderless: { kind: "boolean" },
  "disable-xres": { kind: "boolean" },
  "allow-deferred-backend": { kind: "boolean" },
}

function settingError(key: string, rule: SettingRule, value: unknown): string | undefined {
  switch (rule.kind) {
    case "integer":
      return typeof value === "number" && Number.isInteger(value) &&
        value >= rule.minimum && value <= rule.maximum
        ? undefined
        : `Gamescope setting ${key} must be an integer ${rule.minimum}..${rule.maximum}`
    case "float":
      return typeof value === "number" && Number.isFinite(value) &&
        value >= rule.minimum && value <= rule.maximum
        ? undefined
        : `Gamescope setting ${key} must be a number ${rule.minimum}..${rule.maximum}`
    case "choice":
      return typeof value === "string" && rule.choices.includes(value)
        ? undefined
        : `Gamescope setting ${key} must be one of: ${rule.choices.join(", ")}`
    case "boolean":
      return typeof value === "boolean" ? undefined : `Gamescope setting ${key} must be true or false`
    case "path":
      return typeof value === "string" && value.startsWith("/") && !value.includes("\0")
        ? undefined
        : `Gamescope setting ${key} must be an absolute path without NUL bytes`
    case "string":
      return typeof value === "string" && rule.valid(value)
        ? undefined
        : `Gamescope setting ${key} must be ${rule.accepts}`
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
}
function positiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0
}

// Shell word syntax only, not a shell interpreter. In double quotes POSIX
// backslash removes itself only before $, `, ", \\ or newline. No expansions,
// operator execution, comments, or environment/filesystem access take place.
function appendWords(text: string): string[] {
  const words: string[] = []
  let word = ""
  let started = false
  let quote: "'" | '"' | undefined
  if (text.includes("\0")) {
    throw new ComposeError("gamescope-append", "Gamescope config.append must not contain NUL bytes")
  }
  for (let index = 0; index < text.length; index++) {
    const char = text[index]
    if (quote === "'") {
      if (char === "'") quote = undefined
      else word += char
    } else if (char === "\\") {
      const next = text[index + 1]
      if (next === undefined) {
        throw new ComposeError("gamescope-append", "Gamescope config.append has a trailing backslash")
      }
      if (quote === undefined || '$`"\\\n'.includes(next)) {
        index++
        if (next !== "\n") {
          word += next
          started = true
        }
      } else word += char
    } else if (quote === '"') {
      if (char === '"') quote = undefined
      else word += char
    } else if (char === "'" || char === '"') {
      quote = char
      started = true
    } else if (char === " " || char === "\t" || char === "\n") {
      if (started) words.push(word)
      word = ""
      started = false
    } else {
      word += char
      started = true
    }
  }
  if (quote !== undefined) {
    throw new ComposeError("gamescope-append", "Gamescope config.append has an unterminated quote")
  }
  if (started) words.push(word)
  return words
}

export function composeLaunch(input: PluginComposeInput): PluginLaunchOutput {
  if (input.modifierId !== "@korri:gamescope/gamescope") {
    throw new ComposeError("gamescope-modifier", "Unknown Gamescope modifier contribution")
  }
  const command = input.files?.gamescope
  if (typeof command !== "string" || !command.startsWith("/") || command.includes("\0")) {
    throw new ComposeError("gamescope-file", "Gamescope requires an absolute named gamescope file")
  }
  if (!isRecord(input.settings)) {
    throw new ComposeError("gamescope-setting", "Gamescope settings must be a map of scalar values")
  }
  for (const key of Object.keys(input.settings).sort()) {
    if (!Object.hasOwn(settingsRules, key)) {
      throw new ComposeError("gamescope-setting", `Unknown Gamescope setting: ${key}`)
    }
    const error = settingError(key, settingsRules[key], input.settings[key])
    if (error !== undefined) throw new ComposeError("gamescope-setting", error)
  }
  const settings = { ...input.settings }
  settings["force-composition"] ??= forceCompositionDefault
  for (const [width, height] of [["output-width", "output-height"], ["nested-width", "nested-height"]]) {
    if ((settings[width] === undefined) !== (settings[height] === undefined)) {
      throw new ComposeError("gamescope-setting-pair", `Gamescope settings ${width} and ${height} must be given as a pair`)
    }
  }
  if (settings["output-width"] === undefined) {
    if (!positiveInteger(input.display?.width) || !positiveInteger(input.display?.height)) {
      throw new ComposeError("gamescope-output-size", "Gamescope requires output-width and output-height settings or a valid display hardware fact")
    }
    settings["output-width"] = input.display.width
    settings["output-height"] = input.display.height
  }
  if (
    !isRecord(input.config) || Object.keys(input.config).some(key => key !== "append") ||
    (input.config.append !== undefined && typeof input.config.append !== "string")
  ) {
    throw new ComposeError("gamescope-config", "Gamescope config permits only append text")
  }
  const args = ["--backend", "wayland", "--fullscreen", "--expose-wayland"]
  for (const key of Object.keys(settingsRules)) {
    const value = settings[key]
    if (value === true) args.push(`--${key}`)
    else if (value !== undefined && value !== false) args.push(`--${key}`, String(value))
  }
  args.push(...appendWords(input.config.append ?? ""), "--", input.plan.command, ...input.plan.args)
  return { ...input.plan, command, args }
}

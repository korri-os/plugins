import type { PluginLaunchOutput } from "../../contracts/generated/korrid"
import type { PluginComposeInput } from "./plugin"

class ComposeError extends Error {
  readonly retryable = false
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = "PluginError"
  }
  toJSON() {
    return { code: this.code, message: this.message, retryable: this.retryable }
  }
}

// Korri passes --force-composition unless the merged settings set
// video.force-composition to false. Change this one constant to change the default;
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
  return (
    value !== "" &&
    !value.includes("\0") &&
    value.split("/").every(part => part !== "" && part !== "." && part !== "..")
  )
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
    kind: "string",
    accepts: "X,Y with integers 0..2147483647",
    example: "0,0",
    valid: hotspot,
  },
  "cursor-scale-height": { kind: "integer", minimum: 1, maximum: intMax },
  "hide-cursor-delay": { kind: "integer", minimum: 0, maximum: intMax },
  "prefer-vk-device": {
    kind: "string",
    accepts: "VENDOR:DEVICE with 1..8 hex digits each",
    example: "13b5:74021000",
    valid: value => /^[0-9A-Fa-f]{1,8}:[0-9A-Fa-f]{1,8}$/.test(value),
  },
  "reshade-effect": {
    kind: "string",
    accepts: "a relative file name under reshade/Shaders without . or .. segments",
    example: "Example.fx",
    valid: shaderName,
  },
  "reshade-technique-idx": { kind: "integer", minimum: 0, maximum: intMax },
  "xwayland-count": { kind: "integer", minimum: 1, maximum: intMax },
  steam: { kind: "boolean" },
  "virtual-connector-strategy": {
    kind: "choice",
    choices: ["SingleApplication", "SteamControlled", "PerAppId", "PerWindow"],
  },
  borderless: { kind: "boolean" },
  "disable-xres": { kind: "boolean" },
  "allow-deferred-backend": { kind: "boolean" },
}

// Authored paths, in the same stable argv order as the native evidence table.
export const settingsPaths: Record<string, string> = {
  "output-width": "video.output.width",
  "output-height": "video.output.height",
  "nested-width": "video.nested.width",
  "nested-height": "video.nested.height",
  "nested-refresh": "video.nested.fps",
  scaler: "video.scaling.scaler",
  filter: "video.scaling.filter",
  sharpness: "video.scaling.sharpness",
  "framerate-limit": "video.fps-limit",
  "max-scale": "video.scaling.max",
  "force-composition": "video.force-composition",
  "adaptive-sync": "video.adaptive-sync",
  rt: "scheduling.realtime",
  "fade-out-duration": "window.fade-out-ms",
  "force-windows-fullscreen": "window.force-windows-fullscreen",
  "hdr-enabled": "video.hdr.enable",
  "hdr-sdr-content-nits": "video.hdr.sdr-content-nits",
  "hdr-itm-enabled": "video.hdr.inverse-tone-mapping.enable",
  "hdr-itm-sdr-nits": "video.hdr.inverse-tone-mapping.sdr-nits",
  "hdr-itm-target-nits": "video.hdr.inverse-tone-mapping.target-nits",
  "sdr-gamut-wideness": "video.hdr.sdr-gamut-wideness",
  "disable-color-management": "video.color-management",
  "force-grab-cursor": "window.grab-cursor",
  "mouse-sensitivity": "input.mouse-sensitivity",
  "default-touch-mode": "input.default-touch-mode",
  cursor: "cursor.image",
  "cursor-hotspot": "cursor.hotspot",
  "cursor-scale-height": "cursor.scale-height",
  "hide-cursor-delay": "cursor.hide-delay-ms",
  "prefer-vk-device": "backend.prefer-vk-device",
  "reshade-effect": "video.reshade.effect",
  "reshade-technique-idx": "video.reshade.technique-index",
  "xwayland-count": "window.xwayland-count",
  steam: "steam.enable",
  "virtual-connector-strategy": "steam.virtual-connector-strategy",
  borderless: "window.borderless",
  "disable-xres": "debug.xres",
  "allow-deferred-backend": "backend.allow-deferred",
}

function settingError(key: string, rule: SettingRule, value: unknown): string | undefined {
  switch (rule.kind) {
    case "integer":
      return typeof value === "number" &&
        Number.isInteger(value) &&
        value >= rule.minimum &&
        value <= rule.maximum
        ? undefined
        : `Gamescope setting ${key} must be an integer ${rule.minimum}..${rule.maximum}`
    case "float":
      return typeof value === "number" &&
        Number.isFinite(value) &&
        value >= rule.minimum &&
        value <= rule.maximum
        ? undefined
        : `Gamescope setting ${key} must be a number ${rule.minimum}..${rule.maximum}`
    case "choice":
      return typeof value === "string" && rule.choices.includes(value)
        ? undefined
        : `Gamescope setting ${key} must be one of: ${rule.choices.join(", ")}`
    case "boolean":
      return typeof value === "boolean"
        ? undefined
        : `Gamescope setting ${key} must be true or false`
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
        throw new ComposeError(
          "gamescope-append",
          "Gamescope config.append has a trailing backslash",
        )
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
  // Korrid validates and skips bad paths first. Direct callers receive the
  // same warn-and-skip behaviour, never the old setting refusal codes.
  const settings = acceptedSettings(input.settings)
  settings["force-composition"] ??= forceCompositionDefault
  if (settings["output-width"] === undefined) {
    if (!positiveInteger(input.display?.width) || !positiveInteger(input.display?.height)) {
      throw new ComposeError(
        "gamescope-output-size",
        "Gamescope requires output-width and output-height settings or a valid display hardware fact",
      )
    }
    settings["output-width"] = input.display.width
    settings["output-height"] = input.display.height
  }
  if (
    !isRecord(input.config) ||
    Object.keys(input.config).some(key => key !== "append") ||
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

interface Diagnostic {
  code: string
  severity: "error"
  message: string
  path: string[]
}
interface SettingsSchema {
  type: "object" | "integer" | "number" | "string" | "boolean"
  title: string
  description: string
  additionalProperties?: false
  properties?: Record<string, SettingsSchema>
  enum?: readonly string[]
  oneOf?: { const: string; title: string }[]
  minimum?: number
  maximum?: number
  default?: boolean
  dependentRequired?: Record<string, string[]>
}
const touchModes = ["hover", "left", "right", "middle", "passthrough", "disabled", "trackpad"]
const inverted = new Set(["disable-color-management", "disable-xres"])
const nativeByPath = new Map(Object.entries(settingsPaths).map(([key, path]) => [path, key]))

function nativeValue(key: string, value: unknown): unknown {
  if (key === "default-touch-mode" && typeof value === "string") return touchModes.indexOf(value)
  return inverted.has(key) && typeof value === "boolean" ? !value : value
}

function readSettings(
  values: unknown,
  path: string[] = [],
  found: Record<string, unknown> = {},
  diagnostics: Diagnostic[] = [],
) {
  const dotted = path.join(".")
  const key = nativeByPath.get(dotted)
  if (key !== undefined) {
    const error =
      key === "default-touch-mode"
        ? typeof values === "string" && touchModes.includes(values)
          ? undefined
          : `Gamescope setting ${dotted} must be one of: ${touchModes.join(", ")}`
        : settingError(dotted, settingsRules[key], values)
    if (error)
      diagnostics.push({ code: "gamescope-setting", severity: "error", message: error, path })
    else found[key] = nativeValue(key, values)
  } else if (!isRecord(values)) {
    diagnostics.push({
      code: "gamescope-setting",
      severity: "error",
      message: `${dotted || "Gamescope settings"} must be an object`,
      path,
    })
  } else {
    for (const name of Object.keys(values).sort()) {
      const next = [...path, name]
      const prefix = next.join(".")
      if (
        name.includes(".") ||
        ![...nativeByPath.keys()].some(
          candidate => candidate === prefix || candidate.startsWith(`${prefix}.`),
        )
      ) {
        diagnostics.push({
          code: "gamescope-setting",
          severity: "error",
          message: `Unknown Gamescope setting: ${prefix}`,
          path: next,
        })
      } else readSettings(values[name], next, found, diagnostics)
    }
  }
  return { found, diagnostics }
}

function checkedSettings(values: unknown) {
  const result = readSettings(values)
  // Invalid dimensions invalidate their valid mate too: korrid removes every
  // error path once, then compose can use the display fact for output size.
  for (const [width, height] of [
    ["output-width", "output-height"],
    ["nested-width", "nested-height"],
  ]) {
    const w = result.found[width] !== undefined
    const h = result.found[height] !== undefined
    if (w !== h) {
      const key = w ? width : height
      result.diagnostics.push({
        code: "gamescope-setting-pair",
        severity: "error",
        path: settingsPaths[key].split("."),
        message: `Gamescope settings ${settingsPaths[width]} and ${settingsPaths[height]} must be given as a pair`,
      })
    }
  }
  return result
}

function acceptedSettings(values: unknown): Record<string, unknown> {
  const { found, diagnostics } = checkedSettings(values)
  for (const diagnostic of diagnostics) {
    const key = nativeByPath.get(diagnostic.path.join("."))
    if (key !== undefined) delete found[key]
  }
  return found
}

export function validateSettings(input: { values?: unknown; revision?: string }) {
  const { diagnostics } = checkedSettings(input.values === undefined ? {} : input.values)
  return { valid: diagnostics.length === 0, diagnostics }
}

export function describeSettings(_input: { id: string }) {
  const section = (title: string): SettingsSchema => ({
    type: "object",
    title,
    description: `${title} settings for Gamescope.`,
    properties: {},
    additionalProperties: false,
  })
  const schema = section("Gamescope")
  for (const [key, path] of Object.entries(settingsPaths)) {
    const names = path.split(".")
    let parent = schema
    for (const name of names.slice(0, -1)) {
      parent.properties ??= {}
      const properties = parent.properties
      properties[name] ??= section(name.replace(/-/g, " "))
      parent = properties[name]
    }
    const rule = settingsRules[key]
    const title = names[names.length - 1].replace(/-/g, " ")
    const leaf: SettingsSchema = {
      type:
        rule.kind === "float"
          ? "number"
          : rule.kind === "path" || rule.kind === "choice"
            ? "string"
            : rule.kind,
      title,
      description: `Gamescope --${key}${inverted.has(key) ? " (inverted positive switch)" : ""}.${rule.kind === "string" ? ` Accepts ${rule.accepts}.` : ""}`,
    }
    if (rule.kind === "integer" || rule.kind === "float") {
      leaf.minimum = rule.minimum
      leaf.maximum = rule.maximum
    }
    if (rule.kind === "choice") leaf.enum = rule.choices
    if (key === "default-touch-mode") {
      leaf.type = "string"
      leaf.enum = touchModes
      delete leaf.minimum
      delete leaf.maximum
    }
    if (leaf.enum)
      leaf.oneOf = leaf.enum.map(value => ({ const: value, title: value.replace(/-/g, " ") }))
    if (key === "force-composition") leaf.default = forceCompositionDefault
    parent.properties ??= {}
    parent.properties[names[names.length - 1]] = leaf
  }
  const video = schema.properties?.video.properties
  if (video === undefined) throw new Error("Gamescope schema is missing its video section")
  for (const surface of ["output", "nested"]) {
    video[surface].dependentRequired = {
      width: ["height"],
      height: ["width"],
    }
  }
  return { schema, revision: "3.16.31" }
}

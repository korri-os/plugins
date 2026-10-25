// Mirrors the approved nested-settings treaty; keep the pinned Korri input.
type SettingValue = string | number | boolean
export interface SettingsDescribeInput {
  id: string
}
export interface SettingsValidateInput {
  values: Record<string, unknown>
  revision?: string
}
export interface SettingsRenderInput {
  id: string
  settings: Record<string, unknown>
  display?: { width: number; height: number }
}
export interface Diagnostic {
  code: string
  severity: "error"
  path: string[]
  message: string
}
export interface Schema {
  type: "object" | "integer" | "number" | "string" | "boolean"
  title: string
  description?: string
  properties?: Record<string, Schema>
  additionalProperties?: false
  enum?: readonly SettingValue[]
  minimum?: number
  maximum?: number
  default?: SettingValue
  pattern?: string
}
interface ObjectSchema extends Schema {
  type: "object"
  properties: Record<string, Schema>
  additionalProperties: false
}
interface Rule {
  schema: Schema
  args: (value: SettingValue) => string[]
}
const intMax = 2_147_483_647
const revision = "2"
const integer = (minimum = 0, maximum = intMax): Schema => ({
  type: "integer",
  title: "",
  minimum,
  maximum,
})
const choice = (values: readonly SettingValue[]): Schema => ({
  type: typeof values[0] === "number" ? "integer" : "string",
  title: "",
  enum: values,
})
const boolean = (): Schema => ({ type: "boolean", title: "" })
const title = (key: string) =>
  key.replaceAll("-", " ").replace(/^./, (letter) => letter.toUpperCase())
const object = (name: string): ObjectSchema => ({
  type: "object",
  title: name,
  properties: {},
  additionalProperties: false,
})
function schemaForRules(): ObjectSchema {
  const root = object("Settings")
  for (const [path, rule] of Object.entries(rules)) {
    const parts = path.split(".")
    let properties = root.properties
    for (const section of parts.slice(0, -1)) {
      if (!Object.hasOwn(properties, section)) properties[section] = object(title(section))
      const child = properties[section]
      if (child.properties === undefined)
        throw new Error(`Setting section overlaps a leaf: ${path}`)
      properties = child.properties
    }
    const key = parts[parts.length - 1]
    properties[key] = {
      ...rule.schema,
      title: title(key),
      description: rule.schema.description ?? `Sets ${path}.`,
    }
  }
  return root
}
function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
}
function accepts(schema: Schema, value: unknown): value is SettingValue {
  if (schema.type === "integer" || schema.type === "number") {
    if (
      typeof value !== "number" ||
      !Number.isFinite(value) ||
      (schema.type === "integer" && !Number.isInteger(value))
    )
      return false
    if (schema.minimum !== undefined && value < schema.minimum) return false
    if (schema.maximum !== undefined && value > schema.maximum) return false
  } else if (typeof value !== schema.type) return false
  if (typeof value === "string" && /[\0\r\n]/.test(value)) return false
  return !schema.enum || schema.enum.some((item) => item === value)
}
function collect(values: unknown): {
  settings: Map<string, SettingValue>
  diagnostics: Diagnostic[]
} {
  const settings = new Map<string, SettingValue>()
  const diagnostics: Diagnostic[] = []
  function walk(value: unknown, schema: Schema, path: string[]): void {
    if (schema.type === "object") {
      if (!record(value)) {
        diagnostics.push({
          code: "setting-type",
          severity: "error",
          path,
          message: "Setting section must be an object",
        })
        return
      }
      const properties = schema.properties ?? {}
      for (const [key, child] of Object.entries(value)) {
        if (!Object.hasOwn(properties, key))
          diagnostics.push({
            code: "setting-unknown",
            severity: "error",
            path: [...path, key],
            message: "Unknown setting",
          })
        else walk(child, properties[key], [...path, key])
      }
    } else if (!accepts(schema, value)) {
      diagnostics.push({
        code: "setting-value",
        severity: "error",
        path,
        message: `Expected ${schema.type}${schema.enum ? ` (${schema.enum.join(", ")})` : ""}${schema.minimum !== undefined ? `, minimum ${schema.minimum}` : ""}${schema.maximum !== undefined ? `, maximum ${schema.maximum}` : ""}; strings must not contain NUL or line breaks`,
      })
    } else settings.set(path.join("."), value)
  }
  walk(values, schemaForRules(), [])
  return { settings, diagnostics }
}
function checkId(id: string): void {
  if (id !== contributionId) throw new Error(`Unknown settings contribution: ${id}`)
}
export function describeSettings(input: SettingsDescribeInput): {
  schema: ObjectSchema
  revision: string
} {
  checkId(input.id)
  return { schema: schemaForRules(), revision }
}

const contributionId = "@korri:moonlight/moonlight"
const flag = (name: string) => (value: SettingValue) => [`-${name}`, String(value)]
const switchFlag =
  (name: string, when = true) =>
  (value: SettingValue) =>
    value === when ? [`-${name}`] : []
// moonlight-embedded 775444287305849ebdf4736c75298ad0713e2d5d,
// src/config.c long_options / parse_argument: integers parse into signed int.
const rules: Record<string, Rule> = {
  "video.resolution.width": { schema: integer(1), args: flag("width") },
  "video.resolution.height": { schema: integer(1), args: flag("height") },
  "video.fps": { schema: integer(1), args: flag("fps") },
  "video.bitrate-kbps": {
    schema: {
      ...integer(1),
      description:
        "Unset: twice Moonlight's native bitrate for the resolved size and fps (60 when unset). The RG35XX SP cedrus encoder looked soft at 3 Mbit/s, 640x480 (2026-10-25).",
    },
    args: flag("bitrate"),
  },
  "video.codec": {
    schema: { ...choice(["auto", "h264", "h265", "av1"]), default: "h264" },
    args: flag("codec"),
  },
  "video.hdr.enable": { schema: boolean(), args: switchFlag("hdr") },
  "video.rotation-degrees": { schema: choice([0, 90, 180, 270]), args: flag("rotate") },
  "video.optimize-game-settings": { schema: boolean(), args: switchFlag("nosops", false) },
  "video.allow-unsupported-resolution": {
    schema: boolean(),
    args: switchFlag("nounsupported", false),
  },
  "audio.channels": {
    schema: choice(["stereo", "5.1", "7.1"]),
    args: (value) => (value === "stereo" ? [] : flag("surround")(value)),
  },
  "audio.play-on-host": {
    schema: {
      ...boolean(),
      default: true,
      description: "Keep audio on the holder: the holder keeps playing and keeps its sound.",
    },
    args: switchFlag("localaudio"),
  },
  "input.mouse-emulation": { schema: boolean(), args: switchFlag("nomouseemulation", false) },
  "network.remote-optimizations": {
    schema: choice(["auto", "on", "off"]),
    args: (value) => flag("remote")(value === "on" ? "yes" : value === "off" ? "no" : "auto"),
  },
  "network.packet-size-bytes": { schema: integer(1), args: flag("packetsize") },
  "logging.level": {
    schema: choice(["info", "verbose", "debug"]),
    args: (value) => (value === "info" ? [] : [`-${value}`]),
  },
}
function resolutionPair(settings: Map<string, SettingValue>, diagnostics: Diagnostic[]): void {
  const width = "video.resolution.width"
  const height = "video.resolution.height"
  if (settings.has(width) !== settings.has(height)) {
    for (const path of [width, height]) {
      diagnostics.push({
        code: "setting-pair",
        severity: "error",
        path: path.split("."),
        message: "Resolution width and height must be set together",
      })
      settings.delete(path)
    }
  }
}
export function validateSettings(input: SettingsValidateInput): {
  valid: boolean
  diagnostics: Diagnostic[]
} {
  const { settings, diagnostics } = collect(input.values)
  resolutionPair(settings, diagnostics)
  return { valid: diagnostics.length === 0, diagnostics }
}
// config.c at the pinned revision: pixel bands and kbps per 30 fps.
// Twice the native default: cedrus looked soft at 640x480, 2026-10-25.
function defaultBitrate(settings: Map<string, SettingValue>): number {
  const width = settings.get("video.resolution.width")
  const height = settings.get("video.resolution.height")
  const fps = settings.get("video.fps")
  // With no display fact, match Moonlight's own 1280x720 / 60 defaults.
  const pixels =
    (typeof width === "number" ? width : 1280) * (typeof height === "number" ? height : 720)
  const base =
    pixels <= 640 * 360
      ? 1000
      : pixels <= 854 * 480
        ? 1500
        : pixels <= 1366 * 768
          ? 5000
          : pixels <= 1920 * 1200
            ? 10000
            : pixels <= 2560 * 1600
              ? 20000
              : 40000
  return 2 * Math.trunc(base * ((typeof fps === "number" ? fps : 60) / 30))
}
export function renderSettings(input: SettingsRenderInput): { args: string[] } {
  checkId(input.id)
  const { settings, diagnostics } = collect(input.settings)
  resolutionPair(settings, diagnostics)
  const display = input.display
  if (
    display !== undefined &&
    !settings.has("video.resolution.width") &&
    accepts(rules["video.resolution.width"].schema, display.width) &&
    accepts(rules["video.resolution.height"].schema, display.height)
  ) {
    settings.set("video.resolution.width", display.width)
    settings.set("video.resolution.height", display.height)
  }
  if (!settings.has("video.bitrate-kbps"))
    settings.set("video.bitrate-kbps", defaultBitrate(settings))
  const args: string[] = []
  for (const [path, rule] of Object.entries(rules)) {
    const value = settings.get(path) ?? rule.schema.default
    if (value !== undefined) args.push(...rule.args(value))
  }
  return { args }
}

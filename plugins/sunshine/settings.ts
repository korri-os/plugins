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
const revision = "1"
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

const contributionId = "@korri:sunshine/sunshine"
const native = (key: string) => (value: SettingValue) => [
  `${key}=${typeof value === "boolean" ? (value ? "enabled" : "disabled") : value}`,
]
const codes = (key: string, names: readonly string[]) => (value: SettingValue) => [
  `${key}=${names.indexOf(String(value))}`,
]
const codecModes = ["auto", "off", "main", "main10"]
const encryptionModes = ["off", "supported", "required"]
// Sunshine v2025.924.154138 docs/configuration.md / src/config.cpp.
// Patch 0037 adds offset 0..1000; patches 0021/0022 add ARM encoders.
const rules: Record<string, Rule> = {
  "logging.level": {
    schema: choice(["none", "fatal", "error", "warning", "info", "debug", "verbose"]),
    args: native("min_log_level"),
  },
  "input.controller": { schema: boolean(), args: native("controller") },
  "input.gamepad": { schema: choice(["auto", "ds5", "switch", "xone"]), args: native("gamepad") },
  "input.motion-as-ds4": { schema: boolean(), args: native("motion_as_ds4") },
  "input.touchpad-as-ds4": { schema: boolean(), args: native("touchpad_as_ds4") },
  "input.ds5-random-mac": { schema: boolean(), args: native("ds5_inputtino_randomize_mac") },
  "input.back-button-timeout-ms": {
    schema: {
      ...integer(-1),
      description: "Hold Back for this many milliseconds to emulate Guide; -1 disables emulation.",
    },
    args: native("back_button_timeout"),
  },
  "input.keyboard": { schema: boolean(), args: native("keyboard") },
  "input.key-repeat.delay-ms": { schema: integer(), args: native("key_repeat_delay") },
  "input.key-repeat.rate-hz": {
    schema: { type: "number", title: "", minimum: 0, maximum: Number.MAX_VALUE },
    args: native("key_repeat_frequency"),
  },
  "input.right-alt-as-windows-key": { schema: boolean(), args: native("key_rightalt_to_key_win") },
  "input.mouse": { schema: boolean(), args: native("mouse") },
  "input.high-resolution-scrolling": {
    schema: boolean(),
    args: native("high_resolution_scrolling"),
  },
  "input.pen-touch": { schema: boolean(), args: native("native_pen_touch") },
  "audio.enable": { schema: boolean(), args: native("stream_audio") },
  "video.max-bitrate-kbps": {
    schema: {
      ...integer(),
      description: "Maximum stream bitrate in kbps; 0 uses the client's request.",
    },
    args: native("max_bitrate"),
  },
  "video.minimum-fps": { schema: integer(0, 1000), args: native("minimum_fps_target") },
  "video.encoder.name": {
    schema: choice(["nvenc", "quicksync", "amdvce", "vaapi", "software", "v4l2m2m", "rkmpp"]),
    args: native("encoder"),
  },
  "video.encoder.fec-percent": { schema: integer(1, 255), args: native("fec_percentage") },
  "video.encoder.qp": { schema: integer(), args: native("qp") },
  "video.encoder.min-threads": { schema: integer(1), args: native("min_threads") },
  "video.encoder.hevc": { schema: choice(codecModes), args: codes("hevc_mode", codecModes) },
  "video.encoder.av1": { schema: choice(codecModes), args: codes("av1_mode", codecModes) },
  "video.encoder.software.preset": {
    schema: choice([
      "ultrafast",
      "superfast",
      "veryfast",
      "faster",
      "fast",
      "medium",
      "slow",
      "slower",
      "veryslow",
    ]),
    args: native("sw_preset"),
  },
  "video.encoder.software.tune": {
    schema: choice(["film", "animation", "grain", "stillimage", "fastdecode", "zerolatency"]),
    args: native("sw_tune"),
  },
  "video.capture.vblank-offset-ms": {
    schema: integer(0, 1000),
    args: native("capture_vblank_offset_ms"),
  },
  "network.address-family": { schema: choice(["ipv4", "both"]), args: native("address_family") },
  "network.external-ip": {
    schema: {
      type: "string",
      title: "",
      pattern: "^[^\\u0000\\r\\n]*$",
      description: "External IP address; an empty string lets Sunshine detect it.",
    },
    args: native("external_ip"),
  },
  "network.lan-encryption": {
    schema: choice(encryptionModes),
    args: codes("lan_encryption_mode", encryptionModes),
  },
  "network.wan-encryption": {
    schema: choice(encryptionModes),
    args: codes("wan_encryption_mode", encryptionModes),
  },
  "network.ping-timeout-ms": { schema: integer(-1), args: native("ping_timeout") },
}
export function validateSettings(input: SettingsValidateInput): {
  valid: boolean
  diagnostics: Diagnostic[]
} {
  const { diagnostics } = collect(input.values)
  return { valid: diagnostics.length === 0, diagnostics }
}
export function renderSettings(input: SettingsRenderInput): { args: string[] } {
  checkId(input.id)
  const { settings } = collect(input.settings)
  const args: string[] = []
  for (const [path, rule] of Object.entries(rules)) {
    const value = settings.get(path)
    if (value !== undefined) args.push(...rule.args(value))
  }
  return { args }
}

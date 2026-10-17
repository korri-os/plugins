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

type Rule = { minimum: number; maximum?: number } | { choices: readonly string[] }
// Gamescope 3.16.18 src/main.cpp: getopt long options and scaler/filter parsers.
// This order is also the argv order. Native append words follow all typed flags.
const settingsRules: Record<string, Rule> = {
  "output-width": { minimum: 1 },
  "output-height": { minimum: 1 },
  "nested-width": { minimum: 1 },
  "nested-height": { minimum: 1 },
  "nested-refresh": { minimum: 1 },
  scaler: { choices: ["auto", "integer", "fit", "fill", "stretch"] },
  filter: { choices: ["linear", "nearest", "fsr", "nis", "pixel"] },
  sharpness: { minimum: 0, maximum: 20 },
  "framerate-limit": { minimum: 0 },
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
    const rule = settingsRules[key]
    const value = input.settings[key]
    if ("choices" in rule) {
      if (typeof value !== "string" || !rule.choices.includes(value)) {
        throw new ComposeError("gamescope-setting", `Gamescope setting ${key} must be one of: ${rule.choices.join(", ")}`)
      }
    } else if (
      typeof value !== "number" || !Number.isSafeInteger(value) ||
      value < rule.minimum || (rule.maximum !== undefined && value > rule.maximum)
    ) {
      throw new ComposeError("gamescope-setting", `Gamescope setting ${key} must be an integer ${rule.minimum}..${rule.maximum ?? "MAX_SAFE_INTEGER"}`)
    }
  }
  const settings = { ...input.settings }
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
    if (settings[key] !== undefined) args.push(`--${key}`, String(settings[key]))
  }
  args.push(...appendWords(input.config.append ?? ""), "--", input.plan.command, ...input.plan.args)
  return { ...input.plan, command, args }
}

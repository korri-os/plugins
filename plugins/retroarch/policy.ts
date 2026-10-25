// The legacy nested policy, renamed by ADR 0037 / the 2026-10-25 brief.
// JSON Schema is the runtime source of truth: no Effect dependency is needed
// in the empty plugin sandbox. Renderer types derive from this same schema.
export type LaunchSettingValue = string | number | boolean

export interface SettingSchema {
  readonly type: "object" | "string" | "number" | "integer" | "boolean"
  readonly title?: string
  readonly description?: string
  readonly properties?: Readonly<Record<string, SettingSchema>>
  readonly patternProperties?: Readonly<Record<string, SettingSchema>>
  readonly additionalProperties?: false
  readonly enum?: readonly string[]
  readonly oneOf?: readonly { readonly const: string; readonly title: string }[]
  readonly minimum?: number
  readonly maximum?: number
  readonly exclusiveMinimum?: number
  readonly minLength?: number
  readonly default?: LaunchSettingValue
  readonly dependentRequired?: Readonly<Record<string, readonly string[]>>
}

function section<const P extends Record<string, SettingSchema>>(
  properties: P,
  pairs: readonly (readonly [string, string])[] = [],
) {
  return {
    type: "object",
    properties,
    additionalProperties: false,
    ...(pairs.length
      ? {
          dependentRequired: Object.fromEntries(
            pairs.flatMap(([a, b]) => [
              [a, [b]],
              [b, [a]],
            ]),
          ),
        }
      : {}),
  } as const
}
const boolean = () => ({ type: "boolean" }) as const
const text = () => ({ type: "string", minLength: 1 }) as const
const number = (minimum?: number, maximum?: number, exclusive = false) =>
  ({
    type: "number",
    ...(minimum === undefined ? {} : exclusive ? { exclusiveMinimum: minimum } : { minimum }),
    ...(maximum === undefined ? {} : { maximum }),
  }) as const
const integer = (minimum: number) =>
  ({ type: "integer", minimum, maximum: Number.MAX_SAFE_INTEGER }) as const
const choice = <const E extends readonly string[]>(values: E) =>
  ({
    type: "string",
    enum: values,
    oneOf: values.map(value => ({
      const: value,
      title: value.replace(/-/g, " ").replace(/^./, c => c.toUpperCase()),
    })),
  }) as const
const ports = <const S extends SettingSchema>(schema: S) =>
  ({
    type: "object",
    patternProperties: { "^[1-9][0-9]*$": schema },
    additionalProperties: false,
  }) as const

type Values<S> = S extends { properties: infer P }
  ? { readonly [K in keyof P]?: Values<P[K]> }
  : S extends { patternProperties: infer P }
    ? { readonly [key: string]: Values<P[keyof P]> }
    : S extends { enum: readonly (infer E)[] }
      ? E
      : S extends { type: "boolean" }
        ? boolean
        : S extends { type: "number" | "integer" }
          ? number
          : string

export const RetroArchPolicy = section({
  logging: section({
    level: choice(["info", "verbose"]),
    "core-level": choice(["debug", "info", "warning", "error"]),
  }),
  lifecycle: section({
    "auto-overrides": { ...boolean(), default: false },
    "auto-remaps": { ...boolean(), default: false },
    "game-specific-options": { ...boolean(), default: false },
    "auto-shaders": { ...boolean(), default: false },
    "show-hidden-files": boolean(),
    "load-dummy-on-core-shutdown": boolean(),
    "history-list": boolean(),
    "performance-counters": boolean(),
    "all-users-control-menu": boolean(),
    "suspend-screensaver": boolean(),
    "sustained-performance-mode": boolean(),
    "game-mode": boolean(),
  }),
  drivers: section({
    input: text(),
    joypad: text(),
    video: text(),
    audio: text(),
    resampler: text(),
    camera: text(),
    location: text(),
    record: text(),
  }),
  video: section({
    fullscreen: boolean(),
    "windowed-fullscreen": boolean(),
    "refresh-rate-hz": number(0, undefined, true),
    vsync: boolean(),
    "aspect-ratio": choice(["config", "square", "core-provided", "custom", "full"]),
    "aspect-ratio-value": number(0, undefined, true),
    "force-aspect": boolean(),
    "crop-overscan": boolean(),
    smooth: boolean(),
    shader: section({ enable: boolean(), path: text(), "watch-files": boolean() }),
    hdr: section({
      enable: boolean(),
      "max-nits": number(0, undefined, true),
      "paper-white-nits": number(0, undefined, true),
      contrast: number(0, undefined, true),
      "expand-gamut": boolean(),
    }),
    recording: section({
      "post-filter": boolean(),
      gpu: boolean(),
    }),
    "gpu-screenshot": boolean(),
    sync: section({
      "hard-sync": boolean(),
      "hard-sync-frames": integer(0),
      "frame-delay-ms": number(0, 99),
      "frame-delay-auto": boolean(),
    }),
    resolution: section({ width: integer(0), height: integer(0) }, [["width", "height"]]),
    scaling: section({ scaler: choice(["auto", "integer"]), factor: number(0, undefined, true) }),
    stats: section({ fps: boolean(), memory: boolean(), "frame-count": boolean() }),
  }),
  audio: section({
    enable: boolean(),
    "menu-sounds": boolean(),
    mute: boolean(),
    "mixer-mute": boolean(),
    "latency-ms": number(0),
    "output-rate-hz": integer(1),
    sync: boolean(),
    "rate-control": section({ enable: boolean(), delta: number(0, undefined, true) }),
    "max-timing-skew": number(0, undefined, true),
    "volume-db": number(),
    "mixer-volume-db": number(),
    "resampler-quality": choice(["dont-care", "lowest", "lower", "normal", "higher", "highest"]),
  }),
  input: section({
    autodetect: boolean(),
    "max-users": integer(1),
    "poll-type-behavior": choice(["early", "normal", "late"]),
    "axis-threshold": number(0, 1),
    "analog-deadzone": number(0, 1),
    "analog-sensitivity": number(0, undefined, true),
    "remap-binds": boolean(),
    descriptors: section({
      "label-show": boolean(),
      "hide-unbound": boolean(),
    }),
    overlay: section({
      enable: boolean(),
      path: text(),
      opacity: number(0, 1),
      scale: number(0, undefined, true),
      "behind-menu": boolean(),
      "hide-in-menu": boolean(),
    }),
    "auto-game-focus": choice(["off", "on", "detect"]),
    "menu-toggle-combo": choice([
      "none",
      "down-y-l-r",
      "l3-r3",
      "l1-r1-start-select",
      "start-select",
      "l3-r",
      "l-r",
      "hold-start",
      "hold-select",
      "down-select",
      "l2-r2",
    ]),
    "quit-combo": choice([
      "none",
      "down-y-l-r",
      "l3-r3",
      "l1-r1-start-select",
      "start-select",
      "l3-r",
      "l-r",
      "hold-start",
      "hold-select",
      "down-select",
      "l2-r2",
    ]),
    ports: ports(
      section({
        "libretro-device": integer(0),
        "joypad-index": integer(0),
        "analog-dpad-mode": choice([
          "none",
          "left-analog",
          "right-analog",
          "left-analog-forced",
          "right-analog-forced",
        ]),
      }),
    ),
  }),
  menu: section({
    "show-start-screen": boolean(),
    "pause-core": boolean(),
    mouse: boolean(),
    pointer: boolean(),
    clock: boolean(),
    "battery-level": boolean(),
    "core-name": boolean(),
    "dynamic-wallpaper": boolean(),
    wallpaper: text(),
    "screensaver-timeout-seconds": integer(0),
  }),
  saves: section({
    "autosave-interval-seconds": integer(0),
    "auto-load-state": boolean(),
    "auto-save-state": boolean(),
    "auto-index": boolean(),
    "max-keep": integer(0),
    thumbnail: boolean(),
    "sort-savefiles": boolean(),
    "sort-savestates": boolean(),
    "block-sram-overwrite": boolean(),
    "save-file-compression": boolean(),
    "state-file-compression": boolean(),
  }),
  rewind: section({
    enable: boolean(),
    granularity: integer(1),
    "buffer-size-mb": integer(1),
    "buffer-size-step-mb": integer(1),
    "auto-stride": boolean(),
  }),
  playback: section({
    "pause-when-inactive": boolean(),
    "pause-on-disconnect": boolean(),
    "slowmotion-ratio": number(0, undefined, true),
    "fastforward-ratio": number(0),
    "fastforward-frameskip": boolean(),
  }),
  latency: section({
    "run-ahead": section({
      enable: boolean(),
      frames: integer(0),
      "secondary-instance": boolean(),
      "hide-warnings": boolean(),
    }),
    "preemptive-frames": section({
      enable: boolean(),
      frames: integer(0),
    }),
  }),
  achievements: section({
    enable: boolean(),
    username: text(),
    hardcore: boolean(),
    badges: boolean(),
    "rich-presence": boolean(),
    "test-unofficial": boolean(),
  }),
  haptics: section({
    "vibrate-on-keypress": boolean(),
    "device-vibration": boolean(),
  }),
  playlists: section({
    "use-old-format": boolean(),
  }),
  privacy: section({
    "camera-device": text(),
    camera: boolean(),
    location: boolean(),
  }),
  updater: section({
    "show-online-updater": boolean(),
    "show-core-updater": boolean(),
    "auto-extract-archive": boolean(),
  }),
})

export type RetroArchPolicy = Values<typeof RetroArchPolicy>

export interface Diagnostic {
  code: string
  severity: "error" | "warning" | "info"
  message: string
  path?: string[]
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

// Invalid authored leaves stay in storage. Errors name paths, never values;
// korrid skips those paths before launch. Renderers also defend this boundary.
export function validatePolicy(
  values: unknown,
  schema: SettingSchema = RetroArchPolicy,
  path: string[] = [],
): Diagnostic[] {
  const fail = (message: string): Diagnostic[] => [
    { code: "setting-value", severity: "error", path, message },
  ]
  if (schema.type === "object") {
    if (!isRecord(values)) return fail(`${path.join(".") || "Settings"} must be an object`)
    const diagnostics: Diagnostic[] = []
    for (const key of Object.keys(values).sort()) {
      const child = Object.hasOwn(schema.properties ?? {}, key)
        ? schema.properties?.[key]
        : Object.entries(schema.patternProperties ?? {}).find(([pattern]) =>
            new RegExp(pattern).test(key),
          )?.[1]
      if (!child || key.includes("."))
        diagnostics.push({
          code: "setting-unknown",
          severity: "error",
          path: [...path, key],
          message: `Unknown RetroArch setting: ${[...path, key].join(".")}`,
        })
      else diagnostics.push(...validatePolicy(values[key], child, [...path, key]))
    }
    for (const [key, dependencies] of Object.entries(schema.dependentRequired ?? {})) {
      if (
        Object.hasOwn(values, key) &&
        dependencies.some(
          other =>
            !Object.hasOwn(values, other) ||
            diagnostics.some(
              item => item.path?.length === path.length + 1 && item.path[path.length] === other,
            ),
        )
      )
        diagnostics.push({
          code: "setting-pair",
          severity: "error",
          path: [...path, key],
          message: `${[...path, key].join(".")} requires its width/height pair`,
        })
    }
    return diagnostics
  }
  if (typeof values !== (schema.type === "integer" ? "number" : schema.type))
    return fail(`${path.join(".")} must be ${schema.type}`)
  if (
    typeof values === "number" &&
    (!Number.isFinite(values) ||
      (schema.type === "integer" && !Number.isSafeInteger(values)) ||
      (schema.minimum !== undefined && values < schema.minimum) ||
      (schema.maximum !== undefined && values > schema.maximum) ||
      (schema.exclusiveMinimum !== undefined && values <= schema.exclusiveMinimum))
  )
    return fail(`${path.join(".")} is outside its numeric limits`)
  if (
    typeof values === "string" &&
    ((schema.minLength !== undefined && values.length < schema.minLength) ||
      (schema.enum !== undefined && !schema.enum.includes(values)))
  )
    return fail(`${path.join(".")} must be ${schema.enum?.join(" | ") ?? "a non-empty string"}`)
  return []
}

export function decodeRetroArchPolicy(input: unknown): RetroArchPolicy {
  const diagnostics = validatePolicy(input)
  if (diagnostics.length) throw new Error(diagnostics.map(item => item.message).join("; "))
  return input as RetroArchPolicy
}

// The runtime schema gets readable titles and descriptions at every node.
// This supplies readable labels for every object and leaf without a second schema.
export function titledSchema(schema: SettingSchema, title = "RetroArch"): SettingSchema {
  return {
    ...schema,
    title,
    description: schema.description ?? `${title} settings for RetroArch.`,
    ...(schema.properties
      ? {
          properties: Object.fromEntries(
            Object.entries(schema.properties).map(([key, child]) => [
              key,
              titledSchema(
                child,
                key.replace(/-/g, " ").replace(/^./, c => c.toUpperCase()),
              ),
            ]),
          ),
        }
      : {}),
    ...(schema.patternProperties
      ? {
          patternProperties: Object.fromEntries(
            Object.entries(schema.patternProperties).map(([key, child]) => [
              key,
              titledSchema(child, "Input port"),
            ]),
          ),
        }
      : {}),
  }
}

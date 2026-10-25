import { describe, expect, it } from "bun:test"
import {
  RetroArchPolicy,
  decodeRetroArchPolicy,
  validatePolicy,
  type SettingSchema,
} from "./policy"
import { renderRetroArchSettings } from "./render-settings"
import types from "./settings-types.json"

function sample(schema: unknown): unknown {
  const node = schema as {
    type: string
    properties?: Record<string, unknown>
    enum?: unknown[]
    minimum?: number
  }
  if (node.type === "object")
    return Object.fromEntries(
      Object.entries(node.properties ?? {}).map(([key, child]) => [key, sample(child)]),
    )
  if (node.enum) return node.enum[0]
  if (node.type === "string") return "example"
  if (node.type === "boolean") return false
  return Math.max(1, node.minimum ?? 0)
}

describe("nested RetroArch vocabulary", () => {
  it("keeps the evidence key/type table equal to actual renderer outputs", () => {
    const rendered = renderRetroArchSettings(decodeRetroArchPolicy(sample(RetroArchPolicy)))
    expect(
      Object.fromEntries(
        rendered.map(([key, value]) => [
          key,
          typeof value === "boolean" ? "Boolean" : typeof value === "number" ? "Number" : "String",
        ]),
      ),
    ).toEqual(types)
  })

  it("renders nested resolution, scaling, shader, stats, logging and named choices", () => {
    const pairs = Object.fromEntries(
      renderRetroArchSettings(
        decodeRetroArchPolicy({
          video: {
            resolution: { width: 640, height: 480 },
            scaling: { scaler: "integer", factor: 3 },
            "aspect-ratio": "core-provided",
            vsync: false,
            shader: { enable: true, path: "crt.glslp", "watch-files": false },
            stats: { fps: true },
            sync: { "frame-delay-ms": 4 },
          },
          logging: { level: "verbose", "core-level": "warning" },
          input: {
            "auto-game-focus": "detect",
            "quit-combo": "start-select",
            ports: { "2": { "joypad-index": 1, "analog-dpad-mode": "none" } },
          },
          audio: { "volume-db": -3, "rate-control": { enable: true, delta: 0.005 } },
        }),
      ),
    )
    expect(pairs).toMatchObject({
      video_fullscreen_x: 640,
      video_fullscreen_y: 480,
      video_scale_integer: true,
      video_scale: 3,
      aspect_ratio_index: 22,
      video_vsync: false,
      video_shader: "crt.glslp",
      video_shader_enable: true,
      video_shader_watch_files: false,
      fps_show: true,
      video_frame_delay: 4,
      log_verbosity: true,
      libretro_log_level: 2,
      input_auto_game_focus: 2,
      input_quit_gamepad_combo: 4,
      input_player2_joypad_index: 1,
      input_player2_analog_dpad_mode: 0,
      audio_volume: -3,
      audio_rate_control: true,
      audio_rate_control_delta: 0.005,
    })
  })

  it("rejects flat native keys, old names, owned paths and invalid values", () => {
    for (const value of [
      { video_vsync: true },
      { video: { vsync: "true" } },
      { video: { "refresh-rate-hz": 0 } },
      { input: { "analog-deadzone": 2 } },
      { video: { resolution: { width: 640 } } },
      { logging: { level: "debug" } },
      { audio: { device: "pipewire" } },
      { paths: { "savefile-directory": "/tmp" } },
      { updater: { "buildbot-url": "https://example.invalid" } },
      { saves: { "savefiles-in-content-dir": true } },
      { video: { "integer-scale": true } },
    ])
      expect(() => decodeRetroArchPolicy(value)).toThrow()
  })

  it("retains every named choice's native enum index", () => {
    for (const [index, name] of [
      "dont-care",
      "lowest",
      "lower",
      "normal",
      "higher",
      "highest",
    ].entries()) {
      // The loop below checks values in native enum order (DONTCARE starts at 0).
      const pairs = Object.fromEntries(
        renderRetroArchSettings(decodeRetroArchPolicy({ audio: { "resampler-quality": name } })),
      )
      expect(pairs.audio_resampler_quality).toBe(index)
    }
    for (const [index, mode] of [
      "none",
      "left-analog",
      "right-analog",
      "left-analog-forced",
      "right-analog-forced",
    ].entries()) {
      const pairs = Object.fromEntries(
        renderRetroArchSettings(
          decodeRetroArchPolicy({ input: { ports: { "1": { "analog-dpad-mode": mode } } } }),
        ),
      )
      expect(pairs.input_player1_analog_dpad_mode).toBe(index)
    }
    for (const [index, mode] of ["early", "normal", "late"].entries()) {
      const pairs = Object.fromEntries(
        renderRetroArchSettings(decodeRetroArchPolicy({ input: { "poll-type-behavior": mode } })),
      )
      expect(pairs.input_poll_type_behavior).toBe(index)
    }
    for (const [index, level] of ["debug", "info", "warning", "error"].entries()) {
      const pairs = Object.fromEntries(
        renderRetroArchSettings(decodeRetroArchPolicy({ logging: { "core-level": level } })),
      )
      expect(pairs.libretro_log_level).toBe(index)
    }
  })

  it("enforces each schema leaf's types, bounds, choices and non-empty strings", () => {
    function walk(schema: SettingSchema) {
      if (schema.type === "object") {
        expect(schema.additionalProperties).toBe(false)
        for (const child of [
          ...Object.values(schema.properties ?? {}),
          ...Object.values(schema.patternProperties ?? {}),
        ])
          walk(child)
        return
      }
      const valid = sample(schema)
      expect(validatePolicy(valid, schema)).toEqual([])
      expect(validatePolicy(null, schema)).toHaveLength(1)
      expect(validatePolicy({}, schema)).toHaveLength(1)
      if (schema.enum) {
        for (const choice of schema.enum) expect(validatePolicy(choice, schema)).toEqual([])
        expect(validatePolicy("not-a-choice", schema)).toHaveLength(1)
        expect(schema.oneOf?.map(item => item.const)).toEqual([...schema.enum])
        expect(schema.oneOf?.every(item => item.title.length > 0)).toBe(true)
      }
      if (schema.minimum !== undefined)
        expect(validatePolicy(schema.minimum - 1, schema)).toHaveLength(1)
      if (schema.maximum !== undefined)
        expect(validatePolicy(schema.maximum + 1, schema)).toHaveLength(1)
      if (schema.exclusiveMinimum !== undefined)
        expect(validatePolicy(schema.exclusiveMinimum, schema)).toHaveLength(1)
      if (schema.type === "integer") expect(validatePolicy(1.5, schema)).toHaveLength(1)
      if (schema.type === "number") expect(validatePolicy(Infinity, schema)).toHaveLength(1)
      if (schema.minLength) expect(validatePolicy("", schema)).toHaveLength(1)
    }
    walk(RetroArchPolicy)
  })
})

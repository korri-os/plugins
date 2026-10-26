import { describe, expect, test } from "bun:test"
import type { Schema } from "./settings"
import { handlers } from "./plugin"

const id = "@korri:sunshine/sunshine"
const render = (settings = {}) => handlers["settings.render"]({ id, settings }).args
const validate = (values: Record<string, unknown>) => handlers["settings.validate"]({ values })
const paths = [
  "logging.level",
  "input.controller",
  "input.gamepad",
  "input.motion-as-ds4",
  "input.touchpad-as-ds4",
  "input.ds5-random-mac",
  "input.back-button-timeout-ms",
  "input.keyboard",
  "input.key-repeat.delay-ms",
  "input.key-repeat.rate-hz",
  "input.right-alt-as-windows-key",
  "input.mouse",
  "input.high-resolution-scrolling",
  "input.pen-touch",
  "audio.enable",
  "video.max-bitrate-kbps",
  "video.minimum-fps",
  "video.encoder.name",
  "video.encoder.fec-percent",
  "video.encoder.qp",
  "video.encoder.min-threads",
  "video.encoder.hevc",
  "video.encoder.av1",
  "video.encoder.software.preset",
  "video.encoder.software.tune",
  "video.capture.vblank-offset-ms",
  "network.address-family",
  "network.external-ip",
  "network.lan-encryption",
  "network.wan-encryption",
  "network.ping-timeout-ms",
]
function leaves(schema: Schema, prefix = ""): string[] {
  if (schema.type !== "object") return [prefix]
  expect(schema.additionalProperties).toBe(false)
  return Object.entries(schema.properties ?? {}).flatMap(([key, child]) =>
    leaves(child, prefix ? `${prefix}.${key}` : key),
  )
}
const all = {
  logging: { level: "debug" },
  input: {
    controller: true,
    gamepad: "ds5",
    "motion-as-ds4": false,
    "touchpad-as-ds4": false,
    "ds5-random-mac": false,
    "back-button-timeout-ms": 2000,
    keyboard: true,
    "key-repeat": { "delay-ms": 400, "rate-hz": 30.5 },
    "right-alt-as-windows-key": true,
    mouse: false,
    "high-resolution-scrolling": false,
    "pen-touch": false,
  },
  audio: { enable: true },
  video: {
    "max-bitrate-kbps": 3000,
    "minimum-fps": 30,
    encoder: {
      name: "v4l2m2m",
      "fec-percent": 10,
      qp: 28,
      "min-threads": 2,
      hevc: "main",
      av1: "off",
      software: { preset: "superfast", tune: "zerolatency" },
    },
    capture: { "vblank-offset-ms": 2 },
  },
  network: {
    "address-family": "both",
    "external-ip": "203.0.113.7",
    "lan-encryption": "required",
    "wan-encryption": "supported",
    "ping-timeout-ms": 15000,
  },
}

describe("Sunshine nested launch service settings", () => {
  test("describes exactly the 31 approved leaves", () => {
    const { schema, revision } = handlers["settings.describe"]({ id })
    expect(leaves(schema)).toEqual(paths)
    expect(revision).not.toBe("")
  })
  test("validates and renders every setting as one native key=value argument", () => {
    expect(validate(all)).toEqual({ valid: true, diagnostics: [] })
    expect(render(all)).toEqual([
      "min_log_level=debug",
      "controller=enabled",
      "gamepad=ds5",
      "motion_as_ds4=disabled",
      "touchpad_as_ds4=disabled",
      "virtualhid_randomize_mac=disabled",
      "back_button_timeout=2000",
      "keyboard=enabled",
      "key_repeat_delay=400",
      "key_repeat_frequency=30.5",
      "key_rightalt_to_key_win=enabled",
      "mouse=disabled",
      "high_resolution_scrolling=disabled",
      "native_pen_touch=disabled",
      "stream_audio=enabled",
      "max_bitrate=3000",
      "minimum_fps_target=30",
      "encoder=v4l2m2m",
      "fec_percentage=10",
      "qp=28",
      "min_threads=2",
      "hevc_mode=2",
      "av1_mode=1",
      "sw_preset=superfast",
      "sw_tune=zerolatency",
      "capture_vblank_offset_ms=2",
      "address_family=both",
      "external_ip=203.0.113.7",
      "lan_encryption_mode=2",
      "wan_encryption_mode=1",
      "ping_timeout=15000",
    ])
    expect(render()).toEqual([])
  })
  test("maps all named native codes and patched encoders", () => {
    for (const [code, choice] of ["auto", "off", "main", "main10"].entries())
      expect(render({ video: { encoder: { hevc: choice, av1: choice } } })).toEqual([
        `hevc_mode=${code}`,
        `av1_mode=${code}`,
      ])
    for (const [code, choice] of ["off", "supported", "required"].entries())
      expect(render({ network: { "lan-encryption": choice, "wan-encryption": choice } })).toEqual([
        `lan_encryption_mode=${code}`,
        `wan_encryption_mode=${code}`,
      ])
    for (const name of ["v4l2m2m", "rkmpp"])
      expect(render({ video: { encoder: { name } } })).toEqual([`encoder=${name}`])
  })
  test("accepts sentinels and native bounds", () => {
    expect(
      validate({
        input: { "back-button-timeout-ms": -1, "key-repeat": { "delay-ms": 0, "rate-hz": 24.9 } },
        video: {
          "max-bitrate-kbps": 0,
          "minimum-fps": 0,
          encoder: { "fec-percent": 255 },
          capture: { "vblank-offset-ms": 1000 },
        },
      }).valid,
    ).toBe(true)
  })
  test("reports exact path segments for unknown and invalid values", () => {
    for (const [values, path] of [
      [{ video: { encoder: { hevc: 2 } } }, ["video", "encoder", "hevc"]],
      [{ network: { "lan-encryption": 2 } }, ["network", "lan-encryption"]],
      [
        { video: { capture: { "vblank-offset-ms": 1001 } } },
        ["video", "capture", "vblank-offset-ms"],
      ],
      [{ video: { "minimum-fps": 1001 } }, ["video", "minimum-fps"]],
      [{ input: { keyboard: "enabled" } }, ["input", "keyboard"]],
      [
        { input: { "key-repeat": { "rate-hz": Number.POSITIVE_INFINITY } } },
        ["input", "key-repeat", "rate-hz"],
      ],
      [{ network: { "external-ip": "address\nencoder=software" } }, ["network", "external-ip"]],
      [{ video: { surprise: true } }, ["video", "surprise"]],
      [{ "logging.level": "info" }, ["logging.level"]],
    ] as const) {
      const result = validate(values)
      expect(result.valid).toBe(false)
      expect(result.diagnostics).toContainEqual(
        expect.objectContaining({ severity: "error", path: [...path] }),
      )
      expect(render(values).every((arg) => /^[a-z0-9_]+=[^\r\n\0]*$/.test(arg))).toBe(true)
    }
  })
  test("does not describe or render any excluded native key", () => {
    const excluded = [
      "file_apps",
      "credentials_file",
      "pkey",
      "cert",
      "file_state",
      "log_path",
      "capture",
      "capture_rt_priority",
      "adapter_name",
      "output_name",
      "audio_sink",
      "virtual_sink",
      "port",
      "upnp",
      "origin_web_ui_allowed",
      "global_prep_cmd",
      "sunshine_name",
      "locale",
      "system_tray",
      "notify_pre_releases",
      "always_send_scancodes",
      "install_steam_audio_drivers",
      "ds4_back_as_touchpad_click",
      "keybindings",
      "vaapi_strict_rc_buffer",
      "dd_configuration_option",
      "dd_resolution_option",
      "dd_manual_resolution",
      "dd_refresh_rate_option",
      "dd_manual_refresh_rate",
      "dd_hdr_option",
      "dd_wa_hdr_toggle_delay",
      "dd_config_revert_delay",
      "dd_config_revert_on_disconnect",
      "dd_mode_remapping",
      "nvenc_preset",
      "nvenc_twopass",
      "nvenc_spatial_aq",
      "nvenc_vbv_increase",
      "nvenc_realtime_hags",
      "nvenc_latency_over_power",
      "nvenc_opengl_vulkan_on_dxgi",
      "nvenc_h264_cavlc",
      "qsv_preset",
      "qsv_coder",
      "qsv_slow_hevc",
      "amd_usage",
      "amd_rc",
      "amd_enforce_hrd",
      "amd_quality",
      "amd_preanalysis",
      "amd_vbaq",
      "amd_coder",
      "vt_coder",
      "vt_software",
      "vt_realtime",
    ]
    const values = Object.fromEntries(excluded.map((key) => [key, "injected"]))
    expect(render(values)).toEqual([])
    expect(validate(values).diagnostics).toHaveLength(excluded.length)
  })
  test("rejects a different contribution id", () => {
    expect(() => handlers["settings.describe"]({ id: "other" })).toThrow()
    expect(() => handlers["settings.render"]({ id: "other", settings: {} })).toThrow()
  })
})

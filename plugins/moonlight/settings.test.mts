import { describe, expect, test } from "bun:test"
import type { Schema } from "./settings"
import { handlers, runners } from "./plugin"

const id = "@korri:moonlight/moonlight"
const render = (settings = {}, display?: { width: number; height: number }) =>
  handlers["settings.render"]({ id, settings, display }).args
const validate = (values: Record<string, unknown>) => handlers["settings.validate"]({ values })
const paths = [
  "video.resolution.width",
  "video.resolution.height",
  "video.fps",
  "video.bitrate-kbps",
  "video.codec",
  "video.hdr.enable",
  "video.rotation-degrees",
  "video.optimize-game-settings",
  "video.allow-unsupported-resolution",
  "audio.channels",
  "audio.play-on-host",
  "input.mouse-emulation",
  "network.remote-optimizations",
  "network.packet-size-bytes",
  "logging.level",
]
function leaves(schema: Schema, prefix = ""): string[] {
  if (schema.type !== "object") return [prefix]
  expect(schema.additionalProperties).toBe(false)
  return Object.entries(schema.properties ?? {}).flatMap(([key, child]) =>
    leaves(child, prefix ? `${prefix}.${key}` : key),
  )
}

describe("Moonlight nested settings", () => {
  test("declares a non-local runner and exactly the 15 approved leaves", () => {
    expect(runners.moonlight).toEqual({ id, program: "moonlight" })
    const { schema, revision } = handlers["settings.describe"]({ id })
    expect(leaves(schema)).toEqual(paths)
    expect(revision).not.toBe("")
    expect(schema.properties.video.properties?.codec.default).toBe("h264")
    expect(schema.properties.audio.properties?.["play-on-host"].default).toBe(true)
    expect(schema.properties.audio.properties?.["play-on-host"].description).toContain("holder")
    expect(schema.properties.video.properties?.["bitrate-kbps"].description).toContain("twice")
  })
  test("renders every setting with the native flags", () => {
    const settings = {
      video: {
        resolution: { width: 854, height: 480 },
        fps: 30,
        "bitrate-kbps": 5000,
        codec: "h265",
        hdr: { enable: true },
        "rotation-degrees": 90,
        "optimize-game-settings": false,
        "allow-unsupported-resolution": false,
      },
      audio: { channels: "5.1", "play-on-host": true },
      input: { "mouse-emulation": false },
      network: { "remote-optimizations": "on", "packet-size-bytes": 1024 },
      logging: { level: "debug" },
    }
    expect(validate(settings)).toEqual({ valid: true, diagnostics: [] })
    expect(render(settings, { width: 1920, height: 1080 })).toEqual([
      "-width",
      "854",
      "-height",
      "480",
      "-fps",
      "30",
      "-bitrate",
      "5000",
      "-codec",
      "h265",
      "-hdr",
      "-rotate",
      "90",
      "-nosops",
      "-nounsupported",
      "-surround",
      "5.1",
      "-localaudio",
      "-nomouseemulation",
      "-remote",
      "yes",
      "-packetsize",
      "1024",
      "-debug",
    ])
  })
  test("uses display fallback, h264, doubled native bitrate and host audio without forcing fps", () => {
    expect(render({}, { width: 640, height: 480 })).toEqual([
      "-width",
      "640",
      "-height",
      "480",
      "-bitrate",
      "6000",
      "-codec",
      "h264",
      "-localaudio",
    ])
    expect(render()).toEqual(["-bitrate", "20000", "-codec", "h264", "-localaudio"])
    expect(render({}, { width: -1, height: 480 })).toEqual([
      "-bitrate",
      "20000",
      "-codec",
      "h264",
      "-localaudio",
    ])
  })
  test("renders positive switches, stereo, rotations, codecs and logging levels", () => {
    expect(
      render({
        video: {
          hdr: { enable: false },
          "optimize-game-settings": true,
          "allow-unsupported-resolution": true,
        },
        audio: { channels: "stereo", "play-on-host": false },
        input: { "mouse-emulation": true },
        logging: { level: "info" },
      }),
    ).toEqual(["-bitrate", "20000", "-codec", "h264"])
    expect(render({ audio: { channels: "7.1" }, logging: { level: "verbose" } })).toEqual([
      "-bitrate",
      "20000",
      "-codec",
      "h264",
      "-surround",
      "7.1",
      "-localaudio",
      "-verbose",
    ])
    for (const codec of ["auto", "h264", "h265", "av1"])
      expect(render({ video: { codec } })).toEqual([
        "-bitrate",
        "20000",
        "-codec",
        codec,
        "-localaudio",
      ])
    for (const rotation of [0, 90, 180, 270])
      expect(render({ video: { "rotation-degrees": rotation } })).toContain(String(rotation))
    for (const [choice, native] of [
      ["auto", "auto"],
      ["on", "yes"],
      ["off", "no"],
    ])
      expect(render({ network: { "remote-optimizations": choice } })).toEqual([
        "-bitrate",
        "20000",
        "-codec",
        "h264",
        "-localaudio",
        "-remote",
        native,
      ])
  })
  test("doubles the pinned native bitrate table at every pixel-band boundary", () => {
    for (const [width, height, bitrate] of [
      [640, 360, 2000],
      [641, 360, 3000],
      [854, 480, 3000],
      [855, 480, 10000],
      [1366, 768, 10000],
      [1367, 768, 20000],
      [1920, 1200, 20000],
      [1921, 1200, 40000],
      [2560, 1600, 40000],
      [2561, 1600, 80000],
    ]) {
      const args = render({ video: { resolution: { width, height }, fps: 30 } })
      expect(args[args.indexOf("-bitrate") + 1]).toBe(String(bitrate))
    }
    const args = render({ video: { fps: 59 } }, { width: 640, height: 360 })
    expect(args[args.indexOf("-bitrate") + 1]).toBe("3932")
  })
  test("uses explicit settings before display facts and leaves an explicit bitrate unchanged", () => {
    const args = render(
      { video: { resolution: { width: 640, height: 480 }, fps: 30 } },
      { width: 1920, height: 1080 },
    )
    expect(args[args.indexOf("-bitrate") + 1]).toBe("3000")
    expect(render({ video: { "bitrate-kbps": 1234 }, audio: { "play-on-host": false } })).toEqual([
      "-bitrate",
      "1234",
      "-codec",
      "h264",
    ])
  })
  test("reports invalid leaves, sections, unknown paths and width/height pairing", () => {
    for (const resolution of [{ width: 640 }, { height: 480 }, { width: 0, height: 480 }]) {
      const result = validate({ video: { resolution } })
      expect(result.valid).toBe(false)
      expect(result.diagnostics.map((d) => d.path)).toContainEqual(["video", "resolution", "width"])
      expect(result.diagnostics.map((d) => d.path)).toContainEqual([
        "video",
        "resolution",
        "height",
      ])
    }
    for (const values of [
      { video: { fps: 0 } },
      { video: { fps: 30.5 } },
      { video: { fps: Number.NaN } },
      { video: { codec: "hevc" } },
      { video: { "rotation-degrees": 45 } },
      { audio: { channels: 5.1 } },
      { video: false },
      { "video.fps": 30 },
      { video: { fps: null } },
    ]) {
      const result = validate(values)
      expect(result.valid).toBe(false)
      expect(result.diagnostics.every((d) => d.severity === "error" && d.path.length > 0)).toBe(
        true,
      )
    }
  })
  test("never emits Korri-owned or excluded flags even if supplied as settings", () => {
    const excluded = [
      "app",
      "keydir",
      "mapping",
      "platform",
      "input",
      "viewonly",
      "port",
      "windowed",
      "autowindowresize",
      "noautowindowresize",
      "quitappafter",
      "audio",
      "config",
      "save",
      "pin",
      "720",
      "1080",
      "4k",
    ]
    const args = render(Object.fromEntries(excluded.map((key) => [key, "injected"])))
    for (const flag of excluded) expect(args).not.toContain(`-${flag}`)
    expect(validate(Object.fromEntries(excluded.map((key) => [key, "injected"]))).valid).toBe(false)
  })
  test("rejects a different contribution id", () => {
    expect(() => handlers["settings.describe"]({ id: "other" })).toThrow()
    expect(() => handlers["settings.render"]({ id: "other", settings: {} })).toThrow()
  })
})

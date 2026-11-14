// The viewer keeps Moonlight's settings exactly (#435): the same schema,
// diagnostics and arguments, under the viewer's own runner. native-check.nix
// places this file beside the built viewer source, with Moonlight's plugin
// in ../moonlight.
import { describe, expect, test } from "bun:test"
import * as viewer from "./plugin"
import * as moonlight from "../moonlight/plugin"

const ids = { viewer: "@korri:viewer/viewer", moonlight: "@korri:moonlight/moonlight" }
const values: Record<string, unknown>[] = [
  {},
  { video: { codec: "h265", fps: 30, "bitrate-kbps": 6000 } },
  { video: { resolution: { width: 640, height: 480 }, hdr: { enable: true } } },
  { video: { resolution: { width: 640 } } },
  { video: { "rotation-degrees": 90, "optimize-game-settings": false } },
  { video: { "allow-unsupported-resolution": false, codec: "bad" } },
  { audio: { channels: "5.1", "play-on-host": false } },
  { input: { "mouse-emulation": false } },
  { network: { "remote-optimizations": "on", "packet-size-bytes": 1024 } },
  { logging: { level: "debug" } },
  { unknown: { setting: 1 } },
]
const displays = [undefined, { width: 1280, height: 720 }, { width: 640, height: 480 }]

describe("Korri viewer settings", () => {
  test("declare the viewer's own runner, program and setup unit", () => {
    expect(viewer.name).toBe("viewer")
    expect(viewer.runners).toEqual({ viewer: { program: "viewer" } })
    expect(viewer.services).toEqual(["korri-viewer-setup"])
  })

  test("describe Moonlight's schema and revision", () => {
    expect(viewer.handlers["settings.describe"]({ id: ids.viewer })).toEqual(
      moonlight.handlers["settings.describe"]({ id: ids.moonlight }),
    )
  })

  test("validate and render as Moonlight does, value for value", () => {
    for (const plugin of values) {
      expect(viewer.handlers["settings.validate"]({ values: { plugin } })).toEqual(
        moonlight.handlers["settings.validate"]({ values: { plugin } }),
      )
      for (const display of displays) {
        expect(
          viewer.handlers["settings.render"]({ id: ids.viewer, settings: { plugin }, display }),
        ).toEqual(
          moonlight.handlers["settings.render"]({ id: ids.moonlight, settings: { plugin }, display }),
        )
      }
    }
  })

  test("answer only for the viewer's runner", () => {
    expect(() => viewer.handlers["settings.describe"]({ id: ids.moonlight })).toThrow()
    expect(() =>
      viewer.handlers["settings.render"]({ id: ids.moonlight, settings: { plugin: {} } }),
    ).toThrow()
  })
})

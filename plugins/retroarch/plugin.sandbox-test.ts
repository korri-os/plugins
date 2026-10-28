// Runs inside settings-check.nix against the selected program's evidence.
import { afterAll, describe, expect, it } from "bun:test"
import { createHash } from "node:crypto"
import { mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { handlers } from "./plugin"
import type { SettingSchema } from "./policy"

const launch = handlers["launch.prepare"]
type PluginLaunchInput = Parameters<typeof launch>[0]

function input(overrides?: PluginLaunchInput["overrides"]): PluginLaunchInput {
  return {
    runnerId: "@korri:mgba/mgba",
    familyId: "@korri:retroarch",
    program: "/program",
    corePath: "/core",
    contentPath: "/rom",
    accountRoot: "/account",
    saveRoot: "/account/saves/wario-land-4",
    cacheRoot: "/cache",
    files: { autoconfig: "/autoconfig" },
    artifacts: {},
    overrides,
  }
}
function content(overrides?: PluginLaunchInput["overrides"]): string {
  return launch(input(overrides)).files[0].content
}
const reserved = [
  "cheevos_password",
  "cheevos_token",
  "network_cmd_password",
  "network_cmd_enable",
  "network_cmd_port",
  "netplay_password",
  "netplay_ip_port",
  "netplay_public_announce",
  "netplay_nat_traversal",
  "netplay_use_mitm_server",
  "netplay_spectate_password",
  "kiosk_mode_enable",
  "config_save_on_exit",
  "menu_driver",
]

describe("RetroArch netplay launch", () => {
  for (const netplay of [
    { role: "host", passwordConfig: "/run/netplay/password.cfg" },
    {
      role: "client",
      address: "127.0.0.1",
      port: 42001,
      player: 2,
      passwordConfig: "/run/netplay/password.cfg",
    },
  ] as const) {
    it(`prepares the ${netplay.role} without reading the password file or exposing a secret`, () => {
      // This path does not exist. The effect-free handler must only pass it on.
      const plan = launch({ ...input(), netplay })
      expect(plan.args).toEqual([
        "--config",
        "/account/retroarch.cfg",
        ...(netplay.role === "client" ? ["--connect", "127.0.0.1", "--port", "42001"] : []),
        "--appendconfig",
        netplay.passwordConfig,
        "-L",
        "/core",
        "/rom",
      ])
      expect(plan.files).toHaveLength(1)
      expect(plan.files[0].content).not.toContain("netplay_password")
      expect(plan.args).not.toContain("netplay_password")
      expect(plan.files[0].content).toContain('network_cmd_enable = "true"')
      expect(plan.files[0].content).toContain('network_cmd_port = "55355"')
      expect(plan.files[0].content).toContain('netplay_ip_port = "55435"')
      for (const key of [
        "netplay_public_announce",
        "netplay_nat_traversal",
        "netplay_use_mitm_server",
      ])
        expect(plan.files[0].content).toContain(`${key} = "false"`)
    })
  }

  it("never puts the password file's contents in the declaration", () => {
    const root = mkdtempSync(join(tmpdir(), "korri-netplay-"))
    try {
      const passwordConfig = join(root, "password.cfg")
      const password = "netplay-test-secret-do-not-expose"
      writeFileSync(passwordConfig, `netplay_password = "${password}"\n`, { mode: 0o600 })
      for (const netplay of [
        { role: "host", passwordConfig },
        { role: "client", address: "127.0.0.1", port: 42001, player: 2, passwordConfig },
      ] as const) {
        const plan = launch({ ...input(), netplay })
        expect(JSON.stringify(plan)).not.toContain(password)
        expect(plan.args).toContain(passwordConfig)
      }
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })
})

describe("RetroArch nested settings operations", () => {
  it("keeps per-game saves, the core's state subfolder and the protected kiosk defaults", () => {
    const plan = launch(input())
    const root = input().saveRoot
    expect(plan.saveLocations).toEqual([
      { key: "saves", kind: "save", path: `${root}/saves` },
      { key: "states", kind: "savestate", path: `${root}/states` },
      { key: "screenshots", kind: "screenshot", path: `${root}/screenshots` },
    ])
    expect(plan.directories).toEqual([
      "/account/system",
      `${root}/saves`,
      `${root}/states/@korri:mgba/mgba`,
      `${root}/screenshots`,
    ])
    expect(plan.files[0].path).toBe("/account/retroarch.cfg")
    for (const pair of [
      `savefile_directory = "${root}/saves"`,
      `savestate_directory = "${root}/states/@korri:mgba/mgba"`,
      `screenshot_directory = "${root}/screenshots"`,
      'savestate_auto_save = "true"',
      'savestate_auto_load = "true"',
      'config_save_on_exit = "false"',
      'menu_driver = "null"',
      'kiosk_mode_enable = "true"',
    ])
      expect(plan.files[0].content).toContain(pair)
    expect(launch({ ...input(), saveRoot: "/other" }).files[0].content).not.toContain(root)
  })

  it("keeps managed saves even when raw config replaces them", () => {
    const root = input().saveRoot
    for (const [key, path] of Object.entries({
      savefile_directory: `${root}/saves`,
      savestate_directory: `${root}/states/@korri:mgba/mgba`,
      screenshot_directory: `${root}/screenshots`,
    })) {
      const cfg = content({
        config: { prepend: `${key} = "/custom/prepend"`, append: `${key} = "/custom/append"` },
      })
      expect(cfg).toContain(`${key} = "${path}"`)
      expect(cfg).not.toContain("/custom/")
    }
  })

  it("accepts the nested launch tree and renders verbose argv plus native verbosity", () => {
    const settings = {
      drivers: { video: "vulkan" },
      video: {
        resolution: { width: 640, height: 480 },
        scaling: { scaler: "integer", factor: 3 },
        stats: { fps: true },
      },
      logging: { level: "verbose", "core-level": "warning" },
      audio: { "volume-db": -3.5 },
    }
    const before = structuredClone(settings)
    expect(handlers["settings.validate"]({ values: settings }).valid).toBe(true)
    const plan = launch(input({ settings }))
    expect(plan.args).toEqual(["-v", "--config", "/account/retroarch.cfg", "-L", "/core", "/rom"])
    for (const pair of [
      'video_driver = "vulkan"',
      'video_scale_integer = "true"',
      "video_scale = 3",
      'fps_show = "true"',
      "video_fullscreen_x = 640",
      "video_fullscreen_y = 480",
      "libretro_log_level = 2",
      'log_verbosity = "true"',
      "audio_volume = -3.5",
    ])
      expect(plan.files[0].content).toContain(pair)
    expect(settings).toEqual(before)
    const info = launch(
      input({ settings: { logging: { level: "info" }, video: { scaling: { scaler: "auto" } } } }),
    )
    expect(info.args).not.toContain("-v")
    expect(info.files[0].content).toContain('log_verbosity = "false"')
    expect(info.files[0].content).toContain('video_scale_integer = "false"')
  })

  it("reports unknown, invalid, unsupported and Korri-owned paths without stopping launch", () => {
    for (const [settings, path] of [
      [{ video_driver: "vulkan" }, ["video_driver"]],
      [{ video: { "refresh-rate-hz": -1 } }, ["video", "refresh-rate-hz"]],
      [{ audio: { device: "secret" } }, ["audio", "device"]],
      [{ paths: { "savefile-directory": "/custom" } }, ["paths"]],
      [{ lifecycle: { "save-on-exit": true } }, ["lifecycle", "save-on-exit"]],
      [{ drivers: { menu: "ozone" } }, ["drivers", "menu"]],
      [{ video: { shader: { path: "secret" } } }, ["video", "shader", "path"]],
      [
        { input: { ports: { "1": { "joypad-index": 1 } } } },
        ["input", "ports", "1", "joypad-index"],
      ],
    ] as const) {
      const report = handlers["settings.validate"]({ values: settings })
      expect(report.valid).toBe(false)
      expect(
        report.diagnostics.some(item => JSON.stringify(item.path) === JSON.stringify(path)),
      ).toBe(true)
      expect(JSON.stringify(report)).not.toContain("secret")
      expect(() => content({ settings })).not.toThrow()
    }
    for (const scaler of ["fit", "fill", "stretch"]) {
      const settings = { video: { scaling: { scaler }, "refresh-rate-hz": 60 } }
      expect(handlers["settings.validate"]({ values: settings }).diagnostics[0].path).toEqual([
        "video",
        "scaling",
        "scaler",
      ])
      expect(content({ settings })).not.toContain("video_scale_integer")
      expect(content({ settings })).toContain("video_refresh_rate = 60")
    }
  })

  it("reports bad pairs, nested malformed sections, limits and dotted names at their paths", () => {
    for (const values of [
      { video: { resolution: { width: 640 } } },
      { video: { "stats.fps": true } },
      { input: { "analog-deadzone": 2 } },
      { video: false },
      { video: { hdr: [] } },
      { audio: null },
    ]) {
      const report = handlers["settings.validate"]({ values })
      expect(report.valid).toBe(false)
      expect(
        report.diagnostics.every(
          item => item.severity === "error" && item.path !== undefined && item.path.length > 0,
        ),
      ).toBe(true)
    }
  })

  it("describes nested schema metadata, choices, limits and inherited safe defaults", () => {
    const described = handlers["settings.describe"]({ id: input().runnerId })
    expect(described.revision).toMatch(/^\d+\.\d+/)
    function walk(schema: SettingSchema) {
      expect(schema.title).toBeTruthy()
      expect(schema.description).toBeTruthy()
      if (schema.type === "object") {
        expect(schema.additionalProperties).toBe(false)
        for (const child of Object.values(schema.properties ?? {})) walk(child)
      }
    }
    walk(described.schema)
    const properties = described.schema.properties
    expect(properties?.video.properties?.scaling.properties?.scaler.enum).toEqual([
      "auto",
      "integer",
    ])
    expect(properties?.logging.properties?.["core-level"].enum).toEqual([
      "debug",
      "info",
      "warning",
      "error",
    ])
    expect(properties?.lifecycle.properties?.["auto-overrides"].default).toBe(false)
    expect(properties?.video.properties?.sync.properties?.["frame-delay-ms"].maximum).toBe(99)
    for (const key of ["environment", "paths", "configFile", "video_driver"])
      expect(properties?.[key]).toBeUndefined()
    expect(properties?.audio.properties?.device).toBeUndefined()
    expect(properties?.drivers.properties?.menu).toBeUndefined()
    expect(properties?.lifecycle.properties?.["save-on-exit"]).toBeUndefined()
    expect(
      handlers["settings.validate"]({ values: {}, revision: "old" }).diagnostics[0].severity,
    ).toBe("info")
  })

  it("emits one assignment per key with baseline < typed < prepend < append", () => {
    const cfg = content({
      settings: { drivers: { video: "vulkan" }, audio: { "volume-db": -3.5 } },
      config: {
        prepend: '# ignored\nvideo_driver = "sdl2"\naudio_volume = -2',
        append: 'video_driver = "glcore"\nvideo_driver = "gl1" # final',
      },
    })
    const keys = cfg
      .split("\n")
      .filter(line => line.includes(" = "))
      .map(line => line.split(" = ")[0])
    expect(new Set(keys).size).toBe(keys.length)
    expect(cfg).toContain('video_driver = "gl1" # final\n')
    expect(cfg).toContain("# generated by Korri\n")
    expect(cfg).not.toContain("# ignored")
  })

  it("never accepts a reserved native raw assignment, even if shadowed", () => {
    for (const key of reserved) {
      for (const block of ["prepend", "append"] as const)
        expect(() => content({ config: { [block]: `${key} = false\n${key} = true` } })).toThrow(key)
    }
    expect(() => launch({ ...input(), contentPath: undefined, ref: "123" })).toThrow(
      "requires a content file",
    )
  })

  it("keeps raw native syntax, rejects malformed assignments and replacement", () => {
    expect(
      content({
        config: { prepend: '\n #include "not-loaded.cfg"\n Future_key9 = "a#b" # comment\n' },
      }),
    ).toContain('Future_key9 = "a#b" # comment\n')
    for (const line of ["missing", "= value", "bad-key = value", "a b = value", "#skip\n[section]"])
      expect(() => content({ config: { append: line } })).toThrow("Invalid RetroArch")
    expect(() => content({ config: { replace: "" } })).toThrow("replace")
    expect(() =>
      content({ config: { append: "cheevos-password = private-token-marker" } }),
    ).toThrow(/^Invalid RetroArch overrides.config assignment$/)
  })

  it("warns and skips unsafe typed strings without logging their values, including shadowed values", () => {
    for (const value of [
      'device "quoted"',
      '"leading',
      'a"#unclosed',
      'a"b#outside',
      'é"x',
      "a\nb",
      "a\rb",
      "a\0b",
      "a\ud800b",
      "a\udfffb",
    ]) {
      const settings = { menu: { wallpaper: value } }
      const report = handlers["settings.validate"]({ values: settings })
      expect(report.valid).toBe(false)
      expect(report.diagnostics[0].path).toEqual(["menu", "wallpaper"])
      expect(report.diagnostics[0].message).toBe(
        "Unsupported RetroArch string setting: menu_wallpaper",
      )
      expect(content({ settings })).not.toContain("menu_wallpaper")
      expect(content({ settings, config: { append: 'menu_wallpaper = "valid"' } })).toContain(
        'menu_wallpaper = "valid"',
      )
    }
  })

  it("uses the same native string safety for generated directories and autoconfig", () => {
    for (const value of ['root "quoted"', "root\nnext", "root\0next"]) {
      expect(() => launch({ ...input(), accountRoot: value })).toThrow("system_directory")
      expect(() => launch({ ...input(), files: { autoconfig: value } })).toThrow(
        "joypad_autoconfig_dir",
      )
    }
  })
})

// The Nix gate always sets this to a build-machine executable compiled from the
// caller program's patched sources. Standalone TS tests cannot replace that gate.
const parser = process.env.KORRI_TEST_RETROARCH_CONFIG_PARSER
const directory = mkdtempSync(join(tmpdir(), "retroarch-config-"))
afterAll(() => rmSync(directory, { recursive: true, force: true }))
function parsed(cfg: string, keys: string[], env: Record<string, string> = {}): string[] {
  if (!parser) throw new Error("Native parser executable is required")
  const path = join(directory, "retroarch.cfg")
  writeFileSync(path, cfg)
  const result = Bun.spawnSync([parser, path, ...keys], { env: { ...process.env, ...env } })
  expect(result.exitCode).toBe(0)
  return result.stdout.toString().split("\0").slice(0, -1)
}

describe.skipIf(!parser)("pinned config_file_new/config_get_string semantics", () => {
  it("keeps federation-only transport ready when hosting starts during ordinary play", () => {
    expect(
      parsed(content(), [
        "network_cmd_enable",
        "network_cmd_port",
        "netplay_ip_port",
        "netplay_public_announce",
        "netplay_nat_traversal",
        "netplay_use_mitm_server",
      ]),
    ).toEqual(["true", "55355", "55435", "false", "false", "false"])
  })

  it("reads the per-game folders through the actual RetroArch parser", () => {
    const root = input().saveRoot
    expect(
      parsed(content(), ["savefile_directory", "savestate_directory", "screenshot_directory"]),
    ).toEqual([`${root}/saves`, `${root}/states/@korri:mgba/mgba`, `${root}/screenshots`])
  })

  it("proves the parser keeps the first duplicate and does not JSON-decode strings", () => {
    expect(parsed('video_driver = "gl"\nvideo_driver = "vulkan"\n', ["video_driver"])).toEqual([
      "gl",
    ])
    expect(
      parsed(`audio_device = ${JSON.stringify('device "quoted"')}\n`, ["audio_device"]),
    ).toEqual(["device \\"])
  })

  it("prefers each Korri seat pad for its own player", () => {
    // udev enumerates the persistent seat pads in sysfs-name order
    // (input10 before input8), so default order put Seat P3 on player 1.
    // Preferred reservation (type 1) matches the device name and leaves the
    // default order on hosts that have no seat pads.
    const keys = [1, 2, 3, 4].flatMap(player => [
      `input_player${player}_device_reservation_type`,
      `input_player${player}_reserved_device`,
    ])
    expect(parsed(content(), keys)).toEqual(
      [1, 2, 3, 4].flatMap(player => ["1", `Korri Seat P${player}`]),
    )
  })

  it("selects the X11 GL context by default and lets raw config replace it", () => {
    // Gamescope gives the game both Wayland and Xwayland; X11 keeps the picture 1:1.
    expect(parsed(content(), ["video_driver", "video_context_driver"])).toEqual(["gl", "x"])
    for (const [config, expected] of [
      [{ prepend: 'video_context_driver = "wayland"' }, "wayland"],
      [{ append: 'video_context_driver = "kms"' }, "kms"],
      [
        { prepend: 'video_context_driver = "wayland"', append: 'video_context_driver = "x_egl"' },
        "x_egl",
      ],
    ] as const) {
      const cfg = content({ config })
      expect(cfg.match(/^video_context_driver = /gm)).toHaveLength(1)
      expect(parsed(cfg, ["video_context_driver"])).toEqual([expected])
    }
  })

  it("applies baseline < typed < raw prepend < raw append in native lookups", () => {
    const settings = { drivers: { video: "vulkan" } }
    const prepend = 'video_driver = "ignored"\nvideo_driver = "sdl2"'
    const append = 'video_driver = "glcore"\nvideo_driver = "gl1" # final'
    for (const [overrides, expected] of [
      [undefined, "gl"],
      [{ settings }, "vulkan"],
      [{ settings, config: { prepend } }, "sdl2"],
      [{ settings, config: { prepend, append } }, "gl1"],
      [{ config: { append } }, "gl1"],
    ] as const) {
      expect(parsed(content(overrides), ["video_driver"])).toEqual([expected])
    }
    expect(
      parsed(
        content({
          settings: {
            video: { vsync: false, fullscreen: true },
            audio: { "volume-db": -3.5, "latency-ms": 0 },
          },
        }),
        [
          "video_vsync",
          "audio_volume",
          "video_fullscreen",
          "audio_latency",
          "config_save_on_exit",
          "kiosk_mode_enable",
          "menu_driver",
        ],
      ),
    ).toEqual(["false", "-3.5", "true", "0", "false", "true", "null"])
  })

  it("normalizes raw separators before replacing a native assignment", () => {
    for (const assignment of [
      'video_driver="vulkan"',
      'video_driver ="vulkan"',
      'video_driver= "vulkan"',
    ]) {
      expect(parsed(content({ config: { append: assignment } }), ["video_driver"])).toEqual([
        "vulkan",
      ])
    }
  })

  it("round-trips native strings, literal backslashes, whitespace, hashes and Unicode", () => {
    for (const value of [
      "device\\path\\n",
      "\\",
      " leading\tand trailing ",
      "a#b",
      "a=b",
      "café/🎮",
      'hw:"quoted"',
      'hw:"dev#1"',
    ]) {
      expect(
        parsed(content({ settings: { menu: { wallpaper: value } } }), ["menu_wallpaper"]),
      ).toEqual([value])
    }
    const request = input()
    request.accountRoot = "/account\\literal"
    request.files.autoconfig = "/autoconfig\\literal"
    expect(
      parsed(launch(request).files[0].content, ["system_directory", "joypad_autoconfig_dir"]),
    ).toEqual(["/account\\literal/system", "/autoconfig\\literal"])
    expect(
      parsed(content({ config: { append: 'audio_device = "native\\path#1" # comment' } }), [
        "audio_device",
      ]),
    ).toEqual(["native\\path#1"])
  })
})


describe("melonDS compositor touch", () => {
  it("uses the compositor for pointer input without changing the shared-seat joypad driver", () => {
    for (const overrides of [
      undefined,
      { settings: { drivers: { input: "udev" } } },
      { config: { append: 'input_driver = "linuxraw"' } },
    ]) {
      const plan = launch({ ...input(overrides), runnerId: "@korri:melonds/melonds" })
      expect(plan.files[0].content).toContain('input_driver = "x"\n')
      expect(plan.files[0].content).not.toContain('input_driver = "udev"')
      expect(plan.files[0].content).not.toContain('input_driver = "linuxraw"')
      expect(plan.files[0].content).toContain('input_joypad_driver = "udev"\n')
      expect(plan.files[0].content).toContain('config_save_on_exit = "false"\n')
      expect(plan.files[1]).toEqual({ path: "/account/melonds-layout.opt", content: 'melonds_threaded_renderer = "enabled"\nmelonds_touch_mode = "Touch"\n' })
      expect(plan.env).toEqual({ KORRI_RETROARCH_CORE_OPTIONS_OVERLAY: plan.files[1].path })
      expect(plan.files[0].content).not.toContain("melonds_touch_mode")
    }
  })

  it("keeps 54 other-core launch plans byte-identical to candidate 2f5aedc", () => {
    // Golden SHA-256 of the entire serialized plans from the previous candidate,
    // including native cfg bytes, custom input drivers, option routing and netplay.
    // Rebased once: the shared cfg now sets input_quit_gamepad_combo = "0" so
    // inputd's L1 + R1 + Start + Select hold is the only kill chord.
    const plans = []
    for (const runnerId of ["@korri:mgba/mgba", "@korri:snes9x/snes9x", "@korri:gambatte/gambatte"]) {
      for (const files of [{ autoconfig: "/autoconfig" }, { autoconfig: "/autoconfig", "core-info": "/core-info" }]) {
        for (const overrides of [undefined, {
          settings: { drivers: { input: "sdl2", joypad: "sdl2", video: "vulkan" }, audio: { "volume-db": -3.5 } },
        }, { config: { append: 'input_driver = "linuxraw"\ncore_options_path = "/person/custom.opt"\nglobal_core_options = "true"' } }]) {
          for (const netplay of [undefined, { role: "host", passwordConfig: "/run/password.cfg" }, {
            role: "client", address: "127.0.0.1", port: 42001, passwordConfig: "/run/password.cfg",
          }] satisfies (PluginLaunchInput["netplay"])[]) {
            plans.push(launch({ ...input(overrides), runnerId, files, netplay }))
          }
        }
      }
    }
    expect(plans).toHaveLength(54)
    expect(createHash("sha256").update(JSON.stringify(plans)).digest("hex"))
      .toBe("b4a2732e711453a59fc9762a80965e8c57e34e98b6cd528f206ac9e6c8ca24fd")
  })
})

describe("melonDS chosen layout", () => {
  for (const layout of ["Top/Bottom", "Left/Right", "Top Only", "Bottom Only"]) {
    it(`provisions ${layout} without changing the launch command`, () => {
      const request = { ...input(), runnerId: "@korri:melonds/melonds" }
      const unchanged = launch(request)
      const plan = launch({ ...request, layout })
      expect(plan.args).toEqual(unchanged.args)
      expect(plan.files).toHaveLength(2)
      expect(plan.files![0]).toEqual(unchanged.files![0])
      expect(plan.files![1].content).toBe(`melonds_screen_layout = "${layout}"\nmelonds_screen_gap = "0"\nmelonds_threaded_renderer = "enabled"\nmelonds_touch_mode = "Touch"\n`)
      expect(plan.env).toEqual({ KORRI_RETROARCH_CORE_OPTIONS_OVERLAY: plan.files![1].path })
    })
  }

  it("enables touch without forcing a layout when Core did not choose one", () => {
    const plan = launch({ ...input(), runnerId: "@korri:melonds/melonds" })
    expect(plan.files).toHaveLength(2)
    expect(plan.files[0].path).toBe("/account/retroarch.cfg")
    expect(plan.files[0].content).not.toContain("melonds_screen_")
    expect(plan.files[1].content).toBe('melonds_threaded_renderer = "enabled"\nmelonds_touch_mode = "Touch"\n')
    expect(plan.env).toEqual({ KORRI_RETROARCH_CORE_OPTIONS_OVERLAY: plan.files[1].path })
  })

  it("refuses layouts it cannot apply", () => {
    expect(() => launch({ ...input(), layout: "Top/Bottom" })).toThrow("layout")
    for (const layout of ["invalid", 'Top Only"\nmelonds_screen_gap = "10']) {
      expect(() => launch({ ...input(), runnerId: "@korri:melonds/melonds", layout })).toThrow("layout")
    }
  })

  it("keeps nested settings and netplay arguments when Core also chooses a layout", () => {
    const request: PluginLaunchInput = {
      ...input({ settings: {
        drivers: { video: "vulkan" },
        logging: { level: "verbose" },
        audio: { "volume-db": -3.5 },
      } }),
      runnerId: "@korri:melonds/melonds",
      netplay: { role: "host", passwordConfig: "/run/netplay/password.cfg" },
    }
    const original = launch(request)
    const layout = launch({ ...request, layout: "Top/Bottom" })
    expect(layout.args).toEqual(original.args)
    expect(layout.files[0]).toEqual(original.files[0])
    expect(layout.files[0].content).toContain('video_driver = "vulkan"')
    expect(layout.files[0].content).toContain("audio_volume = -3.5")
    expect(layout.env).toEqual({ KORRI_RETROARCH_CORE_OPTIONS_OVERLAY: layout.files[1].path })
  })

  it("keeps all native option routing settings unchanged", () => {
    for (const append of [
      'core_options_path = "/person/custom.opt"',
      'global_core_options = "true"',
      'global_core_options = "false"',
      'game_specific_options = "true"',
      'game_specific_options = "false"',
      'menu_config_directory = "/person/config"',
    ]) {
      const request = { ...input({ config: { append } }), runnerId: "@korri:melonds/melonds" }
      const original = launch(request)
      const layout = launch({ ...request, layout: "Top/Bottom" })
      expect(layout.files![0]).toEqual(original.files![0])
      expect(layout.args).toEqual(original.args)
      expect(layout.files![1].content).toBe('melonds_screen_layout = "Top/Bottom"\nmelonds_screen_gap = "0"\nmelonds_threaded_renderer = "enabled"\nmelonds_touch_mode = "Touch"\n')
    }
  })
})

describe.skipIf(!parser)("melonDS overlay through the pinned native parser", () => {
  it("contains the chosen layout, zero gap and absolute touch for each layout", () => {
    for (const layout of ["Top/Bottom", "Left/Right", "Top Only", "Bottom Only"]) {
      const plan = launch({ ...input(), runnerId: "@korri:melonds/melonds", layout })
      expect(parsed(plan.files[0].content, ["input_driver", "input_joypad_driver", "config_save_on_exit"]))
        .toEqual(["x", "udev", "false"])
      expect(parsed(plan.files![1].content, ["melonds_screen_layout", "melonds_screen_gap", "melonds_threaded_renderer", "melonds_touch_mode"]))
        .toEqual([layout, "0", "enabled", "Touch"])
    }
  })
})

import assert from "node:assert/strict"
import { test } from "bun:test"
import { settingsRules } from "./compose"
import * as plugin from "./plugin"
import type { PluginComposeInput } from "./plugin"

const { handlers, modifiers, name } = plugin
const compose = (input: PluginComposeInput) => handlers["launch.compose"](input)
const fixed = ["--backend", "wayland", "--fullscreen", "--expose-wayland"]
const output = ["--output-width", "1240", "--output-height", "1080"]
// Fixed flags, display-filled output size, then the default --force-composition.
const defaults = [...fixed, ...output, "--force-composition"]
function request(changes: Partial<PluginComposeInput> = {}): PluginComposeInput {
  return {
    modifierId: "@korri:gamescope/gamescope",
    runnerId: "@korri:solarus/solarus",
    plan: { command: "/game/engine", args: ["/games/My quest.solarus", "--debug"] },
    settings: {},
    config: {},
    files: { gamescope: "/package/bin/gamescope" },
    display: { width: 1240, height: 1080 },
    ...changes,
  }
}
function refused(input: PluginComposeInput, code: string, reason: RegExp) {
  assert.throws(() => compose(input), (error: unknown) => {
    assert.ok(error instanceof Error)
    assert.equal(Reflect.get(error, "code"), code)
    assert.equal(Reflect.get(error, "retryable"), false)
    assert.match(error.message, reason)
    assert.match(JSON.stringify(error), /"code":/)
    return true
  })
}

test("declares exactly one launch modifier and compose operation", () => {
  assert.equal(name, "gamescope")
  assert.deepEqual(modifiers, { gamescope: { id: "@korri:gamescope/gamescope" } })
  assert.deepEqual(Object.keys(handlers), ["launch.compose"])
  assert.ok(!("runners" in plugin))
  assert.ok(!("systems" in plugin))
})

test("composes fixed flags, ordered typed flags, append words, separator and the game", () => {
  const input = request({
    settings: {
      "framerate-limit": 40, sharpness: 10, filter: "fsr", scaler: "fit",
      "nested-refresh": 60, "nested-height": 720, "nested-width": 960,
      "output-height": 900, "output-width": 1200,
    },
    config: { append: '--hdr-enabled --filter "nearest"' },
  })
  assert.deepEqual(compose(input), {
    ...input.plan,
    command: input.files.gamescope,
    args: [
      ...fixed, "--output-width", "1200", "--output-height", "900",
      "--nested-width", "960", "--nested-height", "720", "--nested-refresh", "60",
      "--scaler", "fit", "--filter", "fsr", "--sharpness", "10",
      "--framerate-limit", "40", "--force-composition", "--hdr-enabled", "--filter", "nearest",
      "--", input.plan.command, ...input.plan.args,
    ],
  })
})

test("uses logical display dimensions only when both output settings are absent", () => {
  const input = request()
  assert.deepEqual(compose(input).args, [...defaults, "--", input.plan.command, ...input.plan.args])
  assert.deepEqual(compose(request({ display: undefined, settings: {
    "output-width": 800, "output-height": 600,
  } })).args.slice(4, 8), ["--output-width", "800", "--output-height", "600"])
})

test("honours POSIX quotes, escapes and empty words without expansion or shell execution", () => {
  const input = request({ config: { append: String.raw`one 'two three' "four five" six\ seven '' "" a"b"'c' $HOME ~ *.rom $(exit) \$USER "\$USER" '` + "`exit`" + String.raw`' "keep\q" "escaped\"quote" "back\\slash" #literal ; |` } })
  assert.deepEqual(compose(input).args.slice(defaults.length, -4), [
    "one", "two three", "four five", "six seven", "", "", "abc", "$HOME", "~",
    "*.rom", "$(exit)", "$USER", "$USER", "`exit`", "keep\\q", 'escaped"quote',
    "back\\slash", "#literal", ";", "|",
  ])
})

test("splits only shell whitespace and removes escaped newlines", () => {
  const input = request({ config: { append: "  one\ttwo\nthree\\\nfour \"five\\\nsix\" a\rb \u00a0 \\\n" } })
  assert.deepEqual(compose(input).args.slice(defaults.length, -4), ["one", "two", "threefour", "fivesix", "a\rb", "\u00a0"])
  assert.deepEqual(compose(request({ config: { append: " \\\n " } })).args, compose(request()).args)
})

test("preserves every runner plan field without mutation", () => {
  const input = request({ plan: {
    command: "/game/engine", args: ["", "--", "weird '$HOME' game"],
    env: { HOME: "/account", TOKEN: "secret" }, envUnset: ["DISPLAY"], cwd: "/account",
    directories: ["/account/saves"], files: [{ path: "/account/config", content: "native text\n" }],
  } })
  const before = structuredClone(input)
  Object.freeze(input.plan)
  const result = compose(input)
  for (const key of ["env", "envUnset", "cwd", "directories", "files"] as const) {
    assert.equal(result[key], input.plan[key])
  }
  assert.deepEqual(input, before)
  assert.deepEqual(result.args.slice(-4), [input.plan.command, ...input.plan.args])
})

test("accepts each supported enum and numeric range boundary", () => {
  for (const scaler of ["auto", "integer", "fit", "fill", "stretch"]) {
    assert.ok(compose(request({ settings: { scaler } })).args.includes(scaler))
  }
  for (const filter of ["linear", "nearest", "fsr", "nis", "pixel"]) {
    assert.ok(compose(request({ settings: { filter } })).args.includes(filter))
  }
  for (const sharpness of [0, 20]) compose(request({ settings: { sharpness } }))
  compose(request({ settings: { "framerate-limit": 0, "nested-refresh": 1 } }))
})

test("refuses unknown settings, bad types, invalid enums and out-of-range values", () => {
  for (const settings of [
    { unknown: true }, { constructor: "flag" }, { scaler: "fullscreen" }, { filter: "bilinear" },
    { scaler: true }, { filter: 2 }, { sharpness: "10" }, { sharpness: -1 },
    { sharpness: 21 }, { sharpness: 1.5 }, { "framerate-limit": -1 },
    { "framerate-limit": true }, { "nested-refresh": 0 }, { "nested-refresh": 1.5 },
    { "output-width": 0, "output-height": 1 }, { "nested-width": -1, "nested-height": 1 },
    { sharpness: Number.NaN }, { "framerate-limit": Number.POSITIVE_INFINITY },
    { "framerate-limit": Number.MAX_SAFE_INTEGER + 1 },
    { "framerate-limit": 2147483648 }, { "output-width": 2147483648, "output-height": 1 },
    { "nested-refresh": 2147484 },
  ]) {
    refused(request({ settings }), "gamescope-setting", /setting|integer|scaler|filter/i)
  }
})

test("refuses non-map settings and non-scalar setting values at the wire boundary", () => {
  for (const settings of [null, [], { filter: null }, { sharpness: {} }, { scaler: ["auto"] }]) {
    refused(JSON.parse(JSON.stringify({ ...request(), settings })), "gamescope-setting", /setting|scaler|filter/i)
  }
})

test("refuses unpaired dimensions even when a display fact could fill the gap", () => {
  for (const settings of [
    { "output-width": 1240 }, { "output-height": 1080 },
    { "nested-width": 640 }, { "nested-height": 480 },
  ]) refused(request({ settings }), "gamescope-setting-pair", /pair/)
})

test("refuses missing output size and invalid display facts", () => {
  refused(request({ display: undefined }), "gamescope-output-size", /output-width.*output-height.*display/i)
  for (const display of [{ width: 0, height: 1080 }, { width: 1240, height: -1 }, { width: 1.5, height: 2 }]) {
    refused(request({ display }), "gamescope-output-size", /display/i)
  }
})

test("refuses absent or invalid gamescope files and unknown modifiers", () => {
  for (const files of [{}, { gamescope: "" }, { gamescope: "relative/gamescope" }, { gamescope: "/bin/game\0scope" }]) {
    refused(request({ files }), "gamescope-file", /gamescope.*file/i)
  }
  refused(request({ modifierId: "@other:modifier/unknown" }), "gamescope-modifier", /modifier/i)
})

test("refuses malformed append and disallowed config keys", () => {
  for (const append of ["'unfinished", '"unfinished', "trailing\\", "bad\0word"]) {
    refused(request({ config: { append } }), "gamescope-append", /append/)
  }
  for (const config of [{ prepend: "--help" }, { replace: "--help" }, { append: false }]) {
    // Exercise the untyped wire boundary, not only TypeScript callers.
    const invalid = JSON.parse(JSON.stringify({ ...request(), config }))
    refused(invalid, "gamescope-config", /config/)
  }
})

const game = (input: PluginComposeInput) => ["--", input.plan.command, ...input.plan.args]
// Typed flags after the fixed four, before append words and the game.
const typed = (settings: PluginComposeInput["settings"]) => {
  const input = request({ settings })
  const args = compose(input).args
  assert.deepEqual(args.slice(0, 4), fixed)
  assert.deepEqual(args.slice(-game(input).length), game(input))
  return args.slice(4, -game(input).length)
}

test("types exactly the reviewed Gamescope options, keyed by their long option names", () => {
  assert.deepEqual(Object.keys(settingsRules), [
    "output-width", "output-height", "nested-width", "nested-height", "nested-refresh",
    "scaler", "filter", "sharpness", "framerate-limit", "max-scale", "force-composition",
    "adaptive-sync", "rt", "fade-out-duration", "force-windows-fullscreen", "hdr-enabled",
    "hdr-sdr-content-nits", "hdr-itm-enabled", "hdr-itm-sdr-nits", "hdr-itm-target-nits",
    "sdr-gamut-wideness", "disable-color-management", "force-grab-cursor", "mouse-sensitivity",
    "default-touch-mode", "cursor", "cursor-hotspot", "cursor-scale-height", "hide-cursor-delay",
    "prefer-vk-device", "reshade-effect", "reshade-technique-idx", "xwayland-count", "steam",
    "virtual-connector-strategy", "borderless", "disable-xres", "allow-deferred-backend",
  ])
})

test("refuses Gamescope options that stay reachable only through append", () => {
  for (const key of [
    "help", "version", "ready-fd", "stats-path", "backend", "fullscreen", "expose-wayland",
    "vr-overlay-key", "vr-session-manager", "debug-hud", "debug-layers", "debug-focus",
    "debug-events", "disable-layers", "synchronous-x11", "composite-debug", "hdr-debug-heatmap",
    "hdr-debug-force-output", "hdr-debug-force-support", "prefer-output", "force-orientation",
    "generate-drm-mode", "display-index", "nested-unfocused-refresh", "immediate-flips", "grab",
    "fsr-sharpness", "keep-alive", "mangoapp", "mura-map",
  ]) {
    refused(request({ settings: { [key]: true } }), "gamescope-setting", new RegExp(`Unknown Gamescope setting: ${key}$`))
  }
  const input = request({ config: { append: "--immediate-flips --mura-map /maps/panel" } })
  assert.deepEqual(compose(input).args.slice(defaults.length, -4), ["--immediate-flips", "--mura-map", "/maps/panel"])
})

test("emits every typed setting in table order, flags without values", () => {
  assert.deepEqual(typed({
    "allow-deferred-backend": true, "disable-xres": true, borderless: true,
    "virtual-connector-strategy": "PerWindow", steam: true, "xwayland-count": 2,
    "reshade-technique-idx": 1, "reshade-effect": "SweetFX/Vibrance.fx",
    "prefer-vk-device": "13B5:74021000", "hide-cursor-delay": 3000, "cursor-scale-height": 720,
    "cursor-hotspot": "4,2", cursor: "/account/cursor.png", "default-touch-mode": 4,
    "mouse-sensitivity": 1.5, "force-grab-cursor": true, "disable-color-management": true,
    "sdr-gamut-wideness": 0.5, "hdr-itm-target-nits": 1000, "hdr-itm-sdr-nits": 100,
    "hdr-itm-enabled": true, "hdr-sdr-content-nits": 203, "hdr-enabled": true,
    "force-windows-fullscreen": true, "fade-out-duration": 200, rt: true, "adaptive-sync": true,
    "force-composition": true, "max-scale": 2.5, "framerate-limit": 30, sharpness: 5,
    filter: "nearest", scaler: "integer", "nested-refresh": 60, "nested-height": 480,
    "nested-width": 640, "output-height": 1080, "output-width": 1240,
  }), [
    "--output-width", "1240", "--output-height", "1080", "--nested-width", "640",
    "--nested-height", "480", "--nested-refresh", "60", "--scaler", "integer",
    "--filter", "nearest", "--sharpness", "5", "--framerate-limit", "30", "--max-scale", "2.5",
    "--force-composition", "--adaptive-sync", "--rt", "--fade-out-duration", "200",
    "--force-windows-fullscreen", "--hdr-enabled", "--hdr-sdr-content-nits", "203",
    "--hdr-itm-enabled", "--hdr-itm-sdr-nits", "100", "--hdr-itm-target-nits", "1000",
    "--sdr-gamut-wideness", "0.5", "--disable-color-management", "--force-grab-cursor",
    "--mouse-sensitivity", "1.5", "--default-touch-mode", "4", "--cursor", "/account/cursor.png",
    "--cursor-hotspot", "4,2", "--cursor-scale-height", "720", "--hide-cursor-delay", "3000",
    "--prefer-vk-device", "13B5:74021000", "--reshade-effect", "SweetFX/Vibrance.fx",
    "--reshade-technique-idx", "1", "--xwayland-count", "2", "--steam",
    "--virtual-connector-strategy", "PerWindow", "--borderless", "--disable-xres",
    "--allow-deferred-backend",
  ])
})

test("force-composition is on unless the merged settings say false", () => {
  assert.deepEqual(typed({}), [...output, "--force-composition"])
  assert.deepEqual(typed({ "force-composition": true }), [...output, "--force-composition"])
  assert.deepEqual(typed({ "force-composition": false }), output)
  for (const value of ["false", 0, 1, "true"]) {
    refused(request({ settings: { "force-composition": value } }), "gamescope-setting", /force-composition must be true or false/)
  }
})

test("a true boolean adds its flag and false omits it", () => {
  for (const key of Object.keys(settingsRules).filter(key => settingsRules[key].kind === "boolean")) {
    const base = key === "force-composition" ? [] : ["--force-composition"]
    const on = typed({ [key]: true })
    assert.equal(on.filter(word => word === `--${key}`).length, 1, key)
    const off = typed({ [key]: false })
    assert.ok(!off.includes(`--${key}`), key)
    assert.deepEqual(off, [...output, ...base])
  }
  for (const value of ["true", "yes", 1, 0, ""]) {
    refused(request({ settings: { steam: value } }), "gamescope-setting", /steam must be true or false/)
  }
  refused(JSON.parse(JSON.stringify({ ...request(), settings: { rt: null } })), "gamescope-setting", /rt must be true or false/)
})

test("integer settings accept the parser's bounds and refuse anything else", () => {
  for (const mode of [0, 6]) assert.ok(typed({ "default-touch-mode": mode }).includes(String(mode)))
  assert.ok(typed({ "nested-refresh": 2147483 }).includes("2147483"))
  assert.ok(typed({ "output-width": 2147483647, "output-height": 1 }).includes("2147483647"))
  assert.ok(typed({ "xwayland-count": 1, "hide-cursor-delay": 0, "fade-out-duration": 0 }).includes("--xwayland-count"))
  for (const settings of [
    { "default-touch-mode": 7 }, { "default-touch-mode": -1 }, { "xwayland-count": 0 },
    { "cursor-scale-height": 0 }, { "hide-cursor-delay": -1 }, { "reshade-technique-idx": 2147483648 },
    { "fade-out-duration": 0.5 }, { "hide-cursor-delay": "3000" },
  ]) refused(request({ settings }), "gamescope-setting", /must be an integer/)
})

test("float settings accept finite numbers inside their limits only", () => {
  assert.ok(typed({ "max-scale": 1.5 }).includes("1.5"))
  assert.ok(typed({ "max-scale": 3.4028234663852886e38 }).includes("3.4028234663852886e+38"))
  assert.ok(typed({ "mouse-sensitivity": 1.1754943508222875e-38 }).includes("1.1754943508222875e-38"))
  for (const wideness of [0, 1]) assert.ok(typed({ "sdr-gamut-wideness": wideness }).includes(String(wideness)))
  assert.ok(typed({ "hdr-itm-sdr-nits": 1000, "hdr-itm-target-nits": 10000, "hdr-sdr-content-nits": 1 }).includes("10000"))
  for (const settings of [
    { "max-scale": 0 }, { "max-scale": 1e-40 }, { "max-scale": 1e39 }, { "max-scale": "1.5" },
    { "mouse-sensitivity": -1 }, { "mouse-sensitivity": Number.NaN },
    { "sdr-gamut-wideness": 1.01 }, { "sdr-gamut-wideness": -0.1 }, { "hdr-itm-sdr-nits": 1000.5 },
    { "hdr-itm-sdr-nits": 0.5 }, { "hdr-itm-target-nits": 10001 }, { "hdr-sdr-content-nits": 0 },
    { "hdr-sdr-content-nits": Number.POSITIVE_INFINITY }, { "max-scale": true },
  ]) refused(request({ settings }), "gamescope-setting", /must be a number/)
})

test("choice settings accept only Gamescope's spellings", () => {
  for (const strategy of ["SingleApplication", "SteamControlled", "PerAppId", "PerWindow"]) {
    assert.deepEqual(typed({ "virtual-connector-strategy": strategy }).slice(-2), ["--virtual-connector-strategy", strategy])
  }
  for (const value of ["perwindow", "Unknown", "", 1]) {
    refused(request({ settings: { "virtual-connector-strategy": value } }), "gamescope-setting", /must be one of: SingleApplication/)
  }
})

test("an explicit connector strategy follows --steam so Gamescope keeps it", () => {
  const args = typed({ "virtual-connector-strategy": "SingleApplication", steam: true })
  assert.ok(args.indexOf("--steam") < args.indexOf("--virtual-connector-strategy"))
})

test("path settings accept absolute paths without NUL bytes", () => {
  assert.deepEqual(typed({ cursor: "/account/my cursor.png" }).slice(-2), ["--cursor", "/account/my cursor.png"])
  for (const cursor of ["cursor.png", "./cursor.png", "~/cursor.png", "", "/account/cur\0sor.png", 1, true]) {
    refused(request({ settings: { cursor } }), "gamescope-setting", /cursor must be an absolute path/)
  }
})

test("string settings accept exactly Gamescope's syntax", () => {
  for (const rule of Object.values(settingsRules)) {
    if (rule.kind === "string") assert.ok(rule.valid(rule.example), rule.example)
  }
  const accepted = {
    "cursor-hotspot": ["0,0", "12,4", "2147483647,2147483647"],
    "prefer-vk-device": ["1002:7300", "13B5:74021000", "a:b", "FFFFFFFF:FFFFFFFF"],
    "reshade-effect": ["Sharpen.fx", "SweetFX/Vibrance.fx", "..fx", "a..b.fx"],
  }
  const rejected = {
    "cursor-hotspot": ["-1,2", "1", "1,2,3", " 1,2", "1, 2", "2147483648,0", "", "a,b", 12],
    "prefer-vk-device": ["0x1002:7300", "1002", "1002:", ":7300", "123456789:1", "1002:7300 ", "g:1", 1002],
    "reshade-effect": ["", "/usr/share/x.fx", "../x.fx", "a/../b.fx", "./a.fx", "a//b.fx", "a/", "a\0b.fx", true],
  }
  for (const [key, values] of Object.entries(accepted)) {
    for (const value of values) assert.deepEqual(typed({ [key]: value }).slice(-2), [`--${key}`, value])
  }
  for (const [key, values] of Object.entries(rejected)) {
    for (const value of values) refused(request({ settings: { [key]: value } }), "gamescope-setting", new RegExp(`${key} must be`))
  }
})

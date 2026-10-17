import assert from "node:assert/strict"
import { test } from "bun:test"
import * as plugin from "./plugin"
import type { PluginComposeInput } from "./plugin"

const { handlers, modifiers, name } = plugin
const compose = (input: PluginComposeInput) => handlers["launch.compose"](input)
const fixed = ["--backend", "wayland", "--fullscreen", "--expose-wayland"]
const output = ["--output-width", "1240", "--output-height", "1080"]
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
      "--framerate-limit", "40", "--hdr-enabled", "--filter", "nearest",
      "--", input.plan.command, ...input.plan.args,
    ],
  })
})

test("uses logical display dimensions only when both output settings are absent", () => {
  const input = request()
  assert.deepEqual(compose(input).args, [...fixed, ...output, "--", input.plan.command, ...input.plan.args])
  assert.deepEqual(compose(request({ display: undefined, settings: {
    "output-width": 800, "output-height": 600,
  } })).args.slice(4, 8), ["--output-width", "800", "--output-height", "600"])
})

test("honours POSIX quotes, escapes and empty words without expansion or shell execution", () => {
  const input = request({ config: { append: String.raw`one 'two three' "four five" six\ seven '' "" a"b"'c' $HOME ~ *.rom $(exit) \$USER "\$USER" '` + "`exit`" + String.raw`' "keep\q" "escaped\"quote" "back\\slash" #literal ; |` } })
  assert.deepEqual(compose(input).args.slice(8, -4), [
    "one", "two three", "four five", "six seven", "", "", "abc", "$HOME", "~",
    "*.rom", "$(exit)", "$USER", "$USER", "`exit`", "keep\\q", 'escaped"quote',
    "back\\slash", "#literal", ";", "|",
  ])
})

test("splits only shell whitespace and removes escaped newlines", () => {
  const input = request({ config: { append: "  one\ttwo\nthree\\\nfour \"five\\\nsix\" a\rb \u00a0 \\\n" } })
  assert.deepEqual(compose(input).args.slice(8, -4), ["one", "two", "threefour", "fivesix", "a\rb", "\u00a0"])
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

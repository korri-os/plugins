import assert from "node:assert/strict"
import { mkdirSync, writeFileSync } from "node:fs"
import type { PluginLaunchInput } from "../../contracts/generated/korrid"
import { handlers, systems, runners } from "./plugin"

const [directory, program] = process.argv.slice(2)
assert.deepEqual(systems.pyxel.content.extensions, ["pyxapp"])
const input: PluginLaunchInput = {
  runnerId: runners.pyxel.id,
  program,
  contentPath: "/media/Selected '; $(touch injected).pyxapp",
  accountRoot: "/accounts/Player One",
  saveRoot: "/saves/Player One/game",
  cacheRoot: "/cache",
  files: {},
  artifacts: {},
}
const launch = handlers["launch.prepare"](input)
assert.deepEqual(launch.args, [input.contentPath])
assert.equal(launch.cwd, input.saveRoot)
assert.deepEqual(launch.saveLocations, [{ key: "saves", kind: "save", path: `${input.saveRoot}/.pyxel` }])
assert.equal(launch.env?.HOME, input.saveRoot)
assert.equal(launch.env?.PYTHONDONTWRITEBYTECODE, "1")
for (const change of [
  { runnerId: "@other:runner/runner" },
  { corePath: "/core.so" },
  { contentPath: undefined },
  { contentPath: "relative.pyxapp" },
  { contentPath: "/media/bad\0.py" },
  { contentPath: "/media/game.zip" },
  { contentPath: "/media/source.py" },
  { accountRoot: "relative" },
  { saveRoot: "relative" },
  { saveRoot: "/bad\0" },
  { overrides: { settings: { fullscreen: true } } },
  { overrides: { config: { append: "anything" } } },
]) assert.throws(() => handlers["launch.prepare"]({ ...input, ...change }))
assert.deepEqual(systems.pyxel.content.evidence, { bytes: [{ offset: 0, hex: "504b0304" }] })
mkdirSync(directory, { recursive: true })
writeFileSync(`${directory}/template.json`, JSON.stringify(input))
console.log("Pyxel literal selected-file plan, account saves and refusals passed")

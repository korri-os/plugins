import assert from "node:assert/strict"
import type { PluginLaunchInput } from "../../contracts/generated/korrid"
import { handlers, runners, systems } from "./plugin"

assert.deepEqual(systems.wiiu, {
  title: "Wii U",
  content: { extensions: ["wua", "wud", "wux", "rpx", "wuhb"] },
})
const input: PluginLaunchInput = {
  runnerId: "@korri:cemu/cemu", program: "/package/bin/cemu",
  contentPath: "/games/A game '; $(exit 1).wua",
  accountRoot: "/accounts/Player One", saveRoot: "/saves/game", cacheRoot: "/cache",
  files: {}, artifacts: {},
}
assert.equal(runners.cemu.program, "cemu")
const plan = handlers["launch.prepare"](input)
assert.deepEqual(plan, {
  command: input.program,
  args: ["-f", "-g", input.contentPath, "--mlc", "/saves/game/mlc01"],
  env: {
    HOME: input.accountRoot,
    XDG_CONFIG_HOME: "/accounts/Player One/.config",
    XDG_DATA_HOME: "/accounts/Player One/.local/share",
    XDG_CACHE_HOME: "/accounts/Player One/.cache",
  },
  cwd: input.accountRoot,
  directories: [input.accountRoot, "/saves/game/mlc01/usr/save"],
  saveLocations: [{ key: "saves", kind: "save", path: "/saves/game/mlc01/usr/save" }],
})
assert.deepEqual(handlers["launch.prepare"]({ ...input, overrides: { settings: {} } }), plan)
for (const namespace of ["@test-publisher", "@another-publisher"]) {
  assert.deepEqual(handlers["launch.prepare"]({
    ...input, runnerId: `${namespace}:cemu/cemu`,
  }), plan)
  assert.throws(() => handlers["launch.prepare"]({
    ...input, runnerId: `${namespace}:cemu/other`,
  }), /Unknown Cemu runner/)
}
for (const patch of [
  { runnerId: "@korri:other/other" }, { corePath: "/core.so" },
  { contentPath: undefined, ref: "123" }, { ref: "123" },
  { overrides: { settings: { fullscreen: false } } },
  { overrides: { config: { append: "anything" } } },
  ...["accountRoot", "saveRoot", "contentPath"].flatMap(key =>
    ["relative", "/bad\0path"].map(value => ({ [key]: value }))),
]) assert.throws(() => handlers["launch.prepare"]({ ...input, ...patch }))
console.log("Cemu launch contract passed")

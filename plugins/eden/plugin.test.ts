import assert from "node:assert/strict"
import type { PluginLaunchInput } from "../../contracts/generated/korrid"
import { handlers, runners, systems } from "./plugin"

assert.deepEqual(systems.switch, {
  title: "Nintendo Switch",
  content: { extensions: ["nsp", "xci"] },
})
const input: PluginLaunchInput = {
  runnerId: "@korri:eden/eden", program: "/package/bin/eden",
  contentPath: "/games/A game '; $(exit 1).nsp",
  accountRoot: "/accounts/Player One", saveRoot: "/saves/game", cacheRoot: "/cache",
  files: {}, artifacts: {},
}
assert.equal(runners.eden.program, "eden")
const plan = handlers["launch.prepare"](input)
assert.deepEqual(plan, {
  command: input.program,
  args: ["-f", "-g", input.contentPath],
  env: {
    HOME: input.accountRoot,
    EDEN_SAVE_ROOT: input.saveRoot,
    XDG_CONFIG_HOME: "/accounts/Player One/.config",
    XDG_DATA_HOME: "/accounts/Player One/.local/share",
    XDG_CACHE_HOME: "/accounts/Player One/.cache",
  },
  cwd: input.accountRoot,
  directories: [input.accountRoot, "/saves/game/nand/user/save"],
  saveLocations: [{ key: "saves", kind: "save", path: "/saves/game/nand/user/save" }],
})
assert.deepEqual(handlers["launch.prepare"]({ ...input, overrides: { settings: {} } }), plan)
for (const patch of [
  { runnerId: "@korri:other/other" }, { corePath: "/core.so" },
  { contentPath: undefined }, { ref: "123" },
  { overrides: { settings: { fullscreen: false } } },
  { overrides: { config: { append: "anything" } } },
  ...["accountRoot", "saveRoot", "contentPath", "program"].flatMap(key =>
    ["relative", "/bad\0path"].map(value => ({ [key]: value }))),
]) assert.throws(() => handlers["launch.prepare"]({ ...input, ...patch }))
for (const key of ["accountRoot", "saveRoot"]) {
  for (const value of ["/bad\npath", '/bad"path']) {
    assert.throws(() => handlers["launch.prepare"]({ ...input, [key]: value }))
  }
}
assert.deepEqual(handlers["launch.prepare"]({ ...input, contentPath: '/games/"quoted".xci' }).args,
  ["-f", "-g", '/games/"quoted".xci'])
const second = handlers["launch.prepare"]({ ...input, accountRoot: "/accounts/two", saveRoot: "/saves/two" })
assert.equal(second.env?.EDEN_SAVE_ROOT, "/saves/two")
assert.equal(second.env?.XDG_DATA_HOME, "/accounts/two/.local/share")
assert.equal(second.saveLocations[0].path, "/saves/two/nand/user/save")
console.log("Eden launch contract passed")

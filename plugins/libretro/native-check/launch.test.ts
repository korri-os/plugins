import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
const packages: Record<string, string> = JSON.parse(readFileSync(process.argv[2], "utf8"))
const expected: Record<string, string> = {
  tic80: "tic80", wasm4: "wasm4", lowresnx: "lowresnx", pzretro: "puzzlescript",
}
for (const [core, path] of Object.entries(packages)) {
  const manifest = JSON.parse(readFileSync(`${path}/manifest.json`, "utf8"))
  const plugin = await import(resolve(path, "plugin.ts"))
  assert.equal(plugin.name, core)
  assert.deepEqual(Object.keys(plugin.systems), [expected[core]])
  const input = {
    runnerId: `@korri:${core}/${core}`,
    program: manifest.files.retroarch,
    corePath: manifest.files[core],
    contentPath: "/media/Selected '; $(touch injected).game",
    accountRoot: "/account/Player One",
    saveRoot: "/saves/Player One/game",
    cacheRoot: "/cache",
    files: manifest.files,
    artifacts: {},
  }
  const output = plugin.handlers["launch.prepare"](input)
  assert.equal(output.command, manifest.files.retroarch)
  assert.deepEqual(output.args, ["--config", `${input.accountRoot}/retroarch.cfg`,
    "-L", input.corePath, input.contentPath])
  const config = output.files.find((f: {path: string}) => f.path.endsWith("retroarch.cfg")).content
  assert.ok(config.includes('input_quit_gamepad_combo = "4"'))
  assert.ok(config.includes('input_menu_toggle_gamepad_combo = "2"'))
  assert.ok(config.includes(`savefile_directory = "${input.saveRoot}/saves"`))
  assert.ok(output.directories.every((d: string) => !d.startsWith("/media")))
  for (const change of [{contentPath: undefined}, {corePath: undefined},
    {overrides: { config: { replace: "invalid" } }}]) {
    assert.throws(() => plugin.handlers["launch.prepare"]({ ...input, ...change }))
  }
}
console.log("Four independent generated runner plans, saves, Start policy and refusals passed")

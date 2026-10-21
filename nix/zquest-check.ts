import assert from "node:assert/strict"
import { spawnSync } from "node:child_process"
import { accessSync, constants, readFileSync } from "node:fs"
import { join } from "node:path"
import process from "node:process"
import type { PluginLaunchInput } from "../contracts/generated/korrid"
import * as plugin from "../plugins/zquest-classic/plugin"
import { preparedLaunch } from "./prepared-launch"

const { handlers, name, runners, systems } = plugin
assert.ok(!("discovery" in plugin))
assert.ok(!("sessionControls" in plugin))

const [packagePath, hostCli, korridCli, recordArguments] = process.argv.slice(2)
assert(packagePath && hostCli && korridCli && recordArguments)
const manifest = JSON.parse(
  readFileSync(join(packagePath, "manifest.json"), "utf8"),
)
assert.deepEqual(manifest.publisher, { namespace: "@korri" })
assert.deepEqual(manifest.sources, ["plugin.ts"])
assert.equal(manifest.entry, "plugin.ts")
assert.deepEqual(Object.keys(manifest.packages), ["zquest-classic"])
assert.deepEqual(manifest.files, {
  zplayer: join(manifest.packages["zquest-classic"], "bin/zplayer"),
})
assert.deepEqual(manifest.services, {})
assert.deepEqual(manifest.ports, {})
accessSync(manifest.files.zplayer, constants.X_OK)
assert.equal(name, "zquest-classic")
assert.deepEqual(systems, {
  "zelda-classic": {
    id: "zelda-classic",
    title: "Zelda Classic Quest",
    content: { extensions: ["qst"] },
  },
})
assert.deepEqual(runners, {
  zplayer: {
    id: "@korri:zquest-classic/zplayer",
    program: "zplayer",
    systems: ["zelda-classic"],
  },
})
assert.deepEqual(Object.keys(handlers), ["launch.prepare"])
const admission = spawnSync(
  hostCli,
  ["seed", packagePath, "https://cache.example.invalid"],
  { encoding: "utf8" },
)
assert.equal(admission.status, 0, admission.stderr)
const receipt = JSON.parse(admission.stdout)
assert.equal(receipt.id, "@korri:zquest-classic")
assert.equal(receipt.package, packagePath)
assert.deepEqual(receipt.desired, { state: "Enabled" })
assert.equal(receipt.previous, null)

for (const contentPath of [
  "/library/Quest.qst",
  "/library/Quest %s '; $(exit 19) #.QST",
]) {
  const input: PluginLaunchInput = {
    runnerId: runners.zplayer.id,
    program: recordArguments,
    contentPath,
    accountRoot: "/accounts/Player One '; $(exit 21)",
    saveRoot: "/accounts/Player One '; $(exit 21)/saves/quest",
    cacheRoot: "/cache",
    files: manifest.files,
    artifacts: {},
  }
  const args = ["--", contentPath, `${input.accountRoot}/zquest-classic`]
  const plan = handlers["launch.prepare"](input)
  assert.deepEqual(plan, {
    command: recordArguments,
    args,
    env: {},
  })
  const result = spawnSync(
    korridCli,
    [
      "plugin-launch", join(packagePath, "plugin.ts"), JSON.stringify(input),
      JSON.stringify({ modifiers: [] }), preparedLaunch(plan),
    ],
    { encoding: "utf8" },
  )
  assert.equal(result.status, 0, result.stderr)
  assert.equal(result.stdout, `${args.join("\0")}\0`)
  for (const unsupported of [
    { contentPath: undefined, ref: "123" },
    { corePath: "/core.so" },
    { overrides: { config: { replace: "unsupported" } } },
    { overrides: { settings: { unsupported: true } } },
  ]) {
    // The host refuses a launch whose preparation throws, before any unit
    // starts. `korrid plugin-launch` no longer evaluates the plugin.
    assert.throws(() =>
      handlers["launch.prepare"]({ ...input, ...unsupported }),
    )
  }
}
console.log(
  "ZQuest manifest, contract, admission and sandboxed launch checks passed",
)

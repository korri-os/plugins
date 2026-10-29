import assert from "node:assert/strict"
import { spawnSync } from "node:child_process"
import { accessSync, constants, mkdtempSync, readFileSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import process from "node:process"
import type { PluginLaunchInput } from "../contracts/generated/korrid"
import * as plugin from "../plugins/solarus/plugin"

const { handlers, name, runners, systems } = plugin
assert.ok(!("discovery" in plugin))
assert.ok(!("sessionControls" in plugin))

const [packagePath, hostCli, korridCli, recordArguments] = process.argv.slice(2)
assert(packagePath && hostCli && korridCli && recordArguments)
const manifest = JSON.parse(readFileSync(join(packagePath, "manifest.json"), "utf8"))
assert.deepEqual(manifest.publisher, { namespace: "@korri" })
assert.deepEqual(manifest.sources, ["plugin.ts"])
assert.equal(manifest.entry, "plugin.ts")
assert.deepEqual(Object.keys(manifest.packages), ["solarus"])
assert.deepEqual(manifest.files, {
  solarus: join(manifest.packages.solarus, "bin/solarus-run"),
})
assert.deepEqual(manifest.services, {})
assert.deepEqual(manifest.ports, {})
accessSync(manifest.files.solarus, constants.X_OK)
assert.equal(name, "solarus")
assert.deepEqual(systems, {
  solarus: { title: "Solarus", content: { extensions: ["solarus"] } },
})
assert.deepEqual(runners, {
  solarus: { program: "solarus", systems: ["solarus"] },
})
assert.deepEqual(Object.keys(handlers), ["launch.prepare"])

const admission = spawnSync(hostCli, [
  "seed", packagePath, "https://cache.example.invalid",
], { encoding: "utf8", timeout: 30_000 })
assert.equal(admission.status, 0, admission.stderr)
const receipt = JSON.parse(admission.stdout)
assert.equal(receipt.id, "@korri:solarus")
assert.equal(receipt.package, packagePath)
assert.deepEqual(receipt.desired, { state: "Enabled" })
assert.equal(receipt.previous, null)

const work = mkdtempSync(join(tmpdir(), "solarus-contract-"))
try {
  const accountRoot = join(work, "Player One '; $(exit 21)")
  for (const contentPath of [
    "/library/My quest.solarus",
    "/library/quest %s '; $(exit 19) #.solarus",
    "/library/quest/data.solarus.zip",
    "/library/unpacked quest/data",
  ]) {
    const input: PluginLaunchInput = {
      runnerId: "@korri:solarus/solarus",
      program: recordArguments,
      contentPath,
      accountRoot,
      saveRoot: join(accountRoot, "saves", "korri_plugin_test"),
      cacheRoot: join(work, "cache"),
      files: manifest.files,
      artifacts: {},
    }
    const expected = {
      command: recordArguments,
      args: [contentPath],
      env: { HOME: accountRoot },
      cwd: accountRoot,
      directories: [accountRoot],
    }
    assert.deepEqual(handlers["launch.prepare"](input), expected)
    assert.deepEqual(handlers["launch.prepare"]({
      ...input, overrides: { settings: {} },
    }), expected)
    const launch = spawnSync(korridCli, [
      "plugin-run", join(packagePath, "plugin.ts"), JSON.stringify(input),
      JSON.stringify({ modifiers: [] }), "fixture",
    ], { encoding: "utf8", timeout: 30_000 })
    assert.equal(launch.status, 0, launch.stderr)
    assert.equal(launch.stdout, `${contentPath}\0${accountRoot}\0${accountRoot}\0`)

    for (const unsupported of [
      { runnerId: "@other:runner/runner" },
      { corePath: "/core.so" },
      { overrides: { config: { replace: "ignored settings" } } },
      { overrides: { settings: { fullscreen: true } } },
      { contentPath: undefined, ref: "123" },
      { contentPath: "-help" },
      { contentPath: "relative.solarus" },
      { contentPath: "/library/quest\0.solarus" },
      { accountRoot: "relative" },
      { accountRoot: "/account\0" },
    ]) {
      const invalid = { ...input, ...unsupported }
      assert.throws(() => handlers["launch.prepare"](invalid))
      const rejected = spawnSync(korridCli, [
        "plugin-run", join(packagePath, "plugin.ts"), JSON.stringify(invalid),
        JSON.stringify({ modifiers: [] }), "fixture",
      ], { encoding: "utf8", timeout: 30_000 })
      assert.notEqual(rejected.status, 0)
      assert.equal(rejected.stdout, "")
    }
  }
} finally {
  rmSync(work, { recursive: true, force: true })
}
console.log("Solarus package, launch contract, host seed/declaration and sandbox checks passed")

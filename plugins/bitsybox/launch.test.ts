import assert from "node:assert/strict"
import { spawnSync } from "node:child_process"
import { mkdtempSync, readFileSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import type { PluginLaunchInput } from "../../contracts/generated/korrid"
import { handlers, runners, systems } from "./plugin"

const [packagePath, host, korrid, record] = process.argv.slice(2)
const manifest = JSON.parse(
  readFileSync(join(packagePath, "manifest.json"), "utf8"),
)
assert.deepEqual(manifest.publisher, { namespace: "@korri" })
assert.deepEqual(manifest.sources, ["plugin.ts"])
assert.deepEqual(Object.keys(manifest.packages), ["bitsybox"])
assert.deepEqual(manifest.files, {
  bitsybox: `${manifest.packages.bitsybox}/bin/bitsybox`,
})
assert.deepEqual(manifest.services, {})
assert.deepEqual(manifest.ports, {})
assert.deepEqual(systems, {
  bitsy: { title: "Bitsy", content: { extensions: ["bitsy"] } },
})
assert.deepEqual(runners, {
  bitsybox: {
    program: "bitsybox",
    systems: ["bitsy"],
  },
})
const admission = spawnSync(
  host,
  ["seed", packagePath, "https://cache.example.invalid"],
  { encoding: "utf8", timeout: 30_000 },
)
assert.equal(admission.status, 0, admission.stderr)
const receipt = JSON.parse(admission.stdout)
assert.equal(receipt.id, "@korri:bitsybox")
assert.equal(receipt.package, packagePath)
assert.deepEqual(receipt.desired, { state: "Enabled" })

const work = mkdtempSync(join(tmpdir(), "bitsy-launch-"))
try {
  const accountRoot = join(work, "Player One '; $(exit 21)")
  const input: PluginLaunchInput = {
    runnerId: "@korri:bitsybox/bitsybox",
    program: record,
    contentPath: `/media/${"long path/".repeat(40)}Selected '; $(exit 19).bitsy`,
    accountRoot,
    saveRoot: join(accountRoot, "saves"),
    cacheRoot: join(work, "cache"),
    files: manifest.files,
    artifacts: {},
  }
  const expected = {
    command: record,
    args: [input.contentPath],
    env: {},
    cwd: accountRoot,
    directories: [accountRoot],
  }
  assert.deepEqual(handlers["launch.prepare"](input), expected)
  assert.deepEqual(
    handlers["launch.prepare"]({ ...input, overrides: { settings: {} } }),
    expected,
  )
  function execute(request: PluginLaunchInput) {
    return spawnSync(
      korrid,
      [
        "plugin-run",
        join(packagePath, "plugin.ts"),
        JSON.stringify(request),
        JSON.stringify({ modifiers: [] }),
        "fixture",
      ],
      { encoding: "utf8", timeout: 30_000 },
    )
  }
  for (const namespace of ["@test-publisher", "@another-publisher"]) {
    const request = { ...input, runnerId: `${namespace}:bitsybox/bitsybox` }
    assert.deepEqual(handlers["launch.prepare"](request), expected)
    const result = execute(request)
    assert.equal(result.status, 0, result.stderr)
    assert.equal(result.stdout, `${input.contentPath}\0${accountRoot}\0`)
    const invalid = { ...input, runnerId: `${namespace}:bitsybox/other` }
    assert.throws(() => handlers["launch.prepare"](invalid), /Unknown Bitsybox runner/)
    const rejected = execute(invalid)
    assert.notEqual(rejected.status, 0, rejected.stderr)
    assert.equal(rejected.stdout, "")
  }
  const launch = execute(input)
  assert.equal(launch.status, 0, launch.stderr)
  assert.equal(launch.stdout, `${input.contentPath}\0${accountRoot}\0`)
  for (const unsupported of [
    { runnerId: "@other:runner/runner" },
    { corePath: "/core.so" },
    { overrides: { config: { replace: "ignored" } } },
    { overrides: { settings: { fullscreen: true } } },
    { contentPath: undefined, ref: "123" },
    { contentPath: "-help" },
    { contentPath: "relative.bitsy" },
    { contentPath: "/media/game\0.bitsy" },
    { accountRoot: "relative" },
    { accountRoot: "/account\0" },
  ]) {
    const invalid = { ...input, ...unsupported }
    assert.throws(() => handlers["launch.prepare"](invalid))
    const rejected = execute(invalid)
    assert.notEqual(rejected.status, 0, rejected.stderr)
    assert.equal(rejected.stdout, "")
  }
} finally {
  rmSync(work, { recursive: true, force: true })
}
console.log(
  "Bitsybox host admission, launch.prepare and plugin-run positive/negative cases passed",
)

// Tests the installed source, not a separate declaration fixture.
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { spawnSync } from "node:child_process"

const [snesPath, otherPath, probe, coreInfo] = process.argv.slice(2)
const snes = await import(resolve(snesPath, "plugin.ts"))
const other = await import(resolve(otherPath, "plugin.ts"))
const manifest = JSON.parse(readFileSync(resolve(snesPath, "manifest.json"), "utf8"))
const result = spawnSync(probe, [manifest.files.snes9x2010], { encoding: "utf8" })
assert.equal(result.status, 0, result.stderr)
const [library, version] = result.stdout.trimEnd().split("\n")
assert.equal(library, "Snes9x 2010")
assert.ok(version.length > 0)
assert.deepEqual(snes.runners.snes9x2010.netplay, { library, version })
assert.match(readFileSync(coreInfo, "utf8"), /^savestate_features = "deterministic"$/m)
assert.equal(Object.hasOwn(other.runners.fake08, "netplay"), false)
assert.equal(other.runners.fake08.core, "fake08")
console.log(`snes9x2010: ${JSON.stringify({ library, version })}; fake08: no netplay`)

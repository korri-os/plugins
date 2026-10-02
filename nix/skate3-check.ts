import assert from "node:assert/strict"
import { spawnSync } from "node:child_process"
import { accessSync, constants, readFileSync } from "node:fs"
import { join } from "node:path"
import process from "node:process"
import type { PluginLaunchInput } from "../contracts/generated/korrid"
import {
  discovery,
  handlers,
  name,
  runners,
  systems,
} from "../plugins/skate-3/plugin"

const [packagePath, hostCli, korridCli, envProgram] = process.argv.slice(2)
assert(packagePath && hostCli && korridCli && envProgram)

const manifest = JSON.parse(
  readFileSync(join(packagePath, "manifest.json"), "utf8"),
)
assert.deepEqual(manifest.publisher, { namespace: "@korri" })
assert.deepEqual(manifest.sources, ["plugin.ts"])
assert.equal(manifest.entry, "plugin.ts")
assert.deepEqual(Object.keys(manifest.packages), ["skate3"])
assert.deepEqual(Object.keys(manifest.files), ["skate3"])
assert.deepEqual(manifest.services, {})
assert.deepEqual(manifest.ports, {})
assert.equal(
  manifest.files.skate3,
  join(manifest.packages.skate3, "bin/skate3"),
)
accessSync(manifest.files.skate3, constants.X_OK)

assert.equal(name, "skate-3")
assert.deepEqual(Object.keys(runners), ["skate3"])
assert.equal(runners.skate3.id, "@korri:skate-3/skate3")
assert.equal(runners.skate3.program, "skate3")
assert(!("systems" in runners.skate3))
assert.deepEqual(runners.skate3.releases, [
  "sha256:bd8d430188aa61b0ebf2e33e5672822dd7e59c9080fc09e802195e1ee75ebff0",
])
assert.deepEqual(systems, { "xbox-360": { id: "xbox-360", title: "Xbox 360" } })
assert.deepEqual(discovery.fileReleases["xbox-360-discs"], {
  id: "@korri:skate-3/xbox-360-discs",
  title: "Xbox 360 disc images",
  extensions: ["iso"],
  system: "xbox-360",
  runners: [runners.skate3.id],
})
assert.deepEqual(Object.keys(handlers), ["launch.prepare"])

// Seed is the host's effect-free admission check, not installation or trust.
const admission = spawnSync(hostCli, [
  "seed",
  packagePath,
  "https://cache.example.invalid",
], {
  encoding: "utf8",
})
assert.equal(admission.status, 0, admission.stderr)
const receipt = JSON.parse(admission.stdout)
assert.equal(receipt.id, "@korri:skate-3")
assert.equal(receipt.package, packagePath)
assert.deepEqual(receipt.desired, { state: "Enabled" })
assert.equal(receipt.previous, null)

for (
  const contentPath of [
    "/library/Skate 3 (USA, Europe) (En,Fr,De,Es,It,Nl).iso",
    "/library/Skate 3 '; $(exit 19) #.iso",
  ]
) {
  const input: PluginLaunchInput = {
    runnerId: runners.skate3.id,
    program: envProgram,
    contentPath,
    accountRoot: "/account",
    files: manifest.files,
  }
  assert.deepEqual(handlers["launch.prepare"](input), {
    command: envProgram,
    args: [],
    env: { SKATE3_INSTALL_ISO: contentPath, SKATE3_INSTALL_TU: "download" },
  })
  // The production callback evaluator materializes the declaration, then
  // executes the real env program supplied through the existing input seam.
  // No game installation or network call occurs in this test.
  const launch = spawnSync(korridCli, [
    "plugin-launch",
    join(packagePath, "plugin.ts"),
    JSON.stringify(input),
  ], { encoding: "utf8" })
  assert.equal(launch.status, 0, launch.stderr)
  const environment = launch.stdout.split("\n")
  assert(environment.includes(`SKATE3_INSTALL_ISO=${contentPath}`))
  assert(environment.includes("SKATE3_INSTALL_TU=download"))
}
console.log(
  "Skate 3 package, contract, admission and sandboxed launch checks passed",
)

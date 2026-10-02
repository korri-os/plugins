// Read the actual generated module and manifest, not a parallel fixture.
import { readFileSync, statSync } from "node:fs"
import { resolve } from "node:path"
import assert from "node:assert/strict"

const [packagePath] = process.argv.slice(2)
const manifest = JSON.parse(readFileSync(`${packagePath}/manifest.json`, "utf8"))
const plugin = await import(resolve(packagePath, manifest.entry))
assert.equal(manifest.publisher.namespace, "@korri")
assert.equal(`${manifest.publisher.namespace}:${plugin.name}`, "@korri:fake08")
assert.deepEqual(plugin.systems, { pico8: { id: "pico8", title: "PICO-8" } })
assert.deepEqual(plugin.discovery.fileReleases["pico8-files"].extensions, ["p8", "p8.png"])
assert.equal(plugin.discovery.fileReleases["pico8-files"].system, "pico8")
assert.deepEqual(plugin.discovery.fileReleases["pico8-files"].runners, ["@korri:fake08/fake08"])
assert.equal(plugin.runners.fake08.family, "@korri:retroarch")
assert.equal(plugin.runners.fake08.program, "retroarch")
assert.equal(plugin.runners.fake08.core, "fake08")
for (const key of ["retroarch", "retroarch-settings", "autoconfig", "fake08"]) {
  assert.ok(manifest.files[key].startsWith("/nix/store/"), key)
  assert.ok(key === "autoconfig" ? statSync(manifest.files[key]).isDirectory() : statSync(manifest.files[key]).size > 0)
}
const launch = plugin.handlers["launch.prepare"]({
  accountRoot: "/tmp/account",
  runnerId: "@korri:fake08/fake08",
  program: manifest.files.retroarch,
  corePath: manifest.files.fake08,
  contentPath: "/tmp/carts/intoruins.p8.png",
  files: manifest.files,
})
assert.equal(launch.command, manifest.files.retroarch)
assert.deepEqual(launch.args, ["--config", "/tmp/account/retroarch.cfg", "-L", manifest.files.fake08, "/tmp/carts/intoruins.p8.png"])
// Exercise the shipped helper with an original .p8.png path. RetroArch must
// pass it to FAKE-08 instead of its built-in image viewer (legacy launch-spec).
assert.ok(launch.files[0].content.includes('builtin_imageviewer_enable = "false"'))
for (const protection of ['kiosk_mode_enable = "true"', 'menu_driver = "null"', 'config_save_on_exit = "false"', 'input_player1_reserved_device = "Korri Seat P1"']) {
  assert.ok(launch.files[0].content.includes(protection), protection)
}
assert.ok(launch.files[0].content.includes(manifest.files.autoconfig))
assert.ok(plugin.handlers["settings.describe"]().schema.properties.video_driver)
assert.ok(!plugin.handlers["settings.describe"]().schema.properties.kiosk_mode_enable)
assert.equal(plugin.sessionControls.quit.owner.id, "@korri:fake08/fake08")
console.log("FAKE-08 generated output, discovery, runtime files and protected helper passed")

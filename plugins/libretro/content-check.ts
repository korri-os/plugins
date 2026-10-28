// Import every generated declaration with the real shared helper and settings.
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"

const [directory, expectedPath] = process.argv.slice(2)
const expected: Record<string, string[]> = JSON.parse(readFileSync(expectedPath, "utf8"))
const groups = {
  gameboy: { id: "gameboy", title: "Game Boy", systems: ["gb", "gbc"] },
  "sega-8bit": { id: "sega-8bit", title: "Sega 8-bit", systems: ["sms", "gg", "sg1000"] },
  "nintendo-8bit": { id: "nintendo-8bit", title: "Nintendo 8-bit", systems: ["nes", "fds"] },
  "mega-drive": { id: "mega-drive", title: "Mega Drive", systems: ["md", "sega32x"] },
}
const content = new Map<string, { extensions: string[], header?: object[], evidence?: object }>()
const seenGroups = new Set<string>()
for (const [core, systemIds] of Object.entries(expected)) {
  const plugin = await import(resolve(directory, `${core}.ts`))
  assert.ok(!("discovery" in plugin), `${core}: removed discovery export`)
  assert.ok(!("sessionControls" in plugin), `${core}: removed sessionControls export`)
  assert.equal(plugin.controls.quit.owner.id, `@korri:${core}/${core}`)
  assert.deepEqual(Object.keys(plugin.systems).sort(), [...systemIds].sort(), core)
  assert.deepEqual(plugin.runners[core].systems, [...systemIds].sort(), core)
  if (core === "melonds") {
    assert.deepEqual(plugin.runners[core].layouts, {
      "Top/Bottom": { panes: {
        upper: { x: 0, y: 0, width: 1, height: 0.5 },
        lower: { x: 0, y: 0.5, width: 1, height: 0.5 },
      } },
      "Left/Right": { panes: {
        upper: { x: 0, y: 0, width: 0.5, height: 1 },
        lower: { x: 0.5, y: 0, width: 0.5, height: 1 },
      } },
      "Top Only": { panes: { upper: { x: 0, y: 0, width: 1, height: 1 } } },
      "Bottom Only": { panes: { lower: { x: 0, y: 0, width: 1, height: 1 } } },
    })
  } else {
    assert.ok(!("layouts" in plugin.runners[core]), `${core}: no declared layouts`)
  }
  // Exercise the real generated entrypoint, including its declaration binding.
  const request = {
    runnerId: plugin.runners[core].id, program: "/program", corePath: "/core",
    contentPath: "/rom", accountRoot: "/account", saveRoot: "/saves", cacheRoot: "/cache",
    files: { autoconfig: "/autoconfig" }, artifacts: {},
  }
  const launch = plugin.handlers["launch.prepare"]
  const original = launch(request)
  if (core === "melonds") {
    assert.ok(original.files[0].content.includes('input_driver = "x"\n'))
    assert.ok(original.files[0].content.includes('input_joypad_driver = "udev"\n'))
    assert.equal(original.files[1].content, 'melonds_threaded_renderer = "enabled"\nmelonds_touch_mode = "Touch"\n')
    for (const layout of ["Top/Bottom", "Left/Right", "Top Only", "Bottom Only"]) {
      const plan = launch({ ...request, layout })
      assert.deepEqual(plan.files[0], original.files[0])
      assert.equal(plan.files[1].content, `melonds_screen_layout = "${layout}"\nmelonds_screen_gap = "0"\nmelonds_threaded_renderer = "enabled"\nmelonds_touch_mode = "Touch"\n`)
      assert.deepEqual(plan.env, { KORRI_RETROARCH_CORE_OPTIONS_OVERLAY: plan.files[1].path })
    }
    assert.throws(() => launch({ ...request, layout: "not-declared" }), /layout/)
  } else {
    assert.equal(original.files.length, 1)
    assert.deepEqual(original.env, {})
    assert.ok(original.files[0].content.includes('input_driver = "udev"\n'))
    assert.throws(() => launch({ ...request, layout: "Top/Bottom" }), /layout/)
  }
  for (const id of systemIds) {
    const system = plugin.systems[id]
    if (id === "nds") {
      assert.deepEqual(system.panes, ["upper", "lower"], core)
      assert.equal(system.arrangement, "upper-above-lower", core)
    } else {
      assert.ok(!("panes" in system), `${core}/${id}: implicit single pane`)
      assert.ok(!("arrangement" in system), `${core}/${id}: no arrangement`)
    }
    assert.equal(system.id, id, core)
    assert.ok(system.title.length > 0, `${core}/${id}: title`)
    assert.ok(system.content?.extensions.length > 0, `${core}/${id}: content extensions`)
    for (const extension of system.content.extensions) {
      assert.equal(extension, extension.toLowerCase(), `${core}/${id}: lowercase extension`)
      assert.ok(!extension.startsWith("."), `${core}/${id}: no leading dot`)
      assert.ok(!["zip", "7z", "rar", "gz", "tar"].includes(extension), `${core}/${id}: no archives`)
    }
    if (content.has(id)) assert.deepEqual(system.content, content.get(id), `${id}: identical across cores`)
    content.set(id, system.content)
  }
  const applicable = Object.fromEntries(Object.entries(groups).filter(([, group]) =>
    group.systems.filter(id => systemIds.includes(id)).length >= 2,
  ))
  assert.deepEqual(plugin.groups ?? {}, applicable, `${core}: applicable groups`)
  for (const id of Object.keys(applicable)) seenGroups.add(id)
}
assert.deepEqual([...seenGroups].sort(), Object.keys(groups).sort())
assert.deepEqual(content.get("gba")?.extensions, ["gba", "agb"])
assert.deepEqual(content.get("nes")?.extensions, ["nes"])
assert.deepEqual(content.get("fds")?.extensions, ["fds"])
assert.deepEqual(content.get("lynx")?.extensions, ["lnx", "lyx", "bll"])
assert.deepEqual(content.get("sg1000")?.extensions, ["sg", "sc", "sf", "sg1", "sc3", "sf7"])
assert.ok(content.get("md")?.extensions.includes("md"), "Mega Drive keeps its real md suffix")
assert.deepEqual(content.get("nes")?.header, [{ size: 16, bytes: { offset: 0, hex: "4e45531a" } }])
assert.deepEqual(content.get("fds")?.header, [{ size: 16, bytes: { offset: 0, hex: "4644531a" } }])
assert.deepEqual(content.get("lynx")?.header, [
  { size: 64, bytes: { offset: 0, hex: "4c594e58" } },
  { size: 64, bytes: { offset: 6, hex: "425339" } },
])
assert.deepEqual(content.get("atari7800")?.header, [{ size: 128, bytes: { offset: 1, hex: "415441524937383030" } }])
assert.deepEqual(content.get("snes")?.header, [{ size: 512, remainder: { divisor: 1024, value: 512 } }])
assert.deepEqual(content.get("nes")?.evidence, { bytes: [{ offset: 0, hex: "4e45531a" }] })
assert.deepEqual(content.get("gba")?.evidence, { bytes: [{ offset: 4, hex: "24ffae51699aa2213d84820a84e409ad" }] })
console.log(`${Object.keys(expected).length} generated cores, ${content.size} systems, headers and all four groups passed`)

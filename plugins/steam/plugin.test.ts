import { describe, expect, test } from "bun:test"
import * as plugin from "./plugin"
import { artifacts, discovery, handlers, runners } from "./plugin"

// The plugin works under any publisher namespace (ADR 0045): CI publishes it
// as one id, a sideloaded test build as another. Nothing below may depend on
// which. These ids are fixtures of the tests, not of the plugin.
const PLUGIN_IDS = ["@test:steam", "@simonwjackson:steam"]

const manifest = (fields = "") =>
  `"AppState" { "appid" "401710" "StateFlags" "4" "name" "Flinthook" ${fields} }`
const discover = (text: string, pluginId = PLUGIN_IDS[0]) => handlers["discovery.discover"]({
  pluginId,
  files: [{ relativePath: "steamapps/appmanifest_401710.acf", text }],
})

const launchInput = (pluginId = PLUGIN_IDS[0]) => ({
  runnerId: `${pluginId}/steam`,
  program: "/nix/store/steam/bin/steam-session",
  ref: "401710",
  accountRoot: "/var/lib/korri/accounts/a",
  cacheRoot: "/var/lib/korri/cache",
  files: {
    "steam-session": "/nix/store/steam/bin/steam-session",
    "@korri:fex/config": "/nix/store/fex/share/fex-emu",
    "@korri:fex/fex-unpack": "/nix/store/fex/bin/fex-unpack",
    "@korri:proton/cachyos-unpack": "/nix/store/proton/bin/cachyos-unpack",
  },
  artifacts: {
    "@korri:fex/rootfs": "/var/lib/korri/cache/fex/rootfs/archlinux-2026-01-08-mesa-26.1.2",
    "@korri:proton/cachyos": "/var/lib/korri/cache/proton/cachyos/11.0-20260601-slr-arm64",
  },
})

describe("Steam launch declaration", () => {
  test("lists the FEX rootfs and Proton-CachyOS artifacts korrid must ready first", () => {
    expect(runners.steam.artifacts).toEqual(["@korri:fex/rootfs", "@korri:proton/cachyos"])
  })

  test("hands the session the FEX config file and the ready artifact directories", () => {
    const input = launchInput()
    expect(handlers["launch.prepare"](input)).toEqual({
      command: input.program,
      args: ["401710"],
      env: {
        STEAM_HOME: "/var/lib/korri/accounts/a/steam",
        KORRI_FEX_CONFIG: "/nix/store/fex/share/fex-emu",
        KORRI_FEX_ROOTFS: "/var/lib/korri/cache/fex/rootfs/archlinux-2026-01-08-mesa-26.1.2",
        KORRI_PROTON_CACHYOS: "/var/lib/korri/cache/proton/cachyos/11.0-20260601-slr-arm64",
      },
      directories: ["/var/lib/korri/accounts/a/steam"],
      envUnset: [],
    })
  })

  test("refuses the launch when Proton, or the FEX config beside the FEX rootfs, is missing", () => {
    const noProton = launchInput()
    delete noProton.artifacts["@korri:proton/cachyos"]
    expect(() => handlers["launch.prepare"](noProton)).toThrow("Steam requires @korri:proton/cachyos")
    const noFile = launchInput()
    delete noFile.files["@korri:fex/config"]
    expect(() => handlers["launch.prepare"](noFile)).toThrow("Steam requires @korri:fex/config")
  })

  test("passes no FEX paths on a device that skips the FEX rootfs (x86_64)", () => {
    const input = launchInput()
    delete input.artifacts["@korri:fex/rootfs"]
    input.artifacts["@korri:proton/cachyos"] =
      "/var/lib/korri/cache/proton/cachyos/11.0-20260601-slr-x86_64"
    expect(handlers["launch.prepare"](input).env).toEqual({
      STEAM_HOME: "/var/lib/korri/accounts/a/steam",
      KORRI_PROTON_CACHYOS: "/var/lib/korri/cache/proton/cachyos/11.0-20260601-slr-x86_64",
    })
  })
})

describe("Steam installed manifest declaration", () => {
  test("declares a local discovery id and names the installed game from VDF in its own namespace", () => {
    expect(discovery).toEqual([{ id: "installed-apps", title: "Steam installed apps" }])
    for (const pluginId of PLUGIN_IDS) {
      expect(discover(manifest(), pluginId)).toEqual([{
        kind: "provider-ref-release",
        confidence: "high",
        source: { relativePath: "steamapps/appmanifest_401710.acf" },
        target: { provider: pluginId, ref: "401710" },
        release: { id: "steam", title: "Flinthook", system: "steam" },
        launch: { use: `${pluginId}/steam` },
      }])
    }
  })

  test("refuses discovery without its plugin id", () => {
    for (const pluginId of ["", "steam", "@test:steam/x"]) {
      expect(() => discover(manifest(), pluginId)).toThrow("requires the plugin id")
    }
  })

  test("skips partial, corrupt, mismatched and unnamed manifests", () => {
    for (const text of [
      manifest().replace('"4"', '"1026"'),
      manifest().replace('"401710"', '"401711"'),
      manifest().replace('"name" "Flinthook"', ""),
      manifest().replace('"Flinthook"', '"   "'),
      '"AppState" {',
    ]) expect(discover(text)).toEqual([])
    expect(handlers["discovery.discover"]({pluginId: PLUGIN_IDS[0], files: []})).toEqual([])
  })

  test("excludes explicit non-game types but accepts missing type and nested VDF", () => {
    for (const type of ["Tool", "Proton", "Steam Runtime", "Steamworks Redistributables"])
      expect(discover(manifest(`"type" "${type}"`))).toEqual([])
    expect(discover(manifest('"type" "gAmE" "InstalledDepots" { "1" { "manifest" "2" } }'))).toHaveLength(1)
    expect(discover(manifest().replace('"4"', '"04"'))).toHaveLength(1)
    expect(discover(manifest().replace('"Flinthook"', '"Flint \\"hook\\""'))[0]?.release.title).toBe('Flint "hook"')
  })
})

// korrid passes the plugin's own artifacts under their local keys.
const engineInput = (pluginId = PLUGIN_IDS[0]) => ({
  ...launchInput(pluginId),
  runnerId: `${pluginId}/engine`,
  program: "/nix/store/steam/bin/steam-engine-session",
  artifacts: {
    ...launchInput(pluginId).artifacts,
    "engine-package": "/var/lib/korri/cache/steam/engine-package/1792618285",
  },
})

describe("Steam engine runner declaration (ADR 0083)", () => {
  test("is a second, ARM64-only runner with its own steps and the engine package", () => {
    expect(runners.engine.program).toBe("steam-engine-session")
    expect(runners.engine.systems).toEqual(["steam"])
    expect(runners.engine.platforms).toEqual(["aarch64-linux"])
    expect(runners.engine.steps.map(step => step.key)).toEqual(["update", "sync", "game"])
    expect(runners.engine.steps[0].label).toBe("Updating")
    expect(runners.engine.artifacts).toEqual([
      "@korri:fex/rootfs", "@korri:proton/cachyos", "engine-package",
    ])
  })

  test("pins Valve's engine package by name, sha2vz and size, with no unpack program", () => {
    const engine = artifacts["engine-package"]
    expect("id" in engine).toBe(false)
    expect("unpack" in engine).toBe(false)
    const build = engine.platforms["aarch64-linux"]
    expect(build.version).toBe("1792618285")
    expect(build.files).toEqual([{
      url: "https://client-update.steamstatic.com/bins_sdk_linuxarm64_linuxarm64.zip.vz.1424aaa33c34c7aa1b6f356fcda3678c210a62d6_10044409",
      sha256: "sha256:e043d05b4e7bcc43e22cc2be3e8872ed1132e79e989cbbe181eb3a5d3f849df7",
      bytes: 10044409,
    }])
    expect(Object.keys(engine.platforms)).toEqual(["aarch64-linux"])
  })

  test("declares no provider record: korrid derives the provider from the plugin id", () => {
    expect("providers" in plugin).toBe(false)
  })

  test("names no publisher namespace of its own anywhere in its declarations", () => {
    const declared = JSON.stringify({ ...plugin, handlers: undefined })
    const foreign = declared.match(/@[A-Za-z0-9_-]+:[A-Za-z0-9_-]+/g) ?? []
    // Only the required plugins of another publisher are named by full id.
    expect(new Set(foreign)).toEqual(new Set(["@korri:fex", "@korri:proton"]))
  })

  test("hands the session the person's engine folder, Proton and FEX, in any namespace", () => {
    for (const pluginId of PLUGIN_IDS) {
      const input = engineInput(pluginId)
      expect(handlers["launch.prepare"](input).command).toBe(input.program)
      const client = launchInput(pluginId)
      expect(handlers["launch.prepare"](client).command).toBe(client.program)
    }
    const input = engineInput()
    expect(handlers["launch.prepare"](input)).toEqual({
      command: input.program,
      args: ["401710"],
      env: {
        STEAM_ENGINE_HOME: "/var/lib/korri/accounts/a/steam-engine",
        KORRI_PROTON_CACHYOS: "/var/lib/korri/cache/proton/cachyos/11.0-20260601-slr-arm64",
        KORRI_FEX_CONFIG: "/nix/store/fex/share/fex-emu",
        KORRI_FEX_ROOTFS: "/var/lib/korri/cache/fex/rootfs/archlinux-2026-01-08-mesa-26.1.2",
      },
      directories: ["/var/lib/korri/accounts/a/steam-engine"],
      envUnset: [],
    })
  })

  test("refuses a launch without the engine package or with a ref that is not an appid", () => {
    const noEngine = engineInput()
    delete (noEngine.artifacts as Record<string, string>)["engine-package"]
    expect(() => handlers["launch.prepare"](noEngine)).toThrow("Steam requires engine-package")
    expect(() => handlers["launch.prepare"]({ ...engineInput(), ref: "401710;x" })).toThrow("provider ref")
  })
})

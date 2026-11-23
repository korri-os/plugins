import { describe, expect, test } from "bun:test"
import * as plugin from "./plugin"
import { artifacts, discovery, handlers, runners } from "./plugin"

// Declarations use full ids, as the published @korri:fex and @korri:proton.
const ID = "@korri:steam"

const manifest = (fields = "") =>
  `"AppState" { "appid" "401710" "StateFlags" "4" "name" "Flinthook" ${fields} }`
const discover = (text: string) => handlers["discovery.discover"]({
  files: [{ relativePath: "steamapps/appmanifest_401710.acf", text }],
})

const launchInput = () => ({
  runnerId: `${ID}/steam`,
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
  test("declares its closed provider by full id and names the installed game from VDF", () => {
    expect(discovery).toEqual([{ id: "@korri:steam/installed-apps", title: "Steam installed apps" }])
    expect(discover(manifest())).toEqual([{
      kind: "provider-ref-release",
      confidence: "high",
      source: { relativePath: "steamapps/appmanifest_401710.acf" },
      target: { provider: "@korri:steam", ref: "401710" },
      release: { id: "steam", title: "Flinthook", system: "steam" },
      launch: { use: "@korri:steam/steam" },
    }])
  })

  test("skips partial, corrupt, mismatched and unnamed manifests", () => {
    for (const text of [
      manifest().replace('"4"', '"1026"'),
      manifest().replace('"401710"', '"401711"'),
      manifest().replace('"name" "Flinthook"', ""),
      manifest().replace('"Flinthook"', '"   "'),
      '"AppState" {',
    ]) expect(discover(text)).toEqual([])
    expect(handlers["discovery.discover"]({files: []})).toEqual([])
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
const engineInput = () => ({
  ...launchInput(),
  runnerId: `${ID}/engine`,
  program: "/nix/store/steam/bin/steam-engine-session",
  artifacts: {
    ...launchInput().artifacts,
    "engine-package": "/var/lib/korri/cache/steam/engine-package/1792618285",
    legacycompat: "/var/lib/korri/cache/steam/legacycompat/1792618285",
  },
})

describe("Steam engine runner declaration (ADR 0083)", () => {
  test("is a second runner for both platforms with its own steps and the engine package", () => {
    expect(runners.engine.program).toBe("steam-engine-session")
    expect(runners.engine.systems).toEqual(["steam"])
    expect(runners.engine.platforms).toEqual(["aarch64-linux", "x86_64-linux"])
    expect(runners.engine.steps.map(step => step.key)).toEqual(["update", "sync", "game"])
    expect(runners.engine.steps[0].label).toBe("Updating")
    expect(runners.engine.artifacts).toEqual([
      "@korri:fex/rootfs", "@korri:proton/cachyos", "@korri:steam/engine-package",
      "@korri:steam/legacycompat",
    ])
  })

  test("pins Valve's engine package by name, sha2vz and size, with no unpack program", () => {
    const engine = artifacts["engine-package"]
    expect(engine.id).toBe("@korri:steam/engine-package")
    expect("unpack" in engine).toBe(false)
    const build = engine.platforms["aarch64-linux"]
    expect(build.version).toBe("1792618285")
    expect(build.files).toEqual([{
      url: "https://client-update.steamstatic.com/bins_sdk_linuxarm64_linuxarm64.zip.vz.1424aaa33c34c7aa1b6f356fcda3678c210a62d6_10044409",
      sha256: "sha256:e043d05b4e7bcc43e22cc2be3e8872ed1132e79e989cbbe181eb3a5d3f849df7",
      bytes: 10044409,
    }])
    // x86_64-linux: bins_sdk_ubuntu12 of steam_client_ubuntu12, the same client version.
    expect(engine.platforms["x86_64-linux"]).toEqual({
      version: "1792618285",
      files: [{
        url: "https://client-update.steamstatic.com/bins_sdk_ubuntu12.zip.vz.e9ae6bc8e0116bd6d8ec14af21362f9f7399ea5c_24063512",
        sha256: "sha256:f03c33ea25ab007550e91b39a682660ccc53426dde6764256b3fe07a5c6833f6",
        bytes: 24063512,
      }],
    })
    expect(Object.keys(engine.platforms)).toEqual(["aarch64-linux", "x86_64-linux"])
  })

  test("pins Valve's legacycompat package of the same client version, with its unpack program", () => {
    // korri#589: bins_misc_linuxarm64 of steam_client_steamdeck_stable_linuxarm64
    // 1792618285 carries legacycompat/ (steamclient.dll, steamclient64.dll, Steam.dll).
    const legacycompat = artifacts.legacycompat
    expect(legacycompat.id).toBe("@korri:steam/legacycompat")
    expect(legacycompat.unpack).toBe("steam-legacycompat-unpack")
    expect(Object.keys(legacycompat.platforms)).toEqual(["aarch64-linux", "x86_64-linux"])
    // Valve serves the same file under the x86_64 manifest's name.
    expect(legacycompat.platforms["x86_64-linux"]).toEqual({
      version: "1792618285",
      files: [{
        url: "https://client-update.steamstatic.com/bins_misc_ubuntu12.zip.vz.c1fe69f2ddbbfd3d89ae14f20185fcf878df5cc8_19812282",
        sha256: "sha256:8888138451bc088adb1ce222a22d63214c1d3b249a06604c844634dfd9a004b3",
        bytes: 19812282,
      }],
    })
    const build = legacycompat.platforms["aarch64-linux"]
    expect(build.version).toBe(artifacts["engine-package"].platforms["aarch64-linux"].version)
    expect(build.files).toEqual([{
      url: "https://client-update.steamstatic.com/bins_misc_linuxarm64.zip.vz.c1fe69f2ddbbfd3d89ae14f20185fcf878df5cc8_19812282",
      sha256: "sha256:8888138451bc088adb1ce222a22d63214c1d3b249a06604c844634dfd9a004b3",
      bytes: 19812282,
    }])
  })

  test("names only its own id and its required plugins' ids, so a test build rewrites one string", () => {
    const declared = JSON.stringify({ ...plugin, handlers: undefined })
    const ids = declared.match(/@[A-Za-z0-9_-]+:[A-Za-z0-9_-]+/g) ?? []
    expect(new Set(ids)).toEqual(new Set(["@korri:steam", "@korri:fex", "@korri:proton"]))
  })

  test("hands the session the person's engine folder, Proton, FEX and legacycompat", () => {
    const input = engineInput()
    expect(handlers["launch.prepare"](input)).toEqual({
      command: input.program,
      args: ["401710"],
      env: {
        STEAM_ENGINE_HOME: "/var/lib/korri/accounts/a/steam-engine",
        KORRI_PROTON_CACHYOS: "/var/lib/korri/cache/proton/cachyos/11.0-20260601-slr-arm64",
        KORRI_FEX_CONFIG: "/nix/store/fex/share/fex-emu",
        KORRI_FEX_ROOTFS: "/var/lib/korri/cache/fex/rootfs/archlinux-2026-01-08-mesa-26.1.2",
        KORRI_STEAM_LEGACYCOMPAT: "/var/lib/korri/cache/steam/legacycompat/1792618285",
      },
      directories: ["/var/lib/korri/accounts/a/steam-engine"],
      envUnset: [],
    })
  })

  test("refuses a launch without the engine package, legacycompat or with a ref that is not an appid", () => {
    const noEngine = engineInput()
    delete (noEngine.artifacts as Record<string, string>)["engine-package"]
    expect(() => handlers["launch.prepare"](noEngine)).toThrow("Steam requires engine-package")
    const noLegacycompat = engineInput()
    delete (noLegacycompat.artifacts as Record<string, string>).legacycompat
    expect(() => handlers["launch.prepare"](noLegacycompat)).toThrow("Steam requires legacycompat")
    expect(() => handlers["launch.prepare"]({ ...engineInput(), ref: "401710;x" })).toThrow("provider ref")
    expect(() => handlers["launch.prepare"]({ ...launchInput(), ref: "" })).toThrow("provider ref")
  })
})

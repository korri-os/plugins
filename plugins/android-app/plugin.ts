import type {
  AndroidLaunchOutput,
  InstalledAppsDiscoveryInput,
  PluginLaunchInput,
  ProviderRefReleaseObservation,
} from "../../contracts/generated/korrid"

// Native Android games installed on the phone (Korri ADR 0054).
//
// The shape is legacy @korri:android-app: system `android`, and the package
// name as the provider ref. Discovery follows @korri:steam: the Android app
// reports its launchable apps, this handler picks the games, and korrid's
// existing reconciliation writes the library. Apps the person adds are kept
// too. Nothing here starts, reads or downloads anything.
export const name = "android-app"
export const title = "Android"
export const description = "Plays games installed on this Android device."

export const discovery = [
  { id: "@korri:android-app/installed-apps", title: "Installed Android games" },
]

export const systems = {
  android: { title: "Android" },
}

export const runners = {
  "android-app": {
    platforms: ["aarch64-android"],
    // No androidPackages: each game's provider ref is its package, and
    // korrid allows exactly that package for that launch.
    systems: ["android"],
  },
}

function discoverInstalledApps(
  input: InstalledAppsDiscoveryInput,
): ProviderRefReleaseObservation[] {
  return input.apps
    .filter((app) => app.isGame || app.added)
    .filter((app) => app.label.trim() !== "")
    .map((app) => ({
      kind: "provider-ref-release",
      confidence: "high",
      source: { relativePath: `installed-apps/${app.packageName}` },
      target: { provider: "@korri:android-app", ref: app.packageName },
      release: { id: "android", title: app.label.trim(), system: "android" },
      launch: { use: "@korri:android-app/android-app" },
    }))
}

// The app is the game: start its current launcher activity. Android may
// rename that activity in an update, so the plugin names only the package.
function prepareLaunch(input: PluginLaunchInput): AndroidLaunchOutput {
  if (!input.ref) {
    throw new Error("An Android game is named by its package")
  }
  if (input.contentPath !== undefined) {
    throw new Error("An Android game takes no content file")
  }
  if (Object.keys(input.overrides?.settings ?? {}).length > 0) {
    throw new Error("Android games have no Korri launch settings")
  }
  return { android: { package: input.ref } }
}

export const handlers = {
  "discovery.discover": discoverInstalledApps,
  "launch.prepare": prepareLaunch,
}

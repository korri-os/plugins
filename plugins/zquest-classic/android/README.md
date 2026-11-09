# zquest-classic on Android (Korri ADR 0054, case 2) — recipe only

This folder holds the build recipe that produced the APK now running on the
owner's Fold7, moved verbatim from aka (`/var/lib/zquest-android-build`,
session 01a1bece). It is not wired into the plugin yet.

Done:
- The APK builds on aka and runs on the Fold7 (debug-signed).
- `korri-fixes.patch`: controller handling, full screen, touch pad hidden
  while a controller is connected.

Next, before an Android runner is added to `plugin.ts`:
1. Replace the store-path `import` in the Nix files and the `/var/lib`
   paths in the scripts with Korri's flake nixpkgs and a work-folder argument.
2. Saves: the port runs in Allegro's user data path (the app's internal
   files folder) and writes `standalone-<quest>.sav` there, beside the
   resources and imported quests (`android-port.patch`, `main`). The bridge
   copies whole folders, so add one line to `korri-fixes.patch` that writes
   saves to a `saves/` subfolder, then integrate the bridge with
   `integrate.py <app> "save=internal:saves"` (korri supports `internal:`
   since `feat/android-plugin-foundation`).
3. Confirm, from the source, how the app accepts a quest file from another
   app, then add the runner with that launch.
4. Give the APK Korri's package name and signing key.

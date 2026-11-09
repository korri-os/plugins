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
2. Find the app's real save folder in its source, then add the Korri save
   bridge with korri's `clients/android-save-bridge/integrate.py`. The
   bridge maps folders under `getExternalFilesDir(null)`; this app keeps
   files under `getFilesDir()`, so the bridge needs an internal-storage form.
3. Confirm, from the source, how the app accepts a quest file from another
   app, then add the runner with that launch.
4. Give the APK Korri's package name and signing key.

# Starter pack

This contains 24 selected games and 25 original PNG cartridge files.
Into Ruins needs the developer's two-file offline release.
The pack contains credits, source notices, the noncommercial CC BY-NC-SA 4.0 license and checksums.
It includes no PICO-8 application, emulator, native service, installer or library registration.

## Use the cartridges

The Korri plugin requires the separate `@korri:fake08` plugin.
Core must approve each exact package under its own publisher binding before activation.
Enabling the approved pack activates FAKE-08 first.
The standalone cartridge output has no player dependency; supply a compatible player when using it alone.
Copy the complete pack to the device.
Keep `CREDITS.md`, `CC-BY-NC-SA-4.0.txt` and `notices/` with the cartridges when sharing them.
Add the `cartridges/` folder manually to your player's library or cartridge search path.
Installing this Korri package does not perform that step or add game tiles.

The PNG images contain code, graphics, maps and sound data.
Do not resize, image-optimize or resave them as ordinary images.
Their original names are preserved; `CREDITS.md` maps numeric filenames to game titles.
To verify the copied cartridge bytes, run this from the pack directory:

```sh
cd cartridges
sha256sum --check ../SHA256SUMS
```

## Into Ruins

Keep `intoruins.p8.png` and `intoruins_main.p8.png` together under their original names.
Start `intoruins.p8.png`, not the main file alone.
The title initializes the game data before loading the main cartridge.
The author's offline pair loads local filenames rather than downloading BBS cartridges.
Your player must support this two-cartridge loading and memory handoff.

The selected FAKE-08 core loaded the second cartridge in a headless runtime test but then failed.
It reported `attempt to concatenate field '?' (a nil value)` in cart 2.
The cause is not yet proven. This is not a passing Into Ruins compatibility test.
The cartridges remain unchanged; do not remove or edit the companion to hide the failure.

The pack uses unmodified offline files from the developer's pinned repository.
`notices/intoruins-offline.txt` records the original archive, hashes and license.
No PICO-8 runtime or exported native executable from that archive is included.

## Known limits

These are licensed source releases, not a compatibility-tested game collection.
Witchbeat is a work-in-progress release without input-lag calibration.
A Dungeon Solitaire player reports a final-level move-check defect.
PICORACER-2048's displayed release is a beta with missing features and a documented Q menu key.
DeFacto saving uses the pause menu and needs persistent player storage.

Building requires the pinned original files to remain available or already exist in the Nix cache.
A changed download fails its hash check rather than silently updating a game.
The checks verify package contents, cartridge structure and byte hashes.
They check the presence of credits, license text and source notices, not rights ownership or gameplay.
Published licenses do not independently prove every contributor's ownership or grant creator endorsement.

## Korri integration

`plugin.ts` exports identity only.
`plugin.nix` uses the existing native `packages`, `files` and `requires` fields.
The dependency names an exact FAKE-08 Korri plugin output, not a raw core or RetroArch package.
Core's supported builder generates the plugin manifest.
The `files.cartridges` entry names the packaged cartridge directory.
The other named files expose credits, license, notices, checksums and these instructions.
There are no game, runner, discovery, service or permission contributions.

This package claims `@korri:starter-pack` with the displayed title `Starter pack`.
That manifest claim alone establishes no device trust.
Building does not sign or publish a cache, configure a signing key, install trust or approve device installation.
Normal signature checks and exact-package approval remain required for plugin installation.
Both this pack and FAKE-08 need approval for their exact outputs under the administrator's `@korri` publisher binding.
No command in this package installs that trust binding.

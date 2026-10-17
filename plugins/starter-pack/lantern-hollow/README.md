# Lantern Hollow

An original, short ZQuest Classic quest made for the Korri Starter pack.
The lanterns of the Hollow have gone dark. Take the sword, go under the hill,
find two keys, get past the Hollow Keeper, and reach the Great Lantern.

- File: `lantern-hollow.qst` (unpacked quest; play it with `@korri:zquest-classic`).
- Length: about 10 to 20 minutes. One village (six screens) and one dungeon
  (seven rooms). Three hearts, one heart vessel, two keys, one boss.
- Controls: D-pad or stick to move, A to swing the sword, START to pause.
- License: CC0 1.0 (`LICENSE.txt`). Third-party assets are CC0 too; see `ASSETS.md`.

## Why this quest exists

On 2026-10-17 every quest in the public ZQuest Classic archive (795 quests,
`data.zquestclassic.com`) was screened for a published redistribution grant and
for Nintendo or other commercial material. None passed both tests. Lantern
Hollow was built instead, only from CC0 assets and original work.

## How it was made

The engine has no blank new-quest template. The quest was therefore saved by
a private ZQuest Classic editor build (revision
`882c906b17e35b4105188e6305ae2929aeba30e3`, the same revision as the player)
with one added headless command, `-lh-build` (`source/lh_recipe.inc`). That
command loads the engine's classic template and then, before saving through the
engine's own writer:

1. blanks every tile, combo, combo alias, map screen, palette and palette name;
2. blanks every item, enemy, weapon-sprite and drop-set name, every message
   string, DMap, door set, shop and info record, every embedded sound and every
   MIDI, and the interface colour references;
3. rebuilds the status and pause subscreens from scratch;
4. writes Lantern Hollow's own tiles, palettes, combos, rooms, enemies, items,
   text, sounds and music from `source/make-recipe.py`.

Numeric engine definitions from the template remain (for example item and
enemy behaviour values such as speed and damage). They contain no artwork,
sound, music or text.

## Checks performed (2026-10-17)

- `source/residue-gate.py` unpacks the saved quest and searches every readable
  byte run for franchise and stock-template words. Result: no hits. The only
  allowed match is the engine's own four-byte section tag `LINK`.
- The published public player (`@simonwjackson:zquest-classic` public3) ran the
  quest headless with scripted input (`source/play.py`). Screenshots confirmed
  the intro text, sword in all directions, screen scrolling, the hill entrance,
  enemies and drops, a key appearing after a room is cleared, the key opening a
  lock door, the boss, and the built-in ending reached at the Great Lantern.
- The CI check `korri-starter-pack-lantern-hollow` loads the quest in the
  packaged engine and replays a short input sequence on every build.

Not checked: a complete human playthrough on every device, balance, and every
enemy and room combination.

## Rebuilding

The tools in `source/` are the exact scripts used. Rebuilding needs the private
authoring editor (`source/editor.nix`, `source/dev-build.sh`,
`source/make-overlay.sh`), which uses upstream's stock resources. Never publish
that editor build or its resources. Run it on a build machine, not a device.

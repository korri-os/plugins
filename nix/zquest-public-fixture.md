# Original ZQuest runtime fixture

These quests are test content, not bundled games. Keep this derivation out
of the public plugin and engine runtime outputs.

## Provenance

`zquest-public-fixture.py` creates every content byte from source literals and
integer geometry. It has no asset inputs, downloads, random values, clock reads,
or imports from an existing quest. The room, diamond player, floor calibration
marks, RGB palette, title, and author label are original. There is no music,
sampled sound, dialogue, item artwork, enemy artwork, or script in the quest.
The generator and generated content use CC0-1.0; see `LICENSE.txt`.

The serialization reference is ZQuestClassic revision
`882c906b17e35b4105188e6305ae2929aeba30e3`: `src/core/qst_header.cpp`,
`qst_tiles.cpp`, `qst_csets.cpp`, `qst_colors.cpp`, `qst_combos.cpp`, `qst_maps.cpp`,
`qst_dmaps.cpp`, `qst_initdata.cpp`, `qst_herosprites.cpp`, the corresponding
native writer in `src/zq/zq_class.cpp`, and `src/zalleg/packfile.h`.
The win variant also uses the `mfZELDA` constant in `src/core/zdefs.h` and
its normal ending dispatch in `src/zc/hero.cpp` (`checkspecial2`, `win_game`)
and `src/zc/zelda.cpp` (`qWON`). Only format field widths/order and native
constants informed this generator. Native save-menu colors/cursor references
come from `ResetSaveScreenSettings` in `src/zc/zelda.cpp`, `src/zc/title.cpp`,
and `overtile8` in `src/tiles.cpp`.
No upstream `.qst`, template, image, sound, palette, or text asset was read or
transformed to make the fixture.

## Reproduce

```sh
python3 nix/zquest-public-fixture.py /tmp/public-room.qst
python3 nix/zquest-public-fixture.py --variant missing-tiles /tmp/public-missing-tiles.qst
python3 nix/zquest-public-fixture.py --variant win /tmp/public-win.qst
```

These hashes replace the earlier fixtures, which omitted native menu colors
and a visible cursor and therefore failed on a clean engine.

| Output | Bytes | Purpose |
| --- | ---: | --- |
| `public-room.qst` | 436,982 | Movement, screenshot, save/continue |
| `public-missing-tiles.qst` | 436,208 | Missing embedded tiles rejection |
| `public-win.qst` | 436,982 | Normal built-in ending, START, save/return |

SHA-256:

```text
abb02a7aa1810a60892435b596f3426c192ef15182c96799e3db67bdc739cd67  public-room.qst
ad34840bd5efc3d4e8ecfc9a2b16d8166cb82e94e16ef2c214ba343e6eaccbbd  public-missing-tiles.qst
088c9c9c0e31ed8cf3316ecab3b4aa4e37faffb307a8666d40438af0c606ab79  public-win.qst
```

The Nix derivation generates each variant twice, compares the results, and
checks fixed hashes. Its output includes `SHA256SUMS`, `generate.py`, this
provenance document, and the license. It needs Python only; no editor build or
engine resources are required. Import `nix/zquest-public-fixture.nix` with
`{ inherit pkgs; }` and use `${fixture}/public-room.qst` (or either variant) in
test commands.

## Scope and native checks

The base room has one 16-by-11 screen with an impassable perimeter, a walkable
interior, and a geometric diamond player at `(120, 80)`. The screenshot has nine RGB colors.
There are no enemies, items, scripted actions, or exits. Arrow-key input moves
the player. Native save/continue menus and screenshots remain engine features.

The native `MCLR` v4 section sets `msgtext=15` and `caption=14`, with explicit
colors for the other native fields. The save-menu cursor is an original
7-pixel-wide diamond in 8x8 quarter-tile 2 (tile 0's lower-left quarter),
using palette entry 14. The engine chooses cset 1 for that cursor; the fixture
defines every cset. No inherited quest colors or cursor art are needed.

Verified locally under Xvfb on the clean x86_64 engine
`/nix/store/svk7zmdjmrfvij4g16gwc47vpq0y2dgk-zquest-classic-unstable-2026-06-18-public1`:
every section loaded, `F6`, `Return`, `Down`, `Return` each caused a visible
pixel change, the native save changed, a backup appeared, and the room
reloaded. `F10`, `Return` each caused a visible response and exited with status
zero. Sound was disabled for this local probe. The prior fixture reproduced
the black menu and failed the same Down pixel-response assertion on this
binary. Neither that assertion nor the engine was changed for this fix.
The parent runtime check must repeat the final fixture with audio enabled
and on both supported architectures.

The quests deliberately omit unused native sections and rely on their
empty runtime defaults. They do not test ZScript, music playback, equipment,
combat, or a full game's compatibility. An old engine may load its own default
sound/UI resources; those are neither inputs to nor embedded in these fixtures.

### Missing-tiles gate

The modern header keeps the base room's native 2.55/61 version and clears
`data_flags[ZQ_TILES]`. The normally framed `TILE` section declares zero tiles.
It remains present so the native dispatcher calls `readtiles`; simply omitting
that section would not exercise the missing-tiles check. No tile pixels occur
in this negative fixture. Other sections remain unchanged.

The clean player must reject this fixture with `qe_missing_tiles` (15), whose
diagnostic starts `This quest needs legacy default tiles (190_tiles.qst)`.
It must not create a playable save, render the room, or try the old
`assets/190_tiles.qst` fallback. Check actual file accesses with
`strace -f -e trace=file`, not only the diagnostic. Verified on the clean
x86_64 engine named above: the expected diagnostic appeared, no successful
quest metadata or native save appeared, and the file-access trace contained
no `190_tiles.qst` access. A pre-clean player is not expected to pass this gate.

### Built-in ending gate

Only one map flag differs from the base room: screen 0's floor cell `(10, 5)`
has `mfZELDA=15`. Coordinates are zero-based tiles; that cell covers pixels
`x=160..175, y=80..95`. There is no script, custom ending text, or extra art.
The flag invokes `win_game()`, dispatches `qWON`, and enters normal `ending()`,
not `ending_scripted()`.

Use a fresh standalone save and the default keyboard mapping:

1. Wait for the initial room and focus the player window.
2. Hold Right for 0.8 seconds, then release. This crosses the win cell from
   the initial `(120, 80)` position at normal frame speed.
3. Observe the native ending. After 30 seconds, press and release Return
   (START) once per second until the save changes and quest metadata reloads.
   The scrolling credits consume early START presses. The final wait accepts
   a fresh press. Allow 150 seconds on slow software-rendered hosts.
4. Assert that the native save changed and a backup exists. Check the return
   to the room. Exit with F10, then Return, and require status zero.

The earlier fixture completed this sequence on a pre-clean x86_64 player
at 53.6 seconds after movement. The final fixture reaches the clean engine's
`QUEST COMPLETE.` / `WELL DONE.` presentation, but that build then stalls
for at least 150 seconds without saving or returning. A GDB capture shows
`midi_player -> midi_seek -> midi_player` on a timer thread; the main thread
waits in `render_timer_wait -> advanceframe -> ending`. This is a separate
ending MIDI/timer blocker, not a passing completion gate. The local probe
used `nosound=1`; repeat with the parent's audio-enabled setup and resolve
the engine/resource blocker before treating the ending as verified.
No engine/resource workaround or relaxed assertion was added to this fixture.

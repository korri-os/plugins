# Public-player source patch

Applies with `patch -p0` to engine revision
`882c906b17e35b4105188e6305ae2929aeba30e3`.
This patch is for the player-only package. It adds no runtime files or config
keys. Package/resource changes are separate.

## Behavior

- `null_quest()` no longer opens `modules/classic/title_gfx.dat`. It resets
  the first 238 tile slots and generates rectangular life-meter cells and
  square save/completion markers at the existing tile indices. It registers
  their blank-tile/quarter flags and fills all color-data banks with neutral
  grayscale values. It rebuilds these buffers on each menu/credits entry;
  a previous user's quest cannot leave its own graphics in those slots.
- The existing save-menu coordinates, paging, name entry, input, scaling,
  save icons from user saves, and save/load code remain intact. The selection
  cursor is a square instead of the former artwork. Menu life cells are
  rectangles instead of the former artwork.
- The built-in ending uses generic quest-complete text instead of Nintendo
  staff credits, the stock game title, stock story text, and Hyrule wording.
  The credits border is an Allegro rectangle, not a quest tile. The ending
  selects the replacement `assets/ending.mid`, without a `zelda.nsf` probe.
- Ending message buffers start empty. Only custom endings read `MsgStrings`.
  Each of the two message indices must be below both `msg_count` and the
  allocated `msg_strings_size`. Each line copies at most 24 bytes after
  checking its offset. Missing messages and missing tails stay empty;
  normal custom messages retain their six 24-byte lines. Initialization
  precedes the credits-skip jump so the C++ jump does not bypass it.
- Ending animation, user-provided ending messages, user quest sprites during
  the pre-credits sequence, hero win scripts, scripted endings, native START
  handling, volume restoration, quest reload, saves, and replay writes remain.
  This is not a removal of user quest content or a redesign of gameplay.
  The legacy celebration logic/item IDs remain intentionally unchanged.
- Quests with `!Header->data_flags[ZQ_TILES] && !from_init` fail with the new
  `qe_missing_tiles` error (appended, preserving existing error numbers).
  No legacy default-tile file is opened. The message is:

  > This quest needs legacy default tiles (190_tiles.qst), which this player does not include. Use a quest with embedded tiles.

  `readtiles` returns the error through the existing `checkstatus` path.
  `loadquest` clears the legacy skip-flags pointer and restores saved load
  globals on failure. `load_quest` does not replace a failed load's error with
  a stale minimum-version error or copy its stale title/version into a save.
- No active player dependency on `modules/classic/default.qst` was found.
  Its tile/combo/color initializers have editor callers. Item/weapon template
  resets explicitly require `App::zquest`. No changes to those editor helpers
  are needed for this player-only package. Omit the file from installation.
- Engine and dependency license notices are not removed.

## Resource-generation interface

| Resource | Requirement retained by this patch |
| --- | --- |
| `modules/classic/classic_fonts.dat` | Mandatory count/signature and indexed-font loading remain. Save menus and ending use `font_zfont`, mapped to `FONT_NES`. Supply an original/licensed 8-pixel-cell font here, including ASCII and glyphs 132/133 for left/right paging arrows. Dialogs use other indexed fonts; keep all required slots. |
| `assets/cursor.bmp` | Still mandatory. Player reads a 16×16 rectangle beginning at (1,1). Preserve the indexed bitmap layout and transparent index 0. `recolor_mouse` recognizes indices 241, 242, 243, and 245 (`dvc(1/2/3/5)`). |
| `sfx.dat` | Mandatory signature and sample indices remain. `null_quest` still restores default SFX when needed. |
| `assets/*.mid` | All seven startup-loaded default MIDI files remain required. Ending now uses `ZC_MIDI_ENDING` directly. |
| Menu logo | Optional `assets/logo.png`, then `assets/zc/ZC_Logo.png`; absent images select the existing text fallback. |
| Compiled `nes_pal` | The separate palette replacement is still needed if required by the package audit. Existing menu highlights/flashes use `NESpal`; this patch replaces color data formerly loaded from the title quest, not that separate compatibility table. |

No `title_gfx.dat`, replacement quest-format menu resource, `190_tiles.qst`,
or player `default.qst` is required.

The current generator fits Tiny5's common game glyphs to the existing slot
advances and heights. This does not enlarge text or change this patch's
font-loading interface. Uncovered Unicode/symbol glyphs use ProggyVector,
which also remains for the debugger. Keep the complete Tiny5 OFL and
ProggyVector notices with generated fonts. The corresponding-source recipe
includes the Tiny5 glyph table and OFL notice as regeneration inputs.
Preserved metrics do not prove that every user quest's custom text layout fits.

## Verified checks

- Read the pinned source directly; `tiles.h` exports `newtilebuf`,
  `reset_tile`, and `register_blank_tiles(int32_t)`. `zalleg/colors.h` exports
  `colordata` and `psTOTAL255`. `zc_sys.cpp` already includes both headers.
- The patch passes `patch --dry-run -p0` against the untouched baseline.
- GCC 14.3.0 compiled all five changed C++ translation units on x86_64:
  `core/qst.cpp`, `core/qst_tiles.cpp`, `zc/zc_sys.cpp`, `zc/ending.cpp`,
  and `zc/zelda.cpp`, using upstream CMake-generated compile commands and
  the existing package's Nix development environment. The updated `qst.h`
  was included in those builds. Existing upstream warnings remain.
- This was object compilation, not a full player link or device execution.
  Local build directory: `/tmp/korri-public-player-build`. Compile logs:
  `/tmp/korri-public-player-compile.log`,
  `/tmp/korri-public-player-compile-final.log`, and
  `/tmp/korri-public-player-zelda-compile.log`.
- Follow-up bounds fix: recompiled `zc/ending.cpp` with GCC 14.3.0. Log:
  `/tmp/korri-public-player-ending-bounds-compile.log`. A C++ harness extracted
  the exact copy block and passed 22 cases with AddressSanitizer and UBSan:
  default `(None)`, null buffer, missing first/second messages, count/capacity
  limits, maximum word index, lengths around 24/48/72 bytes, and embedded NUL.
  Harness: `/tmp/korri-public-player-ending-bounds-test.py`. This tests the
  message-copy block, not the complete rendered ending.

## Remaining acceptance checks and costs

Run complete x86_64/aarch64 builds and the package's resource inventory check.
Test sound-enabled startup, save paging/arrows, name entry, save/reload, and
both ordinary and scripted endings. Exercise a genuinely old quest without
tiles, then load a valid quest in the same process. Verify the explicit error
and that a previous quest's minimum-version metadata does not mask it.

The new appearance differs. Old quests needing stock tiles are unsupported.
User-provided quests/saves still contain their own graphics, text, and audio;
this patch does not establish redistribution rights for them. No claim of
whole-engine legal clearance or rendered-menu/ending validation is made here.

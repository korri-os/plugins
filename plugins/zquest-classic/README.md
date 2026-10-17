# ZQuest Classic

`@korri:zquest-classic` runs unpacked `.qst` files with the native
ZQuest Classic player on Linux x86_64 and aarch64. It does not include the
quest editor, a quest downloader, or automatic game registration.

## Source and integration

The engine pin, dependency pins, and ARM tile-rendering patch come from
Korri's read-only `legacy` branch at
`product/plugins/zquest-classic/packages/zquest-classic/`.
The source is [ZQuestClassic/ZQuestClassic at
882c906b17e35b4105188e6305ae2929aeba30e3](https://github.com/ZQuestClassic/ZQuestClassic/tree/882c906b17e35b4105188e6305ae2929aeba30e3),
from June 18, 2026. This is a development snapshot, not a claim to package
the latest stable release. Quests that require later engine changes can fail.

The system identity `zelda-classic`, title `Zelda Classic Quest`, runner name
`zplayer`, `.qst` discovery extension, and `-standalone` launch mode preserve
legacy's producer. The plugin moved on 2026-10-17 from the personal
`simonwjackson/korri-plugins` repository (`@simonwjackson:zquest-classic`,
revision `dd1fae9`) to this repository's `@korri` namespace so the Starter
pack can require it. There is no alias for the old publisher; a device that
uses the personal plugin needs separate normal approval for `@korri:zquest-classic`.

The source declaration performs no effects. It returns the approved launcher,
the literal quest path, and an account-owned state directory. Core performs the
launch under its existing policy. No Core schema or permission expansion is
required. Unsupported launch overrides and libretro cores are rejected.

Build machines compile the native player from a cleaned source tree. Devices
receive prebuilt outputs. Both architectures use the ZScript interpreter,
following the legacy package.
The ARM patch selects upstream's scalar tile renderer instead of x86 SIMD.
This costs performance for script-heavy quests. The package disables the
updater, WebSocket scripting, and native file-dialog dependency.

The native `allegro.cfg` selects Allegro's built-in DIGMID software synthesizer.
Its patch index is generated from FreePats' existing `crude.cfg` mappings.
This avoids upstream's ALSA MIDI autodetection crash when `/dev/snd/seq` is
absent, as on the Mini V2. It keeps sound effects and music enabled without
a new device service or kernel change. FreePats adds about 33 MiB and uses
substitute or omitted instruments where its tone bank is incomplete. The original
FreePats license and mapping remain in the closure.

`sound-thread-timeout.patch` initializes the legacy audio worker's timeout
before each wait, matching its keyboard, mouse, timer, and joystick workers.
The original worker passed an uninitialized timeout. Sound-enabled ARM checks
exposed stalls that the original muted checks did not cover.

## Public resource build

The public package contains no bundled quest, NSF soundtrack, original
sound bank, or original bitmap-font collection. It does not clear the rights
to quests supplied by users. The publication audit is in
docs/research/zquest-publication-audit.md (personal repository record).

| Resource | Public build behavior |
|---|---|
| Default sound effects | 61 original generated cues keep the existing numeric sound slots. They do not imitate the original game recordings. |
| Default MIDI music | Seven valid silent tracks satisfy the native loader. Quest-provided music still plays. |
| Runtime fonts | Common game glyphs use Tiny5 fitted to the existing character widths and line heights. Uncovered Unicode/symbol glyphs use ProggyVector. Special game alphabets are not reproduced. |
| Native menus and ending | Original geometric markers and neutral completion text replace the stock presentation. User quest content is not changed. |
| Old quests without embedded tiles | Rejected with a missing-default-tiles explanation instead of loading stock artwork or displaying broken graphics. |
| Optional editor/example material | Not included in the runtime resources. |

The separately licensed ZQuest Commons logo, icon and theme music remain with
their terms and credits. Tiny5 derivatives retain the complete SIL OFL 1.1
notice. ProggyVector remains for the debugger and uncovered glyphs with its
font license. FreePats remains the software MIDI instrument bank. Resource generation,
format requirements and notices are in [ASSET-LICENSES.md](ASSET-LICENSES.md).

The player sounds and looks different from upstream. Tiny5 changes common
glyph shapes; it is not a larger-text setting. Very small or narrow cells can
lose detail when fitted. Unusual script glyphs can lose meaning when replaced
with licensed generic glyphs. The resource checks validate their format and
origin inputs, not every community quest's layout.

## Saves and configuration

The owner selected account-owned storage and content-hash save identity on
2026-10-02. State resides beneath `${input.accountRoot}/zquest-classic`,
following the existing Zelda3 account-storage pattern.

The launcher hashes the complete quest with SHA-256, as Core's file scanner
already does. It passes `sha256:<digest>.sav` as upstream's explicit standalone
save filename. There is one native save slot per quest release per account.

| Native path inside the account directory | Purpose |
|---|---|
| `zc.cfg` and `controls.cfg` | The player writes its native configuration and control schemes. |
| `saves/sha256:<digest>.sav` | The native standalone save for these exact quest bytes. |
| `saves/backup/` | The player keeps its native save backups here. |
| `replays/` and `allegro.log` | Upstream replay and diagnostic output remains account-owned. |
| Shipped resource names such as `assets/`, `modules/`, and `base_config/` | Links to immutable resources in the exact installed package. |

Moving or renaming a quest retains its save. A narrow engine patch makes
standalone mode use the newly selected path when loading an existing save.
Different quests with the same filename get different saves. Updating quest
bytes produces a separate save. Moving an older save to an updated quest is
an explicit user operation and depends on that quest's save compatibility.

The launcher holds a directory lock across native execution. A second session
for the same account fails rather than sharing configuration and saves.
Package updates refresh resource links. The launcher refuses to replace local
files or foreign links at those resource names. Edit `zc.cfg` while the player
is stopped. Changing upstream's `save_folder` setting changes where it writes
saves.

## Handheld settings

The owner chose these launcher settings on 2026-10-02. The launcher writes
them into the account's native files before every start. It changes only the
named keys and keeps every other line.

| Setting | Where | Effect |
|---|---|---|
| `-fullscreen` | command line | The player fills the screen. Upstream starts windowed. It overrides `fullscreen` in `zc.cfg`. |
| `replay_upload_prompt = 1` | `zc.cfg`, `[zeldadx]` | Upstream's upload question is marked as asked. `replay_upload` keeps its value; upstream's default is off. The plugin does not consent for the user. |
| `clicktofreeze = 0` | `zc.cfg`, `[zeldadx]` | A touch or click does not open the system menu. |
| `btn_menu = 0` | every scheme in `controls.cfg` except `Default` | The gamepad menu button does not open the system menu. |
| `joystick_name = Korri Seat P1` | the same schemes | Selects the seat where Korri sends the device's own controls. |
| `btn_s = 8`, `btn_ex2 = 10` | the same schemes | Start opens the subscreen; Extra2 moves to the left-stick click. |

Upstream resets the `Default` scheme on every start, so it cannot hold these
keys. When the global scheme is `Default` or missing, the launcher selects
`Custom`, the scheme upstream creates on its own first start.

Allegro numbers gamepads in unsorted `/dev/input` order. On the Mini V2 that
made the newest seat, `Korri Seat P4`, gamepad 0, so an index-based scheme
ignored the device's controls. `gamepad-input.patch` adds `joystick_name`: the
player looks the name up in Allegro's current gamepad list on every input read.
Adding, removing or reordering gamepads does not change the selection. While
the named gamepad is absent the player reads no gamepad, not another one. The
in-game controls dialog stores the name of the gamepad it selects.

The same patch lets any D-pad hat move the hero, in addition to the scheme's
movement stick or buttons. Korri's seats report the D-pad as a hat
(`ABS_HAT0X`/`ABS_HAT0Y`), which Allegro exposes as a digital stick. Upstream
reads only one configured stick for movement, so the D-pad did nothing while
the left stick moved the hero.

Korri's seats report a wired Xbox 360 pad. In Linux's button order,
upstream's defaults put Start on the left-stick click (button 10) and Extra2 on
Start (button 8), so the launcher swaps them.

`nix build .#checks.x86_64-linux.zquest-gamepad-vm` drives the packaged player
with four virtual seats in a VM. P1 is deliberately not Allegro's first
gamepad. It checks that P1's D-pad and left stick move the hero, that other
gamepads do not, and that the selection survives a gamepad added during play
and P1 disconnecting and reconnecting.

The system menu is the player's only in-game route to settings and to ending
the game. Korri stops the session instead. The Escape key still opens the menu,
because upstream hard-codes it; this matters only with a keyboard attached. A
quest-specific scheme that names `Default` also keeps the menu button.

Existing `/storage/saves/zquest-classic` data remains untouched. There is no
fallback read, dual write, or automatic migration from legacy.

Keep companion music files beside the quest as its author specifies. Archives
must be unpacked before discovery. Do not modify a quest while it is running.
Normal signature and permission checks remain required.

## Build and verify

Run from this repository on a build machine:

```sh
nix build --no-link .#packages.x86_64-linux.korri-plugin-zquest-classic
nix build --no-link .#packages.aarch64-linux.korri-plugin-zquest-classic
nix build --no-link .#checks.x86_64-linux.korri-zquest-classic-plugin
nix build --no-link .#checks.aarch64-linux.korri-zquest-classic-plugin
```

The checks exercise the real manifest, strict launch types, host admission,
and production sandboxed callback. They run the packaged player through Core
on Xvfb, using an original generated geometric room rather than an upstream
template or retail data. They exercise
keyboard input, native screenshots, in-game save writes, reload after a rename,
separate accounts, changed-release isolation, concurrent-session refusal, and
preservation of local files. Test accounts do not answer the upload question,
so a launcher regression stops the run at upstream's modal. The checks assert
the exact handheld-settings edits and that the player keeps them on exit.
They also assert upstream's `auto_scopes.zplay` against the pinned interpreter.
Only 26 graphics hashes differ from upstream for the replacement fonts.
All 100 non-graphics events, including script traces, RNG, controls and timing,
remain exact. Its Git LFS files are fetched by hash for tests only and are absent
from the plugin closure. The Tiny5 test checks deterministic generation, exact
fitting pixels, unchanged metrics and rejection of altered glyph/license inputs.
The native asset reader checks all 61 samples, 101 font slots/metrics, seven
silent MIDI tracks and two bitmaps. It exercises the real MIDI timer at each
default loop boundary. The original win-room variant exercises the ending,
acknowledgement, save write, backup and return to the quest.
A private PulseAudio null sink exercises real sound initialization without
hardware or an ALSA sequencer. These checks do not establish audible output,
physical-controller support, all-quest compatibility, or device acceptance.
The `public2` Tiny5 player checks passed on native x86_64 and aarch64 build
machines on 2026-10-16. The off-device validation record (personal repository record)
lists exact outputs, source archive hashes and acceptance limits.
The check-only GitHub workflow runs both architectures and publishes nothing.

For an interactive run with separate test state:

```sh
nix run .#zquest-classic -- /path/to/quest.qst /path/to/test-state
```

## Publication and installation

The output contains the reviewed and generated runtime resources described
above, plus license notices. It omits the editor and all bundled quests.
Upstream declares GPLv3 for the project. The public recipe selects
reviewed runtime resources before compilation and provides generated replacements. A successful build alone does not prove
asset rights. The publication gate checks the final resource inventory and
compares every generated file with its source derivation. The release process
also checks the exact runtime closure and corresponding-source archives.

### Corresponding source

```sh
nix build --no-link .#packages.x86_64-linux.zquest-classic-source
nix build --no-link .#packages.aarch64-linux.zquest-classic-source
```

These outputs contain architecture-specific source archives with the cleaned
engine, explicit CMake dependency sources, generator inputs/notices, and a
standalone Nix recipe. The exact Tiny5 glyph source and complete OFL notice
are included beside the generator and in the original recipe directory.
The runtime font notice retains Tiny5 and ProggyVector terms. These inputs
must regenerate byte-identical resources with the pinned toolchain.
The archives exclude upstream quest/media collections and unneeded dependency
demo/test media. `BUILDING.txt` explains rebuilding from
the extracted source. Source archives and exact `revision.txt`/architecture
path lists accompany the binary release. The original integration recipes are
also in this repository at that revision.

### Signed cache publication

The personal repository's release records (public1, public2) describe the
earlier `@simonwjackson` outputs; they do not cover this `@korri` output.
Publish `korri-plugin-zquest-classic` through this repository's standard
`Publish Nix cache` workflow (see `PUBLICATION.md`). Upload the matching
corresponding-source archives for both architectures as release assets of
this repository before publishing the binary batch, and keep clear directions
to them next to the binaries.

Publisher binding is separate from publication. Signature and exact-package
approval checks stay in force.

## Device installation

Signed publication and device installation require their existing approvals.
Do not build on a device or bypass publisher trust to install this package.
After publishing the architecture-specific output through the approved signed
cache, use Core's existing exact-package approval flow:

```sh
sudo korri-plugin inspect "$CACHE_URL" "$PACKAGE"
# Review the report, then set APPROVAL to its exact digest.
sudo korri-plugin install "$CACHE_URL" "$PACKAGE" "$APPROVAL"
sudo korri-plugin enable @korri:zquest-classic
```

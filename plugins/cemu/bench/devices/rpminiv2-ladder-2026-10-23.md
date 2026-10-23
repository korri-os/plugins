# Mini V2 BotW ladder — 2026-10-23 UTC

**Checkpoint, paused for an unowned game session. Native-aspect baseline:
25 / 24 / 22 FPS (median / p10 / p1), peak 87.2 °C. The target is not met.
The remaining ladder and 15-minute soak have not run.**

At 06:17:58 UTC, after the baseline stopped, another BotW session appeared:
`korri-game-36656694d99744650abe6bc6acb66322.service`, Cemu PID `31953`.
It is not owned by this bench. The supervisor confirmed that no worker started
it and is checking with the owner. Bench stopped work on the device. It did
**not** stop that session, restore files underneath it, or restart any service.
The read-only pause audit still reports `Volume: 0.00 [MUTED]`.

## Source, build and installation

Branch `feat/cemu-mini`, initially `ebbed6a` from `feat/cemu-odin`.

| Commit | Shipped change |
|---|---|
| `492bd65` | Native seed `Graphic/AsyncCompile=false`, only when settings.xml is absent. Package/runtime checks require the seed and preserve an existing person's `true` edit. Temporary workaround for the `draw_execute` / null `activeVertexDS` race; synchronous compilation can hitch. |
| `4bb37ae` | Optional CC0-1.0 BotW 31:27 aspect and five matching resolutions. Mirrors Github989's 4:3/5:4 pattern, retains original 1280×720 game texture dimensions, exposes Square HUD Mode, changes no pack or plugin selection default. Package check covers choices, conditions and unchanged defaults. |

Cemu remains `29f2f1fae4631e2317977debd9eacd55cc28dd7d`. The aarch64-only
Turnip 25.3.2 pin remains intact. No emulator source patch, affinity feature,
per-device profile or new Korri configuration schema was added.

Builds ran on yari and zao, never on a handheld. The production namespace was
built and checked, not installed. The existing approved personal-publisher
composition substitutes only `@korri:` → `@<publisher>:` in plugin.ts and uses
Core's normal mkPlugin builder. No manifest was rewritten.

| Artifact | Exact path |
|---|---|
| Initial async-off Cemu | `/nix/store/ji6qlqds68657i06l2aviwlkvwd6fj5s-cemu-0-unstable-2026-10-22-29f2f1f` |
| Initial personal plugin | `/nix/store/bri95bsd0634xiz30yvhizb1iadrdl23-korri-plugin` |
| Native-aspect Cemu | `/nix/store/lwh1bkqvr2agjs4h6asb32dhg1bamida-cemu-0-unstable-2026-10-22-29f2f1f` |
| Current personal plugin | `/nix/store/avjc0gvac9b49cc4bapgl23yva0bmbrk-korri-plugin` |
| Native-aspect production plugin, built only | `/nix/store/lg7aw924dyx9i1xj202b8ajr6g9grdl6-korri-plugin` |
| Bench | `/nix/store/ycx1s593595i2c2hyax3l5i58d6iqcw8-korri-cemu-bench-0.1.0` |

Zao signed transport closures with the existing cache key and private-cache
metadata with the existing personal publisher key. No key was printed or
copied. Signed `nix copy`, then normal `korri-plugin inspect`, exact-approval
`install`/`update`, and `enable` passed. Current exact approval:
`c07d4687477d8fbdb1785a12301d79a860dabf30809f30346a9981b7e40a12c1`.

The Mini's actual pre-existing binding uses
`file://<plugin-cache>`, not Odin's cache path.
Both that private cache and the `@<publisher>` binding already existed.
Publisher configuration SHA-256 remains
`996cf8dafc4800f0f22d40a2c58a1f44f2825b50c02ac8eb68396c02c0871d33`.
Signature checks remain required; target builders are empty, max-jobs is zero,
and fallback is false. Nothing was pushed, merged, published or deployed as a
system update.

## Device as found

The supplied generation-29 inventory was no longer current at first contact.
The supervisor authorized testing generation 30 as found. Its installation and
04:33:28 reboot preceded this run and came from a separate session; the
supervisor reports that it is not from Core origin/main. These results therefore
qualify only the exact system below, not an assumed main build.

| Fact | Verified value |
|---|---|
| USB-only route | `root@<device-usb-ip>:2222` |
| System generation | 30 |
| Current and system-profile target | `/nix/store/861m162v29s7cj9dcsfmdr7ldgh5qgfz-nixos-system-rpminiv2-sd-card-26.11.20260923.4975466` |
| Bundle | `/nix/store/c6n0dpw4dn4rm65dp6jbvwdw20kay4qd-korri-bundle-0.0.0` |
| Boot ID | `d3e5cc22-ca07-47e7-8766-3151c22ad060` |
| Running korrid | `/nix/store/44f51pv8m97037rl8ip7anmanv1zykck-korrid-0.0.0/bin/korrid` |
| Cemu GPU / driver | Turnip Adreno 650 / Mesa 25.3.2 |
| Initial free root bytes | 11,808,706,560 |
| Speaker | `Volume: 0.00 [MUTED]` |

Every native bench report records the exact system, bundle and boot ID.
The guard checks identity, foreign game units, mute and all readable thermal
zones. It stops its exact bench on a critical trip or 31 complete measurement
seconds below 15 FPS. No boot, system or bundle change occurred during bench.
No GC, game deletion, staged-save deletion, trust change, firmware/partition
write or other USB-device operation occurred.

## Catalog and same-save preparation

Normal plugin admission declared Wii U. With no live game, both
`korrid-control.socket` and `korrid.service` were stopped for the documented
`korrid catalog pair /var/lib/korri/games/wiiu wiiu` command, then started
normally. Pairing added one game, hashed 13,660,330,872 bytes and reported zero
diagnostics. No recovery journal edit or unit reset occurred.

WUA SHA-256 matched:
`064e512446009a42e6de6399b6665c96abe820be039cb3b5a968e40591d8c9ff`.
All 54 staged save files matched `botw-save.sha256`. They were copied beneath
the actual account's declared `saveRoot/mlc01/usr/save/00050000/101c9400`.
The existing account's private `.config` is writable by `korri`, not `korrid`;
Cemu's new native config directory was created as `korri`. No unrelated account
permissions were broadened.

The first launch was refused with `SavesSplit`. The Mini already held synced
Odin BotW history with heads `43947273…` and `c11f33a0…`. With supervisor
approval, supported `app.saves.restore` selected
`sha256:80c5f05621c3f48a86622995eb65ea8cd390b80fb36b64d7fe85a18c932f5ae0`:
its 54 file hashes exactly match the staged save. History was retained, never
hand-edited. A later arriving peer head (`e7f6f30c…`) caused another refusal
before the first native-aspect launch. Another supported restore merged the
visible continuation heads. This is observed save-sync split behavior, not an
emulator crash. The helper now checks save status after a bounded restore.

Every measured comparison restores that exact staged snapshot. P2 injection
uses the existing bench pad and Cemu-generated native controller XML from the
Odin campaign. A live Mini SDL3 enumeration confirmed the same P1/P2 GUIDs.
The native baseline's **actual Cemu process** opened and read slot
`user/80000001/3/game_data.sav`, observed through fanotify **after** launch-time
materialization. This avoids the earlier pre-launch-inode-watch limitation.
No movement follows loading. The location is not visually identified; it must
not be called a verified shrine or Zora's Domain scene. No manual save attempt
was made.

## Native aspect and output

The owner superseded the 16:9 workload while `baseline-03` was running. That
exact bench was interrupted normally. All subsequent game testing uses the
owner's **31:27** choice in native account settings, not a Korri setting.

The previously seeded account pack was explicitly upgraded by hash-guarded
replacement of its Graphics/rules.txt with the newly packaged file. Its original
bytes remain in private evidence. The wrapper still never silently overwrites an
existing person's pack tree.

Baseline native selections:

- Aspect Ratio: `31:27 (1240x1080 handheld)`.
- Resolution: `1028x896` (921,088 pixels, versus 921,600 at 1280×720).
- Square HUD Mode: `Enabled (Experimental, Will Have Some Issues)`, the native
  option exposed by the upstream near-square pattern.
- FPS++: `30FPS Limit`, plus retained advanced `30FPS (ideal for 240/120/60Hz displays)`;
  log confirms the active limit is **30**, not the old normal 45 preset.
- `GX2DrawdoneSync=false`, `vkAccurateBarriers=false`, `VSync=0`,
  `AsyncCompile=false`; multi-core recompiler.
- Native Cemu `Graphic/FullscreenScaling=1` (`kStretch`, CemuConfig.h), so the
  rounded near-31:27 low resolutions fill the owner's exact 1240×1080 output.
  This is an account choice, not a changed shipped default.

Actual Gamescope arguments include:

```text
--backend wayland --fullscreen --expose-wayland
--output-width 1240 --output-height 1080 -- <Cemu runner and literal game argv>
```

The captured chain is korrid plugin-launch → Gamescope → gamescopereaper →
Cemu. Bubblewrap was not observed. Actual Cemu mappings use the pinned
25.3.2 freedreno library; Gamescope keeps system Mesa. No global ICD or TU_DEBUG
setting was added.

**Numeric aspect proof, not a visual review:** screenshots were never opened
with an image viewer or the read tool. Pillow computed luminance only. At
native baseline `screen-160.png`, dimensions are 1240×1080; contiguous edge
rows/columns with mean luminance ≤1/255 are **0 / 0 / 0 / 0**
(top / bottom / left / right). The first sampled edge means are
94.24 / 87.07 / 100.65 / 86.60 on that 0–255 scale. The 16:9 reference instead
has **191 / 192** black top/bottom rows. This proves no captured broad
letterboxing at native aspect. It does **not** prove that HUD text, menus,
spacing or clipping look right. The Square HUD option itself warns that it is
experimental. Owner visual acceptance remains required.

## Ladder checkpoint

Each completed rung has 100 seconds warmup **after** the input script and 180
measurement seconds. Native tests wait 30 seconds before replaying the same
40-second load script. FPS values are nearest-rank one-second X Present bins,
not compositor Hz or reciprocal frame-time percentiles. Temperatures include
warmup. `—` means no qualified completed sample, never zero FPS.

Screenshot paths below are relative to
`/var/lib/korri/cemu-bench-staging/mini-ladder-20261023/` on the Mini.

| Rung | Setting | Aspect / internal resolution | Median | p10 | p1 | Peak °C | Kept / reverted | Screenshot |
|---|---|---|---:|---:|---:|---:|---|---|
| Reference `baseline-02` | May settings, async off, FPS++ 30; save read not independently traced in this run | 16:9 / 1280×720 | 30 | 30 | 30 | 70.5 | Reference only; superseded by owner's aspect requirement | `baseline-02/screen-160.png` |
| 1 `native-baseline` | May settings, async off, FPS++ 30, Square HUD, fill scaling, device-default clocks | 31:27 / 1028×896 | **25** | **24** | **22** | **87.2** | Current measured baseline; below target | `native-baseline/screen-160.png` |
| 2 clocks | Game `cpu.min=100`, `gpu.min=100` | 31:27 / 1028×896 | — | — | — | — | RPC minima set; no sample yet | — |
| 2 governor | Device-only governor comparison | 31:27 / best measured resolution | — | — | — | — | Not run | — |
| 3 resolution | 827×720, then 620×540, then 413×360 | 31:27 | — | — | — | — | Not run | — |
| 3 upscaling | Existing Gamescope nested size / FSR settings | 31:27 | — | — | — | — | Not run | — |
| 4 shadows | Native Graphics pack shadow preset | 31:27 | — | — | — | — | Not run | — |
| 4 ambient occlusion | No AO choice found in the bundled BotW rules | 31:27 | — | — | — | — | Unavailable; no shader patch invented | — |
| 4 anti-aliasing | Native Graphics pack AA preset | 31:27 | — | — | — | — | Not run | — |
| 4 LOD / draw distance | Native Draw Distance pack choices, separately | 31:27 | — | — | — | — | Not run | — |
| 5 CPU options | Native game profile mode / quantum | 31:27 | — | — | — | — | Not run | — |
| 5 barrier skip | Already covered by `vkAccurateBarriers=false` at this Cemu pin | 31:27 | — | — | — | — | No additional independent setting found | — |
| 6 big cores | Test-only exact-Cemu taskset to cores 4–7 | 31:27 | — | — | — | — | Not run; no affinity schema added | — |
| 7 Turnip flags | TU_DEBUG unset | 31:27 | — | — | — | — | No artifact-fix flag justified or tested | — |
| 8 further patches | Emulator / game patches after earlier rungs | 31:27 | — | — | — | — | Not reached | — |

The native baseline minimum was **12 FPS in one bin**, not sustained collapse.
The median misses the target by 5 FPS; p10 misses by 3 FPS. That needs 20% / 12.5%
uplift respectively from the measured baseline. No 15-minute soak has run.

Other attempts: `baseline` and `native-baseline-refused` failed before Cemu
started because of the save split. Their zero placeholders are not FPS results.
`baseline-03` confirmed slot-3 save reads but was deliberately interrupted at
114 seconds when the native-aspect requirement arrived; it has no complete
180-second result.

## Pause state, governor correction and remaining restoration

Rung-2 setup successfully set the two game-layer minimums. It then attempted
an unnecessary Game-layer governor unset and received:
`SettingsInvalid: invalid setting: CPU governor belongs only to device`.
No governor value was changed. The **private, one-off** helper was corrected on
zao: governor writes use `scope: Device` and `revisions.device`; minimum writes
use `scope: Game` and `revisions.games`. These are existing treaty fields,
not a new configuration schema. The correction has not been exercised against
the live device while the unowned game runs. The helper remains under
`/tmp/cemu-mini-evidence/`, not in the product.

As the supervisor required, `cpu.min=100` / `gpu.min=100` remain for the person
currently playing. The helper had restored the temporary item modifier before
those RPC writes; the device's original global Gamescope modifier still wraps
the owner's game. The partial setup's library SHA-256 is
`dfac57c322a33d0dbb4ae318f0117f653f9e6fc2cc58742846681125348bd9c0`.
It must be reviewed under the hash guard before any later restoration, so an
owner edit cannot be overwritten.

Completed bench cleanup records prove empty exact cgroups, no new surviving
bench/game wrapper processes, restored P1 bytes/metadata, and removal of the
bench pad. The later unowned game is deliberately **not** included in a claim
that the whole device is idle. Speaker guard samples and the pause audit all
show muted volume; this worker never unmuted it.

Final restoration is **pending**, not claimed complete. On an authorized
continuation, restore launch limits to device defaults, exact original BotW
item bytes, P1, and remove every experiment-only process/change. The supervisor
clarified the final account exception: retain the owner's 31:27 choice, intended
Square HUD choice, and the best measured native-aspect resolution/FPS++ choices
in Cemu's own settings; use shipped defaults otherwise. The shipped pack remains
16:9 by default for every other account/device. Record the final exact native
settings and restoration proof when that step is actually done.

## Focused checks and private evidence

Passed for the final native-aspect package on both architectures:

```sh
nix build --no-link .#checks.aarch64-linux.korri-cemu-package \
  .#checks.aarch64-linux.korri-cemu-admission --max-jobs 0 \
  --builders 'ssh-ng://<builder-login> aarch64-linux /etc/ssh/ssh_host_ed25519_key 2 1 big-parallel,benchmark - -'
nix build --no-link .#checks.x86_64-linux.korri-cemu-package \
  .#checks.x86_64-linux.korri-cemu-admission --builders '' --max-jobs 1
```

These include strict TypeScript/callback tests, installed-wrapper ShellCheck,
Turnip selection, native aspect/default checks, real Cemu CLI/Xvfb startup,
offline pack loading, native edit preservation and Core admission/execution.
The async-off runtime check first failed against the previous seed; the new
aspect check first failed against the unpatched package. Both then passed.
The initial red Nix runtime attempt also had an unrelated 15-second help
startup timeout; a direct real help probe and subsequent complete checks passed.
Outside-sandbox `--setgid-account` runtime passed for the async-off build.

Also passed: 12 focused bench unit tests; mypy on its 9 Python files; Ruff check
and format check; mypy/Ruff on the new pack check; Python compilation; final
`git diff --check`; commit-hook secret scans. Bare mypy was absent from PATH,
so its existing exact Nix-store executable was used. No full repository suite
or full verification ran.

Private zao evidence: `/tmp/cemu-mini-evidence/` (0700). Device evidence:
`/var/lib/korri/cemu-bench-staging/mini-ladder-20261023/`.
Important files: `campaign-retry.log`, `native-baseline-edge-stats.json`,
`aspect-{arm,x86,final-arm,final-x86,inspection,install,setup}*`,
`preflight.json`, `content.sha256`, `foreign-session-readonly.txt`, and the
native baseline's raw Present/telemetry, cleanup, profile and save-access files.
Screenshots and save contents are not committed. No image file was viewed.

| Acceptance | Checkpoint result |
|---|---|
| Median ≥30; p10 ≥27 at 31:27 | **Not met**, 25 / 24 |
| 15-minute soak holds target, no crash, peak recorded | **Not run** |
| Complete measured ladder table | **Incomplete**, paused after rung 1 |
| Shipped behavior uses native files/existing settings only | **Passed** for the two source changes; no new Korri schema |
| Launch settings restored to device defaults | **Pending**, unowned session deliberately left alone |
| Native-aspect output without captured black bars | **Numeric proof passed** for the baseline screenshot |
| HUD and menus look correct | **Not established**; experimental native option selected, images unviewed |

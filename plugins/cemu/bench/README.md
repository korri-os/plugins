# Korri FPS bench

An administrative Linux tool. It launches **only through korrid**, using the
portal's authenticated localhost `/rpc` reserve/start/stop calls. The installed
runner, Gamescope modifier, bubblewrap policy, limits helper, saves and normal
session lifecycle remain korrid's responsibility. It never runs an emulator
command itself and never changes a system generation or sysfs value.

## Build and deliver (development host only)

```sh
# From this repository. ARM builder chosen explicitly; never run on a handheld.
nix build .#packages.aarch64-linux.korri-cemu-bench --no-link --print-out-paths \
  --max-jobs 0 --builders 'ssh-ng://<builder-login> aarch64-linux /etc/ssh/ssh_host_ed25519_key 1 1 big-parallel,benchmark - -'
# Set BENCH to the exact printed store path. Do not use a moving result symlink.
nix store sign --key-file ~/.config/korri/cache-key.secret --recursive "$BENCH"
nix path-info --sigs --recursive "$BENCH"
NIX_SSHOPTS='-p 2222 -o BatchMode=yes' nix copy --to ssh-ng://root@<device-usb-ip> "$BENCH"
```

The development builder automatically signs with `fuji-1`, **not** the devices'
trusted `korri-cache-fuji-1`. Zao's existing `korri-cache-zao-1` signs the closure
for this test delivery. Never copy/print its secret, change trust, disable
signature checks, or substitute a target build. The bench is a diagnostic tool,
not a plugin; it cannot install or enable Cemu. Native plugin installation must
still use `korri-plugin inspect`, `install`, and `enable` with normal approval.

## Usage on the device

Use root over the administrative SSH route. Run the already copied executable,
not `nix run`/`nix build` on a handheld. `$BENCH` below means that immutable store
path, present on this device. Obtain game and runner IDs from the existing
library/routes; the tool does not create records. The default capability file
is `/run/korri-portal-credentials/KORRID_RPC_CAPABILITY`. It is read privately,
never put in an argument, URL, report, or log. RPC is fixed to loopback.

All measured runs now require `--reference`. There is no ungated mode and no
`--input-delay`. Old WL4 samples below are historical proofs of the observer,
not runnable gameplay-qualified examples.

On Odin, set these variables from the installed library and the existing account.
Do not put the account path or RPC capability in a committed command file.

```sh
GAME=the-legend-of-zelda-breath-of-the-wild-usa-dlc-v208
RUNNER='@<publisher>:cemu/cemu'
# ACCOUNT_ROOT is the real existing user's folder, obtained from a real launch.
REF="$BENCH/share/cemu-bench/references/botw-1920x1080.json"
set -- --game "$GAME" --runner "$RUNNER" --process-name Cemu \
  --reference "$REF" --input-script "$BENCH/share/cemu-bench/botw-load.events" \
  --repeat-input-until-loading \
  --controller-profile "$ACCOUNT_ROOT/.config/Cemu/controllerProfiles/controller0.xml" \
  --controller-template "$STAGING/controller0-bench-p2.xml" \
  --cemu-log "$ACCOUNT_ROOT/.local/share/Cemu/log.txt"
"$BENCH/bin/korri-cemu-bench" run "$@" --output "$STAGING/run-01"
"$BENCH/bin/korri-cemu-bench" soak "$@" --minutes 15 --output "$STAGING/soak-01"
"$BENCH/bin/korri-cemu-bench" ab "$@" --a baseline=- --b repeat=- --output "$STAGING/ab-01"
"$BENCH/bin/korri-cemu-bench" save-proof "$@" \
  --save-root "$ACCOUNT_ROOT/saves/$GAME" --output "$STAGING/save-proof-01"
```

`--warmup` (default 100 s), `--seconds` (180 s) and `--minutes` (15) control
measurement, not game readiness. `--gate-timeout` (120 s, maximum 600) bounds each
state gate. `--gate-poll` defaults to one second. Use a new private (0700) output
directory each time. Keep the Speaker muted. Before **every** launch, the tool
refuses other sessions/units and Eden, Gamescope or Cemu processes. If another
person is playing, poll read-only at intervals of at least five minutes; never
stop their game.

## Gameplay gate and references

1. Capture the compositor with prebuilt `grim`, as `korri`, on the existing
   `korri-wayland` socket. Pixel decoding uses Pillow in memory. No image viewer
   is used. `frames.jsonl` retains only numeric descriptors and capture hashes.
2. Require two consecutive title matches. The title reference uses a sparse
   near-white foreground mask, not the changing background alone. It must also
   be closer to title descriptors than loading or gameplay descriptors.
3. Only then replay the native input script. For BotW, use
   `--repeat-input-until-loading`: repeat the native A pulse every two seconds,
   for at most 60 seconds, and stop sending presses as soon as loading matches.
   A title/intro image can appear before its menu accepts input. A single
   three-press burst is not sufficient. This is a bounded observed-state
   advance, not a fixed startup delay. Capture between scheduled events,
   including during the script. Require a reference-matching loading frame,
   followed by two consecutive reference-matching gameplay frames. Descriptors
   are 31×27 bicubic RGB; matching uses mean absolute channel difference on a
   0–255 scale, calibrated separately for loading and gameplay.
4. Check gameplay again before warmup, and at the end of the complete sample.
   Warmup cannot start on a title/loading/menu frame.
5. Any failure exits non-zero. `report.md` says **not measured**, names the
   reason and gate timings, and contains no performance table or FPS values.
   No `fps.json` is published. Raw Present events remain diagnostic only.

Each report records title/loading/gameplay offsets after launch starts, and the
end-of-sample check. A missing observation says `not observed`, never zero.
The committed numeric references cover BotW at a compositor output of 1920×1080
(16:9 Odin) and 1240×1080 (31:27 Mini). They represent the existing staged,
stationary gameplay, not a proof of a named shrine or Zora's Domain. They are
strict: another save/scene, aspect or output size can refuse a valid run.
Do not widen a threshold to make a failed run pass.

To capture a new reference on a device, first use a normal supported game
session with a complete save, and establish each state's meaning independently.
The capture command is read-only; it never launches a game or chooses a save:

```sh
"$BENCH/bin/korri-cemu-bench-reference" capture --output "$PRIVATE/title-a.png"
# Repeat for different title backgrounds, loading, and stationary gameplay.
# Do not display the PNGs or commit them. Copy them privately to the host.
"$HOST_BENCH/bin/korri-cemu-bench-reference" calibrate --game "$GAME" \
  --title "$PRIVATE/title-a.png" "$PRIVATE/title-b.png" \
  --loading "$PRIVATE/loading.png" \
  --gameplay "$PRIVATE/gameplay-a.png" "$PRIVATE/gameplay-b.png" \
  --output "$PRIVATE/reference.json"
```

Calibration refuses overlapping positive/negative descriptors or an insufficient
stable title foreground. It emits numeric references, original image SHA-256s,
calibrated boundaries, and `*-checks.json` recorded statistics for tests. Review
classification of additional title/loading/menu/gameplay captures before using a
new reference. Record game, aspect, output/internal resolution and real source
campaign in `references/README.md`. Internal resolution need not get another
reference if calibration proves the same output descriptor separates all states.
Only numeric data is committed. The tool never infers semantic scene identity
from a histogram. The raw game assets and save previews stay private.

## Save safety

Core `origin/main` was checked: ADR 0014, `SCRIPTING.md`, the generated
`SessionStartRequest`/`SavePickRequest`, and `host/saves.rs`/`saves/store.rs`.
There is no supported guest/test launch or snapshot opt-out. Sync explicitly
cannot be disabled for a runner that declares saves. The bench does **not** add
an account, skip-snapshot field, direct-launch path, or a private-store writer.

Before reserve/start, it calls `app.saves.check` and records `app.saves.history`'s
unambiguous current head. It refuses a split, a peer in use, a missing head, or
**any** missing, wrong-size or wrong-SHA-256 payload blob, including screenshots.
`Synced` alone is not proof. The read-only object layout comes directly from
Core's `NativeSaveStore::object_path`: `--save-objects` defaults to
`/var/lib/korrid/saves/objects`. It also preserves the original history and blobs
in a private `/tmp/korri-cemu-save-*` backup. Keep that backup until the run is
reviewed; never commit it. There is no automatic unsupported re-insertion of
missing objects.

After exact-session stop, including gate/input failures, it uses the supported
`app.saves.restore` to select that original payload again. It verifies every
blob, exact location/file content and ancestry. Restore **appends a new
continuation**; the original and final head IDs therefore differ. Both IDs and
the number of additional records/session snapshots plus restore records are in
`save-safety.json` and the report. New records can include peer arrivals; they
are not silently counted as exclusively local bench work. If cleanup cannot
prove idle, it refuses restoration and reports the deferred recovery. A
concurrent writer can still race the RPC (it has no expected-head field).

**Remaining risk / note for #212:** bench and restore snapshots still enter the
person's real history, sync, and count toward retention. Restoring content is
not history isolation and cannot fix #208. A supported guest account or
snapshot-free diagnostic session is a Core follow-up, not implemented here.
`app.saves.restore` changes the selected continuation; Core materializes it at
the next launch, not by the bench hand-copying the live save tree.

For additional read proof on the normal/soak run, pass `--save-root` with the
exact launch-declared directory and
`--require-save-read mlc01/usr/save/00050000/101c9400/user/80000001/3/game_data.sav`.
That relative path is the actual Mini/owner May source's slot 3, not an inferred
slot from menu order. `save-read.json` must contain its actual Cemu read and
SHA-256 before warmup. Use another real slot path for a different source.

## Optional in-game save proof

`save-proof` uses the same gates and protected original head. After gameplay it
sends Plus, ten R presses with 0.5-second gaps, A on Save, A to confirm, and waits
at most 30 seconds. It requires a changed `game_data.sav` SHA-256 **and** mtime
under the exact `saveRoot` from this launch declaration, then stable bytes.
It stops, relaunches through korrid, gates gameplay again, and requires the new
hash plus an actual Cemu read of that newly written file (fanotify installed
**after** materialization, before load input). Only then is the proof PASS.
Original content is selected again even on failure. Do not call survival of an
old unchanged file a new-save proof. Device validation is bounded to two route
attempts; a failure stays **unproven**, not a storage error claim.

A/B uses **existing** launch-settings profiles, not a new configuration language.
Use `NAME=profile-id`, or `NAME=-` for no profile. It selects through
`app.launch-settings.profile.select`, snapshots resolved settings, then restores
the original selection through the same revision-checked API. A concurrent
library edit stops the operation rather than overwriting it; an administrator
must then review the recorded selection and restore it if needed. A/B changes
no typed Cemu setting, CPU affinity or per-device emulator profile.

## Per-game input and loaded saves

`--input-script FILE` accepts native **evemu-play event text**, not a Korri
schema. Comments and `E: seconds hex-type hex-code decimal-value` lines are
accepted. The file must be monotonic, finite, at most one hour, and use only
standard gamepad buttons/axes within their Linux ranges. Keyboard and Guide
injection are refused. `wl4-title.events` presses/releases Start; it is a
validation input, not a BotW route.

The tool creates a distinct, **bench-only** synthetic Bluetooth-bus uinput
source named `Korri bench gamepad`, with phys `korri-cemu-bench/input0`.
Its metadata is BUS_BLUETOOTH (0005), vendor 045e, product 02d1, version 0114.
These are test metadata, not a claim about attached physical hardware.
InputPlumber 0.75.2 `src/input/manager.rs:1232–1267` admits virtual Bluetooth
sources; the installed native `60-xbox_one_gamepad.yaml` explicitly matches
045e:02d1 and enables `auto_manage`. The Bluetooth-specific native profile has
no numeric IDs and requires the Microsoft HID driver, so it is not the producer
used here. Never use or document this synthetic path as a product route.

The device is created **after** korrid starts the real game session. Normal USB
uinput probes were not admitted even inside a game; toggling manage-all did
not fix the virtual-device filter. The successful Bluetooth-bus route leaves
`ManageAllDevices` untouched. The bench no longer contains a management toggle.
The existing input stack routes the admitted source to **Korri Seat P2**. It does not
impersonate Korri Seat P1, grab a physical controller, remap a device or bypass
inputd. It refuses attached external/unknown pads before a scripted run. It releases all controls and destroys its uinput device on completion
or handled interruption. It also stops only its newly created, source-less
InputPlumber composite through the normal `Stop` method (the native profile is
persistent). `input-observer.json` verifies the original policy, CompositeDevice0
source ownership and P1 identity/state; `seat-events.json` proves P2 admission.
`input-replay.jsonl` records actual event write times.

RetroArch reserves P1 for a single-player game. **P2 admission is not proof that
Wario Land 4 or BotW reacted.** BotW must select P2 in a bench-only Cemu-native
controller profile in the test account. Supply `--controller-profile /actual/Cemu/controllerProfiles/controller0.xml`
and `--controller-template /actual/bench-p2.xml` together with `--cemu-log`.
Both files must already exist; the template must come from Cemu with P2 selected.
The tool treats their XML bytes as opaque native configuration. It snapshots the
original, atomically installs the template for the run, and restores exact bytes,
mode, ownership, mtime and xattrs after the exact session stops. Symlinks, invalid
XML, files over 1 MiB, and implicit profile creation are refused. If another writer
changes the active profile, the bench fails and keeps the original for manual
review rather than overwriting that edit.

Real Cemu-generated P2 profile loading, staged-save loading and gameplay are now
proved in the [Odin async-off report](devices/odin2portal-async-off-2026-10-23.md)
and [Mini V2 ladder](devices/rpminiv2-ladder-2026-10-23.md). See those reports for
exact builds, settings, save-read traces and measurement limits. This does not
prove a new manual in-game save. No Mini V2 configuration passed a soak, and a
Mini V2 owner-session save payload loss is under investigation. The exact owner
payload could not be restored; the report records the approved older fallback.

For BotW, use the same verified-complete current continuation for each comparison. The bench restores its original payload after every run. Record a native input script for the chosen
fixed spot and supply `--spot 'description of verified position'` and `--cemu-log`.
**A completed script or capped title-screen FPS is not gameplay proof.** Verify
actual save reads and gameplay frames before accepting a sample. The reusable bench now enforces all three frame gates; the Mini report records the private precursor. The scene's
shrine/Zora identity and visual HUD/menu correctness were not established.

Committed samples use consistent account, address and storage placeholders.
Raw private evidence stays outside Git. Run `python3 check_samples.py` here to
check privacy, all sample checksums and FPS reproduction from the retained
Present events. Checksums describe the redacted public copies.

## FPS source and limits

The C observer subscribes to **X11 Present CompleteNotify** for the exact
renderer PID's windows in the game unit's private Xwayland. It joins the game's
mount namespace and drops to its UID/GID for X authentication. It translates the
host PID to the service's `PrivatePIDs` namespace. `_NET_WM_PID` or server-owned
XRes client identity excludes other clients. No process injection,
preload, emulator setting or global MangoHud queue is needed.

Only Pixmap completions count. `Skip` is excluded. One dominant game window is
selected during warmup, and only that window contributes measurement frames.
Bins use the server's monotonic UST timestamp, not observer wakeup time.
The report gives median, nearest-rank p10/p1, and minimum of **one-second FPS
bins**, including zero bins. These are not reciprocal per-frame percentiles.

This counts the game's presentations **to Gamescope**, not the compositor's
repeated output refreshes. Gamescope 3.16.18 `--stats-path` instead counts
`paint_all` every 300 paints (`src/steamcompmgr.cpp`), so it can count redraws
that are not new game frames. MangoApp's global SysV queue also risks stale
cross-run data. Neither is used.

Cost: the observer adds small X event traffic and one-second telemetry reads.
It proves neither panel scanout nor emulated simulation speed. Native Wayland,
a missing X Present extension, no completions, or a renderer/window replacement
can make a run fail. It never silently reports compositor Hz as game FPS.
Cemu's X11/Vulkan gameplay path is verified in the [gated Odin proof](devices/odin2portal-gameplay-gate-2026-10-23.md). Native Wayland still needs another observer.

## Output and cleanup

Successful runs have `report.md`, raw `present.csv`, `fps.json`, one-second CPU kHz/GPU
Hz/all-zone temperature `telemetry.jsonl`, launch limits `settings.json`, actual
`processes.json`/`unit.txt`, and exact-stop proof `cleanup.json`. Missing thermal
reads are null, never zero. When `--cemu-log` is supplied, a stale/missing log or
missing Vulkan/driver/CPU-mode evidence fails the run; matching lines are copied
into the report and the complete log is retained.

Failed runs have `report.md` and available diagnostics, but no `fps.json` or FPS table. An existing active/pending session is refused. A retained `HostLaunchFailed`
from a previous terminal game is accepted only after systemd and the actual game
cgroups conclusively show no game activity; unknown native state still fails. All stop/cancel operations name
**only this bench's launch ID**. No global kill is used. Cleanup records an empty
exact cgroup, no newly surviving game/Cemu/Gamescope processes, and unchanged
boot/system identity. After an exact stop returns `HostRecoveryBlocked`, the tool records the original
warning and polls read-only status for up to 10 seconds plus bounded I/O. It
accepts cleanup only after korrid leaves that state and systemd (including
acquisition units) plus every games-slice cgroup prove idle. It never resets a
unit, edits a recovery journal or restarts korrid. A persistent block or uncertain
native state fails the run. Other RPC/cleanup failures also fail the report
rather than claiming success. See `devices/odin2portal-stop-143.md`. SIGKILL or loss of access can still require an administrator
to stop the recorded exact session. Normal play logs and save-history entries still occur; the original verified save payload is selected again through supported RPC.

The observed chain is recorded on every run. **Core at `4e34b8a9e` does not implement ADR 0015.** Both updated images
can therefore show Gamescope but no bubblewrap. This is not an old-image-only
problem and is **not ADR 0015 acceptance**. The bench records observed processes;
it does not implement the missing core wrapper.

## Focused checks

```sh
cd plugins/cemu/bench
python3 -m unittest -v
mypy --check-untyped-defs *.py
ruff check *.py
ruff format --check *.py
# From repo root; keep this native check on the local host.
nix build .#packages.x86_64-linux.korri-cemu-bench --no-link --builders '' --max-jobs 1
```

The Nix build compiles C with `-Wall -Wextra -Werror`, runs the Python tests,
and exercises the real observer against an Xvfb Present producer that omits
`_NET_WM_PID` (proving XRes selection). Hardware sample reports live in `samples/`.

## Gameplay-gated delivery — 2026-10-23

`/nix/store/092bcnlgn7w4vbbp5cknp30j72cv2h32-korri-cemu-bench-0.1.0`
was built on yari, signed on zao and copied to Odin. The [device report](devices/odin2portal-gameplay-gate-2026-10-23.md)
and [public samples](samples/odin2portal-gameplay-gate/README.md) prove a complete
37/37/36 gameplay run, a no-input refusal with no FPS, and exact original-payload
selection/completeness afterwards. Two manual-save attempts remain unproven.
History isolation is still a Core gap; the campaign created 14 history records.
No Mini validation, patched-driver install or soak is included in this phase.
The device report gives exact async-off/on/soak phase-2 commands.

## Historical delivery — 2026-10-22

Final aarch64 build on fuji, signed on zao and copied to both devices:
`/nix/store/ycx1s593595i2c2hyax3l5i58d6iqcw8-korri-cemu-bench-0.1.0`.
It passed real 15-second lifecycle smoke runs on both updated devices.
The [hardware samples](samples/README.md) retain the separate default-duration
reports, exact provenance, raw FPS/telemetry, A/B/soak smoke results, visible
Odin P2 game response, cleanup audits, limitations and operational deviations.
Copying a closure does not install it into a profile; a later GC can remove it.
No permanent profile or system package was changed for this delivery.

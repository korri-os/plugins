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

| Mode | One command |
|---|---|
| Normal: 100 s warmup + 180 s measurement | `"$BENCH/bin/korri-cemu-bench" run --game wl4 --runner @korri:mgba/mgba --process-name retroarch --input-script "$BENCH/share/cemu-bench/wl4-title.events" --output /var/lib/korri/cemu-bench-staging/run-01` |
| Soak: 100 s warmup + N minutes (default 15) | `"$BENCH/bin/korri-cemu-bench" soak --minutes 15 --game wl4 --runner @korri:mgba/mgba --process-name retroarch --output /var/lib/korri/cemu-bench-staging/soak-01` |
| Two named variants, back-to-back | `"$BENCH/bin/korri-cemu-bench" ab --a baseline=- --b repeat=- --game wl4 --runner @korri:mgba/mgba --process-name retroarch --output /var/lib/korri/cemu-bench-staging/ab-01` |

`--warmup`, `--seconds`, `--input-delay` and `--minutes` control time. Warmup
starts **after** the input script finishes. Scripts start after the default
five-second launch delay. There is no hidden pause counted as measurement.
Use a new output directory per run. Directories are private (0700).

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
review rather than overwriting that edit. Real Cemu profile loading and visible
BotW navigation remain unverified until the plugin and saveRoot exist; no Cemu
field, profile format or default controller layout is invented here.

For BotW, first load the staged in-game save through Cemu's eventual declared
saveRoot. Record a native input script that reaches the chosen fixed spot and
supply `--spot 'description of verified position' --cemu-log /actual/Cemu/log.txt`.
Restore the same save before each comparison. **A script running successfully is
not proof that the scene is correct.** The supplied save preview shows Link in a
shrine, but no BotW input route or actual save load has been verified while the
Cemu plugin is unfinished. No final save layout or speculative BotW sequence is
shipped. Save hashes and exact staging paths are in `devices/`.

## FPS source and limits

The C observer subscribes to **X11 Present CompleteNotify** for the exact
renderer PID's windows in the game unit's private Xwayland. It joins the game's
mount namespace and drops to its UID/GID for X authentication. It translates the
host PID to the service's `PrivatePIDs` namespace. `_NET_WM_PID` or server-owned
XRes client identity excludes other clients. No screenshots, process injection,
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
Cemu's X11/Vulkan path still needs validation after its plugin is installed.

## Output and cleanup

Each run has `report.md`, raw `present.csv`, `fps.json`, one-second CPU kHz/GPU
Hz/all-zone temperature `telemetry.jsonl`, launch limits `settings.json`, actual
`processes.json`/`unit.txt`, and exact-stop proof `cleanup.json`. Missing thermal
reads are null, never zero. When `--cemu-log` is supplied, a stale/missing log or
missing Vulkan/driver/CPU-mode evidence fails the run; matching lines are copied
into the report and the complete log is retained.

An existing active/pending session is refused. A retained `HostLaunchFailed`
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
to stop the recorded exact session. Normal Korri play logs and game-save effects
still occur; this is not a snapshot/rollback of the game's own progress.

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

## Verified delivery

Final aarch64 build on fuji, signed on zao and copied to both devices:
`/nix/store/ycx1s593595i2c2hyax3l5i58d6iqcw8-korri-cemu-bench-0.1.0`.
It passed real 15-second lifecycle smoke runs on both updated devices.
The [hardware samples](samples/README.md) retain the separate default-duration
reports, exact provenance, raw FPS/telemetry, A/B/soak smoke results, visible
Odin P2 game response, cleanup audits, limitations and operational deviations.
Copying a closure does not install it into a profile; a later GC can remove it.
No permanent profile or system package was changed for this delivery.

# Eden bench

Latest Odin evidence: [approved resume-platform result](samples/odin2portal-acceptance/report.md).
NCE and Dynarmic each pass median/p10 60/60 FPS for 180 seconds; the NCE
900-second soak passes at 60/60/59 median/p10/p1. Settings and permanent Seat P1
controls are restored. Bench input temporarily mapped guest P1 to Seat P2.

**Bonneton resume platform, camera turned to face the Odyssey; not the open town
area; FPS may be optimistic versus open-area play.** This is not open-town
performance or audible-audio acceptance. Audio is graph-only at unchanged
0.50 and muted. Backend execution remains inferred. Mini later ran out of memory within 5,559 MiB, with no accepted FPS; its
temporary INI restore is unverified until physical reset and hash check.
`bubblewrap: absent — core gap #184`.

The preparation-stage/device-proof statements below are historical, not current
authorization or results. See the latest report and STATUS.md before device work.


Collector **0.2.2** accepts a native-default backend only when this run's fresh
effective `Cpu.cpu_backend` log names it. Eden rewrites the NCE default flag by
value, even after an explicit choice. No architecture default is guessed;
refusal and runtime-mapping checks remain mandatory and the result remains
inferred. Version 0.2.1's device reports below remain historical evidence.

Historical preparation checkpoint: build-host-tested collector, not then an
accepted SMO benchmark. See
[STATUS.md](STATUS.md), [verification and build path](VERIFICATION.md), and
[device facts](device-facts/). Both devices have verified USB SSH routes.
The user supplied keys and authorized content staging plus a trivial non-Eden
launch. Eden installation and SMO launches remain the next stage. Check each
device for the other workflow before every device step; an idle check is not a lease.

## Historical device proof boundary

On Odin, the tool proved real session reserve, start, exact stop and an empty
exact-session cgroup. **Device FPS measurement is not yet proven.** The only
admitted test game (`wl4`) ran with an empty modifier list, without Gamescope,
so the collector refused to measure a different pipeline. Its stop RPC also
reported `HostRecoveryBlocked`; no owned process remained. A later read-only
status returned `SessionCompleted`, not a continuing recovery refusal.

See the [preserved device report](samples/odin2portal-v021/report.md) and
[read-only findings](samples/odin2portal-v021/findings.md). No wl4 setting was
changed. FPS proof moves to the Odin stage, where SMO's own game-layer launch
settings are in scope. Mini remains untouched; its content staging moves to
the Mini stage after Cemu finishes. This is not a passed SMO benchmark.

## Nix app and cross-build

From the repository root on a build host:

```sh
nix run .#eden-bench -- --help
# Run the collector with the arguments described below:
# Set these to real local-library identities and a fresh Eden log/output path.
: "${GAME:?}" "${RUNNER:?}" "${FRESH_EDEN_LOG:?}" "${OUTPUT:?}"
nix run .#eden-bench -- run --game "$GAME" --runner "$RUNNER" \
  --process-name eden --eden-log "$FRESH_EDEN_LOG" --output "$OUTPUT"
# Build prebuilt ARM delivery artifacts on the daemon's configured builders:
nix build .#packages.aarch64-linux.eden-bench \
  --no-link --print-out-paths --max-jobs 0 -L
```

The app uses the repository's locked publisher Nixpkgs, Python and evdev. The
same package is exposed as `checks.<system>.korri-eden-bench`; its build runs
Python tests, Ruff, mypy, C warnings-as-errors and the two-window Xvfb Present
integration. Do not compile it on a target device or override the daemon's
configured ARM builders with a retired hostname. Sign and copy the exact
printed ARM store path by the route below.

The bench is an administrator's tool, not a plugin or a signature bypass.
Eden installation still uses normal `korri-plugin inspect`, `install`, `enable`.

## Approved signing and delivery route

The automatic builder signature is `<builder-1>-1`, not the devices' trusted
`korri-cache-<builder-1>-1`. Use <build-host>'s **existing**
`~/.config/korri/cache-key.secret`, named `korri-cache-<build-host>-1`, to sign the
closure locally. Both devices trust that public key. This route already served
the Cemu workflow; no new device trust or system change is needed.

Use the exact tested output for the target architecture as `BENCH`; see
VERIFICATION.md for the delivered path. Do not print/copy the secret, change
trusted keys, use `--no-check-sigs`, or dispatch a build from a handheld.

```sh
# On <build-host>. Set BENCH to the exact tested store path, not a moving result link.
set -e
: "${BENCH:?Set the exact tested bench store path}"
nix store sign --key-file "$HOME/.config/korri/cache-key.secret" --recursive "$BENCH"
nix path-info --sigs --recursive "$BENCH"
# Verify korri-cache-<build-host>-1 signatures before copying.
DEVICE=10.42.4.1 # Odin; Mini's verified USB address is 10.42.3.1.
ssh -o BatchMode=yes -p 2222 root@"$DEVICE" bash -s <<'SH'
if pgrep -a -f 'cemu|eden|bench'; then
  echo 'Device busy: wait for the other workflow, then recheck.'
  exit 75
fi
SH
NIX_SSHOPTS='-p 2222 -o BatchMode=yes' nix copy --to "ssh-ng://root@$DEVICE" "$BENCH"
```

The stdin script avoids matching the SSH shell's own command line with the
process check. Wait if any emulator or bench appears; do not stop another
worker's process. Repeat the check before each later device step. This tool's
Nix signing is not plugin-publisher authorization: Eden still needs normal
inspection, installation approval and enablement. Do not install Eden or launch
SMO in this preparation stage.

## Existing contracts, no new settings

Core source authority: `contracts/generated/korrid.ts` and portal
`clients/portal/src/korrid/client.ts`, read from the supplied Core worktree.
The collector calls the existing localhost `/rpc` with the boot capability:

1. Refuse active, pending or observation-failed sessions, and known running
   emulators (Eden, Cemu, Ryujinx, RetroArch).
2. `app.session.reserve {gameId}`.
3. `app.session.start {gameId, runnerId, expectedLaunchId}`.
4. Observe the exact `korri-game-<launchId>.service` cgroup. Require actual
   Gamescope and the renderer's own Xwayland connection. Record bubblewrap's
   presence/absence; do not fabricate the missing Core wrapper.
5. Stop/cancel only the reserved identity. Never use a global kill. Wait for
   the exact cgroup to empty and record new emulator/wrapper leftovers.

The tool neither constructs an emulator argv nor changes launch profiles,
limits, CPU affinity, governors, Eden config or plugin permissions. It does not
create a Korri schema. A shared `/run/korri-emulator-bench.lock` protects tools
that opt into it; process/session checks also detect the current Cemu bench.
They cannot prevent an uncooperative external launch that races these checks.

## Retained terminal failures

Core status can retain `HostLaunchFailed` after an earlier game has exited.
Version 0.2.1 accepts that status as idle only with a parsed terminal launch ID
outside this run, no active/activating/deactivating/reloading game **or acquire**
units, and empty `cgroup.procs` contents for the game slice and every descendant.
Unknown/unreadable state, a populated group/unit, a malformed status, and our
own failed launch all fail. It reads actual pseudo-file contents, never file
sizes. It does not dismiss failures, edit Core state or restart the daemon.

`idle.json` and the report retain the earlier status verbatim (ID and message),
the exact native observations, the outside-this-run decision and acceptance
result. Tests exercise real temporary native-state files, including unreadable
state and our own failure. This native-idle proof duplicates a responsibility
in the Cemu bench, but is independently implemented here.

## FPS source and Core isolation gap

**Neither Eden's counter nor MangoHud.** The admitted MangoHud route does not
exist, so 0.2.0 replaces that dependency with a read-only X11 Present observer.
It measures the frames the game presents to Gamescope, never compositor Hz.

`present-observer.c` is an independent Xlib implementation. It uses XRes 1.2's
server-owned client PID, not arbitrary windows or an assumed `_NET_WM_PID`.
It joins the exact renderer's mount namespace, uses that renderer's display
and X authentication selectors, drops to its UID/GID, and translates host PID
to Xwayland's private PID namespace. It subscribes only to that process's
windows. No preload, graphics layer, extra emulator wrapper or env injection
changes the launch. The observer records Pixmap CompleteNotify events;
`NotifyMSC` and mode `Skip` do not count.

Warmup starts after input replay and discards 100 seconds. One dominant window
from the final ten warmup seconds contributes the next 180 one-second FPS bins,
including zero bins. Soak uses 15 minutes after the same warmup. Percentiles
are nearest-rank FPS-bin quantiles, not slowest-frame averages. Window
destruction, replacement/ambiguity, renderer replacement, no Present events or
observer failure fails the run. UST timestamps, not receipt times, bound bins.
The native integration test observes one of two real presenting clients with
no `_NET_WM_PID` and proves foreign-window exclusion and destruction detection.

Cost: X queries/events and one-second telemetry. This does not prove physical
panel scanout or emulated simulation speed. Native Wayland and missing XRes or
Present extensions are unsupported and fail, not fall back to compositor FPS.

**Bubblewrap absent is a recorded Core gap, not an invented plugin gate.**
Core `4e34b8a9e` does not implement ADR 0015; tracked by
[korri-os/korri#184](https://github.com/korri-os/korri/issues/184). The report
states the observed korrid/Gamescope chain and `bubblewrap: absent — core gap
#184`. That is not sandbox acceptance and does not fail an otherwise valid FPS
run. This tool adds no wrapper or permission bypass to conceal the gap.

## Input and Bonneton

`input.py` validates native evemu `E:` events, permits only gamepad
buttons/axes, excludes Guide, and replays through a distinct uinput gamepad.
It uses the existing native Xbox Bluetooth match, not a Korri Seat P1 identity.
The device is closed on failure and buttons/axes are released. It does not
grab a physical controller or change InputPlumber policy.

**No Bonneton script ships yet.** Eden installation and SMO gameplay are a
separate authorized stage; no scene navigation has been verified. Script execution is not proof of input admission, the game's
player-slot assignment, or arrival at the open area after the first landing.
All reports explicitly say navigation is unverified. Record and prove the
script against the selected real save/profile before promoting this collector
to an accepted benchmark. Do not borrow the other workflow's title-screen
script and call it Bonneton.

## Invocation after prerequisites are satisfied

Use real game/runner IDs from the library. The output must be a new directory.
`EDEN_LOG` is an actual native log path, not a proposed Korri storage path. Archive the previous Eden log before a run; the selected path must not
exist before launch. No game, key or firmware file belongs in the report.

```sh
sudo "$BENCH/bin/korri-eden-bench" run \
  --game "$GAME_ID" --runner "$RUNNER_ID" --process-name eden \
  --eden-log "$EDEN_LOG" \
  --input-script "$VERIFIED_BONNETON_EVEMU_SCRIPT" --output "$NEW_RUN_DIR"

sudo "$BENCH/bin/korri-eden-bench" soak --minutes 15 \
  --game "$GAME_ID" --runner "$RUNNER_ID" --process-name eden \
  --eden-log "$EDEN_LOG" \
  --input-script "$VERIFIED_BONNETON_EVEMU_SCRIPT" --output "$NEW_SOAK_DIR"
```

A trivial non-Eden launch omits `--eden-log` and `--input-script`, but still
uses the real library route, Gamescope and a genuinely presenting process.
For the existing admitted GBA route, use `--game wl4 --runner @korri:mgba/mgba
--process-name retroarch`. No shorter duration override is provided: validation
uses the same 100 + 180 s path. Device results are in VERIFICATION.md.

## Reports and evidence

`report.md` includes median/p10/p1, per-policy CPU and GPU min/peak clocks,
all thermal-zone peaks, summed session RSS/swap peaks, launch-chain observation
and exact cleanup results. `telemetry.jsonl`, `fps.json` and `cleanup.json`
retain the supporting measurements; `processes.json` retains executable and
cgroup identities without argv/environment. RSS sums may double-count shared pages.
Unreadable sensors are null, not zero; peaks include warmup, not startup.

`eden.py` retains only Vulkan renderer/driver/device, the existing
`Cpu.cpu_backend` selection line and known fallback strings. It never copies
the complete log or key diagnostics. Backend evidence is **inferred**, not a
positive runtime-backend log line. Three parts must agree:

1. **Selected:** read the actual renderer's `XDG_CONFIG_HOME`/`HOME`, then its
   native `eden/qt-config.ini` and `custom/<title-id>.ini`. Require explicit
   `Cpu.cpu_backend` (0 Dynarmic, 1 NCE), respecting `\\default` and
   per-game `\\use_global`. With native `\\default=false`, cross-check the explicit
   value against this run's actual `Cpu.cpu_backend: Nce`/`Dynarmic` log line.
   With `\\default=true`, the stored value is ignored: only this run's fresh
   effective log may resolve the selection. Missing logs fail; neither the host
   architecture nor a compiled-in default supplies a guessed selection. Eden
   writes `\\default=true` whenever the value equals its default, including a
   person choosing NCE. Only the selection/field/path and matching log lines are
   retained; no entire config or environment.
2. **Not refused:** the new run's log must not contain these pinned-source
   diagnostics:
   - `Fastmem is required to natively execute code in a performant manner, falling back to Dynarmic`
   - `Program does not utilize 39-bit address space, unable to natively execute code`
   - `page size {:#x} is incompatible with 4K paging` (format placeholder in source)
   - `Using private mappings instead of shared ones`
3. **Runtime:** record measured-window `/proc/<renderer>/maps` lines. NCE
   inference requires executable `memfd:HostMemory` and no large anonymous RWX
   cache in every sample. Dynarmic inference requires anonymous RWX regions
   at least 128 MiB in every sample, consistent with its arm64 code caches.
   Missing, conflicting or ambiguous signals produce `backend: unproven` and
   fail backend acceptance. Configuration changes during the run also fail.

**Important correction to the simple mapping heuristic:** executable
`HostMemory` is not unique to NCE. `k_page_table_base.cpp:112–125` propagates
execute permissions whenever NCE is *compiled in*, not only selected.
`host_memory.cpp:558–576` maps them executable on arm64. Dynarmic with fastmem
can therefore have those mappings too. This collector does not use that
mapping alone to decide the backend. Its additional cache discriminator is
still an inference: anonymous mappings are not uniquely tagged; other JITs or
VMA merging can make it ambiguous. Reports must not call it direct execution
proof. The later Odin labelled-view runs validated agreeing log/mapping evidence;
this remains inferred execution, not direct proof.

Source grounding checked in the actual cached Eden **v0.2.1** source,
`/nix/store/inmrhbhn9k0lnrcw8v4hi9rc2nwp9k95-source`:

| Evidence | Source |
|---|---|
| Native file and per-title paths | `src/frontend_common/config.cpp:30–50` |
| Cpu group and selection flags | `src/frontend_common/config.cpp:356–361,912–935`; `src/common/settings.cpp:227–238` |
| Enum order (0/1) | `src/common/settings_enums.h:138`; `src/common/settings.h:247–260` |
| Effective selection log (not execution proof) | `src/common/settings.cpp:117–140`; `src/yuzu/main_window.cpp:2071–2086` |
| Fastmem/page-size and NCE refusal | `src/common/settings.cpp:180–213`; `src/common/host_memory.cpp:498–501,518–534` |
| Native backend branch | `src/core/hle/kernel/k_process.cpp:1295–1317` |
| Non-unique executable HostMemory | `src/core/hle/kernel/k_page_table_base.cpp:112–125`; `src/common/host_memory.cpp:558–576` |
| Dynarmic 128 MiB arm64 cache (8 MiB null-JIT cache is excluded) | `src/core/arm/dynarmic/arm_dynarmic_64.cpp:256–272`; `src/dynarmic/src/dynarmic/backend/arm64/address_space.cpp:27–36` |
| Anonymous RWX allocation on Linux | pinned `eden-emulator/oaknut` v2.0.3, `include/oaknut/code_block.hpp:28–45` (read upstream; same source pin as Eden's Nix dependency) |
| Vulkan renderer identity | `src/video_core/renderer_vulkan/renderer_vulkan.cpp:255–267` |

No patch, new native log format or Korri setting was introduced. `backend.json`
retains the selection and matching map lines (or their absence), not code or
key bytes. Native defaults and weak runtime signals deliberately cost an
unproven result instead of a fabricated backend claim.

[Report format reference](sample-report.md) contains no invented measurements.
Tests exercise parser, statistics and real loopback HTTP failure/cleanup paths;
these do not substitute for an end-to-end device launch.

## Later consolidation with Cemu

The Cemu bench existed on an **unlanded** branch during this work. No imports
or files from it are vendored here. Duplicated responsibilities to consolidate
after both land: localhost RPC transport, idle/exclusive-session checks, exact
stop, Linux process/cgroup observation, uinput/evemu replay, quantiles,
telemetry and Markdown reporting. Eden log evidence and Bonneton navigation
remain emulator-specific. Native-idle proof, the X Present observer and FPS-bin
adapter also duplicate Cemu responsibilities, through independent implementations
(Xlib instead of XCB for the observer). Independence costs duplicate maintenance
now; it avoids a hidden cross-branch deployment dependency.

Follow-up: split the larger `collect()` orchestration into focused launch,
measurement/evidence, and cleanup/reporting code after this shakedown. Keep its
exact-session cleanup and failure-report contracts intact. This change extracts
only the shared process-name matcher; prelaunch emulator refusal and post-stop
emulator/wrapper detection deliberately keep separate allowed-name policies.

## Working test commands

From the repository root:

```sh
nix build .#checks.x86_64-linux.korri-eden-bench --no-link -L
nix build .#checks.x86_64-linux.korri-eden-package --no-link -L
```

The first check supplies `evdev`, runs all bench tests and static checks, and
exercises real two-window Xvfb Present clients. The second runs the native Vulkan
and P1 helpers as separate scripts, each with the packaged crudini path as its
first argument. Passing multiple unittest module names to those scripts is not
supported. No device or plain-system-Python dependency setup is required.

Use `nix run .#eden-bench -- --help` to exercise the local app without a launch.
The collector talks only to the local korrid and needs its existing capability.
For ARM devices, build on the configured builder, sign/copy the exact immutable
package, then invoke that prebuilt collector; never build or evaluate this flake
on the device.

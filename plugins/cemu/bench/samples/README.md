# Hardware proofs — 2026-10-22 campaign

The [2026-10-23 gameplay-gated proof](odin2portal-gameplay-gate/README.md) uses
observed title/loading/gameplay gates and verifies the original save payload
before/after. Its normal Odin run is **37 / 37 / 36 FPS**; the no-input run is
**not measured**, without an FPS file. The two new manual-save attempts remain
unproven. The older samples below do not acquire these new guarantees retroactively.

The later [BotW async-off campaign](../devices/odin2portal-async-off-2026-10-23.md)
has separate [Cemu samples](odin2portal-cemu-async-off/README.md). Its full 720p
baseline measured **39 / 38 / 36 FPS**, not the 60 FPS WL4 validation below.

**Verified:** both updated devices completed the default 100-second warmup and
180-second measurement through korrid. These are WL4/mGBA validation runs,
**not BotW performance results**.

| Device | System generation | median / p10 / p1 / min FPS | Peak recorded thermal zone | Full report |
|---|---:|---|---:|---|
| Retroid Pocket Mini V2 | 29 | 60 / 60 / 59 / 59 | 53.5 °C | [rpminiv2](rpminiv2/report.md) |
| AYN Odin 2 Portal | 8 | 60 / 59 / 59 / 59 | 46.1 °C | [odin2portal](odin2portal/report.md) |

These are nearest-rank percentiles of one-second Present-completion counts.
They are not per-frame reciprocal percentiles or compositor/panel refresh rates.
Temperature peaks include warmup. Per-device READMEs list native clock ranges.
Gzip files retain exact raw telemetry/Present bytes; the committed `fps.json`
files were reproduced from those compressed raw events with the real metrics
implementation. Each device has a final-build 15-second real-path smoke too.
Build/store-path provenance is explicit in each device README.

## Input, modes and cleanup

- [Visible Odin game response](odin2portal/input-proof/README.md): ordinary P2 A
  advances Mega Man Arena credits → story → title. Start/B controls leave the
  corresponding screen byte-identical. Original screenshots and P2 events are
  retained. This is bench/test only, not a product Bluetooth path or BotW proof.
- [A/B](modes/ab/report.md): two named `baseline=-` / `repeat=-` variants on the
  Mini, each 3 s warmup + 5 s measurement. Both measured 60/60/60/60.
  `profiles-before.json` and `profiles-restored.json` are byte-identical. No
  existing profile was available, so this proves lifecycle/restoration, not the
  effect of different CPU/Cemu settings. Package: `y1srqb4008k03nlrgckah2xkplmca8wz`.
- [Soak smoke](modes/soak/report.md): Mini, 3 s warmup + one minute, measured
  60/60/60/60. The 15-minute default is implemented but was **not** run as a
  thermal qualification. Same prebuilt package as A/B.
- Both full-run cleanup records show empty exact game cgroups, no new surviving
  game/wrapper processes, no warning, and unchanged boot/system.
- Both final audits independently check systemd game/acquisition units and every
  games-slice cgroup. They find no emulator/wrapper/observer process, no bench
  pad, only original CompositeDevice0, false ManageAllDevices and no active
  recovery journal. All full-run input observers confirm unchanged built-in
  sources and P1 identity/state.
- Odin's temporary WL4 Gamescope modifier was restored with concurrent-edit
  hash guards. Final library SHA-256 is the exact original:
  `99f5811e9665a93dda71f1f0b8f31f03d8b43afe5b894ccfe277d42d607df769`.

## Limits and retained state

Cemu/saveRoot, actual staged-save load, Cemu-generated P2 profile loading,
BotW fixed-spot navigation, Cemu Vulkan FPS and CPU-mode log evidence remain
unproved. No layout, affinity feature, emulator default or device profile was
invented to fill those gaps. Korrid's settings facts currently report an empty
`gpuDevfreq` list, while direct sysfs GPU telemetry works; GPU limit enforcement
was not tested.

Bubblewrap was not observed. **Core at `4e34b8a9e` does not implement ADR 0015**;
these updated-image results are not acceptance of that policy.

The separate update worker installed/rebooted the current systems. Bench did
not activate generations or touch boot/firmware/partition state. Read-only NAS
content/save hashes were checked again after both updates; inventory and exact
staging paths are under [`../devices/`](../devices/).

Normal game save/play-log effects and benchmark reports remain intentionally.
The prebuilt tools were copied into the Nix store, not added to a system/user
profile. A later GC may remove them; copy the recorded signed closure again.

## Operational deviations and deletions

- Mini GC: approved `nix-collect-garbage` **without `-d`**, 3,377 dead store paths,
  console reports 5.0 GiB freed; all 24 then-existing system generations retained.
  No manual game/content/cache deletion. No Odin GC.
- An initial native Nix check automatically dispatched to configured **unzen**,
  writing Nix-store build artifacts there. No NAS gaming source was changed.
  This was disclosed; subsequent native checks used `--builders '' --max-jobs 1`.
- Fuji's automatic `fuji-1` signature was correctly refused by device trust.
  Existing zao signing fixed delivery; no key/trust/publisher checks were relaxed.
- A historically approved manage-all probe did not admit USB uinput. It was
  restored to false. The successful Bluetooth route and final tool never write
  that policy.
- Mega Man Arena's normal exact stop briefly reported recovery blocked after
  wrapper exit143. Korrid's own subsequent status recovery resolved it without
  reset/restart/journal edits. The original failed RPC remains in the input-proof
  artifacts. See [the core follow-up note](../devices/odin2portal-stop-143.md).

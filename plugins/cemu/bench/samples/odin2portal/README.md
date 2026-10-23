# odin2portal sample — 2026-10-22 campaign

[Full generated report](report.md): default **100 s warmup + 180 s measurement**,
WL4 through real korrid → existing mGBA runner → Gamescope.

| median | p10 | p1 | min | peak recorded zone temperature |
|---:|---:|---:|---:|---:|
| 60.0 | 59 | 59 | 59 | 46.1 °C |

Temperature peak: `temp/thermal_zone8/cpu4-bottom-thermal/mC`, across warmup and measurement, not only CPU.
The FPS values are one-second Present-completion counts, not simulation speed.
Raw `present.csv.gz` reproduces `fps.json` exactly. `telemetry.jsonl.gz` retains
all one-second clocks/thermal samples, with missing reads represented as null.

| sampled native clock (units in key) | minimum | maximum |
|---|---:|---:|
| `cpu/policy0/kHz` | 556800 | 1459200 |
| `cpu/policy3/kHz` | 614400 | 1920000 |
| `cpu/policy7/kHz` | 595200 | 2956800 |
| `gpu/3d00000.gpu/Hz` | 220000000 | 220000000 |

## Build provenance and cleanup

The full run used code `f9f9056`, prebuilt on fuji:
`/nix/store/hrb259y5k6rkp5k8yg4p4jq1gd6mn4f5-korri-cemu-bench-0.1.0`.

The final code `8e1c771` adds acquisition-unit/full-cgroup idle checks and retains
original recovery warnings on timeout. It changes no FPS/input implementation.
Its [15-second real-path smoke](hardened-smoke/report.md) passed on this device:
`/nix/store/ycx1s593595i2c2hyax3l5i58d6iqcw8-korri-cemu-bench-0.1.0`.
Both closures were signed on zao and imported without changing trust.

`cleanup.json` shows an empty exact game cgroup, no new game/wrapper processes,
no stop warning, and unchanged system/boot. `input-observer.json` proves P2
Start admission and restoration of policy/composites/built-in/P1 state. This
**does not prove WL4 reacted**: single-player RetroArch reserves P1.
`final-audit.json` independently proves no game/acquisition unit or populated
cgroup, no emulator/wrapper/observer process or bench pad, only CompositeDevice0,
false ManageAllDevices and no active recovery journal after all tests.

**Not BotW results.** Cemu load, native controller-profile use, Vulkan FPS and a
verified fixed spot remain blocked by the unfinished plugin/saveRoot.
**Not ADR 0015 acceptance.** Bubblewrap was not observed; core at `4e34b8a9e`
does not implement that wrapper. This is not an old-image-only limitation.

[Separate visible P2 game response proof](input-proof/README.md). The temporary
WL4 modifier was restored; the final audit hash matches the original library.

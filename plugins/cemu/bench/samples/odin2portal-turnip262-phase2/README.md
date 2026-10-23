# Odin patched Turnip phase 2 — 2026-10-23

Six valid gameplay-gated samples completed. The owner stopped after async-on
run 2. Async-on run 3 and the 15-minute soak are **not run (owner decision)**.
The device is restored to the shipped 25.3.2 personal test plugin, async off.

| Run | Driver / async | median / p10 / p1 / min | Peak °C | Result |
|---|---|---|---:|---|
| [shipped-01](shipped-01/report.md) | 25.3.2 / off | 37 / 37 / 36 / 36 | 95.9 | PASS |
| [patched-off-01](patched-off-01/report.md) | 26.2.5 mapped / off | — | — | not measured; helper read stale previous log |
| [patched-off-02](patched-off-02/report.md) | 26.2.5 / off | 40 / 40 / 39 / 39 | 97.1 | PASS |
| [patched-off-03](patched-off-03/report.md) | 26.2.5 / off | 40 / 40 / 39 / 39 | 96.3 | PASS |
| [patched-off-04](patched-off-04/report.md) | 26.2.5 / off | 40 / 39 / 39 / 39 | 95.9 | PASS |
| [patched-on-01](patched-on-01/report.md) | 26.2.5 / on | 39 / 39 / 38 / 37 | 96.7 | PASS |
| [patched-on-02](patched-on-02/report.md) | 26.2.5 / on | 39 / 39 / 38 / 38 | 95.9 | PASS |

Every accepted sample is 100 s warmup after verified gameplay, then 180 complete
one-second X Present bins. The reports and `summary.json` retain title, loading,
gameplay and end-check timings. The first refusal publishes no FPS. Its cause
was fixed before another launch: the private helper now requires a fresh log
rather than treating the prior run's 25.3.2 log as the newly mapped 26.2.5 driver.
No reference or classification threshold changed.

Native settings: 1280×720 May settings, FPS++ normal 45/retained advanced 40,
VSync 0, draw-done sync and accurate barriers false. Game-layer CPU/GPU minima
are 100 for every case. No affinity, cooling or system-driver change occurred.
This same-session shipped reference, not older ungated results, is the control.
These are stationary-scene presentations to Gamescope, not panel refreshes or a
proof of a named location, correct rendering, or every BotW scene.

The unmodified bench is
`/nix/store/092bcnlgn7w4vbbp5cknp30j72cv2h32-korri-cemu-bench-0.1.0`.
The selected patched driver is
`/nix/store/g33aq3b8mljbiay5ls6nin7kkwxi3xbq-mesa-turnip-cemu-fmadz-26.2.5`.
Each case's `driver-evidence.json` retains actual mapped-library paths, hashes
of private map files, and relevant Cemu log lines. Completed patched cases show
fresh `Driver version: Mesa 26.2.5` and the requested async setting. Both valid
async-on cases completed loading and gameplay without `draw_execute`/
`activeVertexDS` SIGTRAP. No Cemu dump was found for the campaign. This bounded
absence does not prove the underlying race is fixed. The early refused case's
stale Cemu log is labelled explicitly and is not driver-version evidence.

Compressed Present events reproduce all **1080** accepted bins. Compressed
telemetry, numeric frame descriptors and redacted Cemu logs are retained. No
image, save payload, capability or key is committed or displayed. Checksums
refer to the redacted public copies. No software was built on the device.

## Restore and limits

[The final audit](final-audit.json) proves exact original library/native/P1
bytes, device-default launch settings, all 3772 original cache file names and
hashes, the original complete 54-file save payload and ancestry, the shipped
plugin enabled, and no surviving renderer/observer/helper/test process or bench
pad. Speaker remained `Volume: 0.55 [MUTED]`. Generated caches remain aside, not
deleted. Boot and system are unchanged. WL4 history is unchanged.

Seven launches, including the helper refusal, added **14 history records**.
Supported restore appends a continuation; it does not isolate history or fix
#208/#212. No new in-game save was attempted. No Mini V2 or firmware work ran.
No push, merge or publication occurred.

**Recommendation: keep 25.3.2 with async off until an approved soak.** The three
patched async-off medians are 40 rather than 37 FPS, but long-duration thermal
and crash qualification was skipped. Async-on is slower in both measured runs.
The candidate remains suitable for further qualification, not an immediate
published-default change. Upstream work should proceed with a regression unit
test before an MR; that test and relevant Mesa CI are still missing.

[Full build provenance, gate timings, decision and checks](../../devices/odin2portal-turnip262-phase2-2026-10-23.md).
Private evidence remains on zao under `/tmp/cemu-phase2-20261023/` and on Odin
under `/var/lib/korri/cemu-bench-staging/phase2-*`.

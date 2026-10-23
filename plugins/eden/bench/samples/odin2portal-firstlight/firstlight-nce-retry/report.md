# odin2portal: Eden bench

Status: FAILED: Exact renderer exited or was replaced
Game `super-mario-odyssey-0100000000010000-v0`; runner `@<publisher>:eden/eden`; launch `1cb224bebd3d2f9bc2c28bf9ede29eb7`.
Booted system: `/nix/store/xqbqdwrn3ws25z9dpnhb3nwl47366m8q-nixos-system-odin2portal-sd-card-26.11.20260923.4975466`; kernel `7.2.0`.

## Measurement

Source: game-window X11 Present CompleteNotify/Pixmap; Skip excluded. Neither Eden's counter nor MangoHud.
XRes server-owned PID selects only this renderer's windows inside Gamescope's Xwayland.
Discard 100 s after input replay; one-second FPS bins, zero bins included; nearest-rank p10/p1.
This counts game presentations to Gamescope, not compositor Hz, simulation speed or physical panel scanout.
Window: 0; duration: 180 s; bins: 0.
Input script: none; trivial launch only.

| median FPS | p10 FPS | p1 FPS |
|---:|---:|---:|
| unavailable | unavailable | unavailable |

## Launch and cleanup

Korrid exact session: `korri-game-1cb224bebd3d2f9bc2c28bf9ede29eb7.service`; renderer host PID: 46950. Gamescope observed: True.
Bubblewrap: absent — core gap korri-os/korri#184 (ADR 0015 unimplemented). Not sandbox acceptance, not a bench failure.
Exact cgroup empty: True; no new emulator/wrapper leftovers: True; observer remaining: False.
Cleanup error: none. See cleanup.json and processes.json.
No env injection, wrapper bypass, policy writes, plugin installation or global kills. Normal korrid play/save effects apply.
Raw evidence on device: present.csv, observer.log, telemetry.jsonl, fps.json, cleanup.json, processes.json, idle.json.

## Retained earlier launch status

No retained HostLaunchFailed was accepted as idle.

## CPU/GPU clocks, temperature and memory

One-second read-only samples; peaks include warmup. Null sensors omitted, not replaced with zero.
RSS/swap sum the exact-session processes; shared RSS may be counted more than once.

| metric (native unit) | minimum | peak |
|---|---:|---:|
| cpu/policy0/kHz | 556800 | 2016000 |
| cpu/policy3/kHz | 729600 | 2803200 |
| cpu/policy7/kHz | 2092800 | 2956800 |
| gpu/3d00000.gpu/Hz | 680000000 | 680000000 |
| session/rss_kB | 284488 | 8926976 |
| session/swap_kB | 0 | 0 |
| thermal/thermal_zone0/aoss0-thermal/mC | 39400 | 46500 |
| thermal/thermal_zone1/cpuss0-thermal/mC | 45000 | 54500 |
| thermal/thermal_zone10/cpu5-bottom-thermal/mC | 43000 | 55300 |
| thermal/thermal_zone11/cpu6-top-thermal/mC | 39000 | 46900 |
| thermal/thermal_zone12/cpu6-bottom-thermal/mC | 39800 | 52900 |
| thermal/thermal_zone13/cpu7-top-thermal/mC | 48900 | 70000 |
| thermal/thermal_zone14/cpu7-middle-thermal/mC | 47300 | 72800 |
| thermal/thermal_zone15/cpu7-bottom-thermal/mC | 46900 | 66500 |
| thermal/thermal_zone16/aoss1-thermal/mC | 40600 | 47700 |
| thermal/thermal_zone17/cpu0-thermal/mC | 44600 | 52400 |
| thermal/thermal_zone18/cpu1-thermal/mC | 40600 | 49700 |
| thermal/thermal_zone19/cpu2-thermal/mC | 42200 | 50900 |
| thermal/thermal_zone2/cpuss1-thermal/mC | 43400 | 51700 |
| thermal/thermal_zone20/video-thermal/mC | 40200 | 48100 |
| thermal/thermal_zone21/mem-thermal/mC | 41000 | 48500 |
| thermal/thermal_zone22/modem0-thermal/mC | 36300 | 42600 |
| thermal/thermal_zone23/modem1-thermal/mC | 35900 | 41400 |
| thermal/thermal_zone24/modem2-thermal/mC | 36700 | 41800 |
| thermal/thermal_zone25/modem3-thermal/mC | 37100 | 43400 |
| thermal/thermal_zone26/camera0-thermal/mC | 36300 | 42200 |
| thermal/thermal_zone27/camera1-thermal/mC | 37100 | 43000 |
| thermal/thermal_zone28/aoss2-thermal/mC | 39800 | 46500 |
| thermal/thermal_zone29/gpuss-0-thermal/mC | 36600 | 43000 |
| thermal/thermal_zone3/cpuss2-thermal/mC | 42600 | 50900 |
| thermal/thermal_zone30/gpuss-1-thermal/mC | 37000 | 42600 |
| thermal/thermal_zone31/gpuss-2-thermal/mC | 37000 | 43000 |
| thermal/thermal_zone32/cdsp0-thermal/mC | 35800 | 41800 |
| thermal/thermal_zone33/cdsp1-thermal/mC | 41000 | 47300 |
| thermal/thermal_zone34/cdsp2-thermal/mC | 39000 | 45000 |
| thermal/thermal_zone35/cdsp3-thermal/mC | 37000 | 43000 |
| thermal/thermal_zone36/gpuss-7-thermal/mC | 37400 | 43800 |
| thermal/thermal_zone37/pm8550-thermal/mC | 37000 | 37000 |
| thermal/thermal_zone38/pm8550b-thermal/mC | 37000 | 37000 |
| thermal/thermal_zone39/pm8550ve-thermal/mC | 37000 | 37000 |
| thermal/thermal_zone4/cpuss3-thermal/mC | 43000 | 52500 |
| thermal/thermal_zone40/battery/mC | 27000 | 27000 |
| thermal/thermal_zone5/cpu3-top-thermal/mC | 45700 | 64900 |
| thermal/thermal_zone6/cpu3-bottom-thermal/mC | 45300 | 64900 |
| thermal/thermal_zone7/cpu4-top-thermal/mC | 44200 | 52100 |
| thermal/thermal_zone8/cpu4-bottom-thermal/mC | 44600 | 56900 |
| thermal/thermal_zone9/cpu5-top-thermal/mC | 43400 | 53300 |

## Eden backend evidence

Backend: unproven. See backend.json.
No Eden log: trivial non-Eden launch or evidence unavailable.


## Operator provenance and acceptance boundary

This is the personal test build `@<publisher>:eden` from committed source
`fc795cdfc782bac0c649fec92f765ac7edc1d416`. Test-only composition replaced exactly
one literal, `@korri:eden/eden` → `@<publisher>:eden/eden`, with no other source
delta. Native Eden and the launcher were unchanged. This is not an official
publication or an accepted SMO performance result. No Bonneton input script
was supplied or verified. The generated template's "trivial launch only" text
must not be read as scene validation for this Eden attempt.

See [the stage report](../report.md) for installation, native diagnostics,
settings restoration and the mandatory graphics stop.

# rpminiv2: Eden bench

Status: FAILED: KeyboardInterrupt
Game `super-mario-odyssey-0100000000010000-v0`; runner `@<publisher>:eden/eden`; launch `2ed49314b125906f46c450f4a39627d6`.
Booted system: `/nix/store/861m162v29s7cj9dcsfmdr7ldgh5qgfz-nixos-system-rpminiv2-sd-card-26.11.20260923.4975466`; kernel `7.2.0`.

## Measurement

Source: game-window X11 Present CompleteNotify/Pixmap; Skip excluded. Neither Eden's counter nor MangoHud.
XRes server-owned PID selects only this renderer's windows inside Gamescope's Xwayland.
Discard 100 s after input replay; one-second FPS bins, zero bins included; nearest-rank p10/p1.
This counts game presentations to Gamescope, not compositor Hz, simulation speed or physical panel scanout.
Window: 0; duration: 180 s; bins: 0.
Input script: replayed (position unverified).

| median FPS | p10 FPS | p1 FPS |
|---:|---:|---:|
| unavailable | unavailable | unavailable |

## Launch and cleanup

Korrid exact session: `korri-game-2ed49314b125906f46c450f4a39627d6.service`; renderer host PID: 24828. Gamescope observed: True.
Bubblewrap: absent — core gap korri-os/korri#184 (ADR 0015 unimplemented). Not sandbox acceptance, not a bench failure.
Exact cgroup empty: True; no new emulator/wrapper leftovers: True; observer remaining: False.
Cleanup error: RPC failed: HostRecoveryBlocked. See cleanup.json and processes.json.
No env injection, wrapper bypass, policy writes, plugin installation or global kills. Normal korrid play/save effects apply.
Raw evidence on device: present.csv, observer.log, telemetry.jsonl, fps.json, cleanup.json, processes.json, idle.json.

## Retained earlier launch status

No retained HostLaunchFailed was accepted as idle.

## CPU/GPU clocks, temperature and memory

One-second read-only samples; peaks include warmup. Null sensors omitted, not replaced with zero.
RSS/swap sum the exact-session processes; shared RSS may be counted more than once.

| metric (native unit) | minimum | peak |
|---|---:|---:|
| cpu/policy0/kHz | 979200 | 1804800 |
| cpu/policy4/kHz | 710400 | 1056000 |
| cpu/policy7/kHz | 844800 | 2841600 |
| gpu/3d00000.gpu/Hz | 305000000 | 305000000 |
| session/rss_kB | 5209892 | 5213700 |
| session/swap_kB | 0 | 0 |
| thermal/thermal_zone0/aoss0-thermal/mC | 41100 | 44200 |
| thermal/thermal_zone1/cpu0-thermal/mC | 43800 | 47700 |
| thermal/thermal_zone10/cpu7-top-thermal/mC | 42600 | 59700 |
| thermal/thermal_zone11/cpu4-bottom-thermal/mC | 43000 | 48000 |
| thermal/thermal_zone12/cpu5-bottom-thermal/mC | 44600 | 48800 |
| thermal/thermal_zone13/cpu6-bottom-thermal/mC | 43000 | 50800 |
| thermal/thermal_zone14/cpu7-bottom-thermal/mC | 43000 | 55000 |
| thermal/thermal_zone15/gpu-top-thermal/mC | 39500 | 41100 |
| thermal/thermal_zone16/aoss1-thermal/mC | 41700 | 44400 |
| thermal/thermal_zone17/wlan-thermal/mC | 40100 | 42000 |
| thermal/thermal_zone18/video-thermal/mC | 40900 | 44400 |
| thermal/thermal_zone19/mem-thermal/mC | 41300 | 44400 |
| thermal/thermal_zone2/cpu1-thermal/mC | 44600 | 48000 |
| thermal/thermal_zone20/q6-hvx-thermal/mC | 42000 | 44800 |
| thermal/thermal_zone21/camera-thermal/mC | 39300 | 41300 |
| thermal/thermal_zone22/compute-thermal/mC | 41700 | 44000 |
| thermal/thermal_zone23/npu-thermal/mC | 41300 | 42800 |
| thermal/thermal_zone24/gpu-bottom-thermal/mC | 40100 | 42400 |
| thermal/thermal_zone25/battery/mC | 26000 | 26000 |
| thermal/thermal_zone3/cpu2-thermal/mC | 44200 | 47300 |
| thermal/thermal_zone31/pm8150-thermal/mC | 46248 | 46800 |
| thermal/thermal_zone32/pm8150b-thermal/mC | 36906 | 37587 |
| thermal/thermal_zone33/pm8150l-thermal/mC | 43329 | 43978 |
| thermal/thermal_zone4/cpu3-thermal/mC | 44600 | 48000 |
| thermal/thermal_zone5/cluster0-thermal/mC | 44200 | 50000 |
| thermal/thermal_zone6/cluster1-thermal/mC | 44600 | 50000 |
| thermal/thermal_zone7/cpu4-top-thermal/mC | 42600 | 47700 |
| thermal/thermal_zone8/cpu5-top-thermal/mC | 44200 | 48000 |
| thermal/thermal_zone9/cpu6-top-thermal/mC | 43000 | 50000 |

## Eden backend evidence

Backend: unproven. See backend.json.
No Eden log: trivial non-Eden launch or evidence unavailable.

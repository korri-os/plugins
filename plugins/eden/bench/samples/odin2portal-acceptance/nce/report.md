# odin2portal: Eden bench

Status: PASS (collection; no Bonneton/navigation acceptance claim)
Game `super-mario-odyssey-0100000000010000-v0`; runner `@<publisher>:eden/eden`; launch `3a7d9c68382126a2660aafce3ee6a3b0`.
Booted system: `/nix/store/xqbqdwrn3ws25z9dpnhb3nwl47366m8q-nixos-system-odin2portal-sd-card-26.11.20260923.4975466`; kernel `7.2.0`.

## Measurement

Source: game-window X11 Present CompleteNotify/Pixmap; Skip excluded. Neither Eden's counter nor MangoHud.
XRes server-owned PID selects only this renderer's windows inside Gamescope's Xwayland.
Discard 100 s after input replay; one-second FPS bins, zero bins included; nearest-rank p10/p1.
This counts game presentations to Gamescope, not compositor Hz, simulation speed or physical panel scanout.
Window: 10485773; duration: 180 s; bins: 180.
Input script: replayed (position unverified).

| median FPS | p10 FPS | p1 FPS |
|---:|---:|---:|
| 60.00 | 60.00 | 60.00 |

## Launch and cleanup

Korrid exact session: `korri-game-3a7d9c68382126a2660aafce3ee6a3b0.service`; renderer host PID: 107103. Gamescope observed: True.
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
| cpu/policy3/kHz | 499200 | 2803200 |
| cpu/policy7/kHz | 2726400 | 2956800 |
| gpu/3d00000.gpu/Hz | 680000000 | 680000000 |
| session/rss_kB | 5991792 | 5996100 |
| session/swap_kB | 0 | 0 |
| thermal/thermal_zone0/aoss0-thermal/mC | 50900 | 60100 |
| thermal/thermal_zone1/cpuss0-thermal/mC | 52500 | 61300 |
| thermal/thermal_zone10/cpu5-bottom-thermal/mC | 50100 | 64900 |
| thermal/thermal_zone11/cpu6-top-thermal/mC | 48100 | 58900 |
| thermal/thermal_zone12/cpu6-bottom-thermal/mC | 49300 | 64900 |
| thermal/thermal_zone13/cpu7-top-thermal/mC | 54900 | 68800 |
| thermal/thermal_zone14/cpu7-middle-thermal/mC | 56500 | 72800 |
| thermal/thermal_zone15/cpu7-bottom-thermal/mC | 55300 | 68400 |
| thermal/thermal_zone16/aoss1-thermal/mC | 51700 | 60300 |
| thermal/thermal_zone17/cpu0-thermal/mC | 50100 | 61900 |
| thermal/thermal_zone18/cpu1-thermal/mC | 48900 | 59200 |
| thermal/thermal_zone19/cpu2-thermal/mC | 49300 | 59600 |
| thermal/thermal_zone2/cpuss1-thermal/mC | 50900 | 60500 |
| thermal/thermal_zone20/video-thermal/mC | 48100 | 57200 |
| thermal/thermal_zone21/mem-thermal/mC | 51700 | 60700 |
| thermal/thermal_zone22/modem0-thermal/mC | 46500 | 54800 |
| thermal/thermal_zone23/modem1-thermal/mC | 44600 | 52800 |
| thermal/thermal_zone24/modem2-thermal/mC | 44600 | 52400 |
| thermal/thermal_zone25/modem3-thermal/mC | 46900 | 55200 |
| thermal/thermal_zone26/camera0-thermal/mC | 44600 | 52400 |
| thermal/thermal_zone27/camera1-thermal/mC | 44900 | 53600 |
| thermal/thermal_zone28/aoss2-thermal/mC | 50900 | 59700 |
| thermal/thermal_zone29/gpuss-0-thermal/mC | 48500 | 58500 |
| thermal/thermal_zone3/cpuss2-thermal/mC | 50500 | 59700 |
| thermal/thermal_zone30/gpuss-1-thermal/mC | 48100 | 57700 |
| thermal/thermal_zone31/gpuss-2-thermal/mC | 49700 | 58500 |
| thermal/thermal_zone32/cdsp0-thermal/mC | 47700 | 56900 |
| thermal/thermal_zone33/cdsp1-thermal/mC | 51700 | 61300 |
| thermal/thermal_zone34/cdsp2-thermal/mC | 49700 | 59300 |
| thermal/thermal_zone35/cdsp3-thermal/mC | 49300 | 58100 |
| thermal/thermal_zone36/gpuss-7-thermal/mC | 49700 | 58500 |
| thermal/thermal_zone37/pm8550-thermal/mC | 37000 | 37000 |
| thermal/thermal_zone38/pm8550b-thermal/mC | 37000 | 37000 |
| thermal/thermal_zone39/pm8550ve-thermal/mC | 37000 | 37000 |
| thermal/thermal_zone4/cpuss3-thermal/mC | 51300 | 60500 |
| thermal/thermal_zone40/battery/mC | 27000 | 27000 |
| thermal/thermal_zone5/cpu3-top-thermal/mC | 54100 | 69200 |
| thermal/thermal_zone6/cpu3-bottom-thermal/mC | 52500 | 71200 |
| thermal/thermal_zone7/cpu4-top-thermal/mC | 48500 | 62900 |
| thermal/thermal_zone8/cpu4-bottom-thermal/mC | 48500 | 67700 |
| thermal/thermal_zone9/cpu5-top-thermal/mC | 48500 | 62100 |

## Eden backend evidence

Backend: NCE (inferred: selected from fresh effective log for native default, not refused, executable HostMemory, no large Dynarmic-like RWX cache). See backend.json.
-- Cpu.cpu_backend: Nce
[   0.899682] Render.Vulkan <Warning> video_core/vulkan_common/vulkan_device.cpp:645:Device: Driver requires higher-than-reported binding limits
[   0.961796] Render.Vulkan <Info> video_core/renderer_vulkan/renderer_vulkan.cpp:221:Report: Driver: turnip Mesa driver 26.2.3
[   0.961799] Render.Vulkan <Info> video_core/renderer_vulkan/renderer_vulkan.cpp:222:Report: Device: Turnip Adreno (TM) 740
[   0.961800] Render.Vulkan <Info> video_core/renderer_vulkan/renderer_vulkan.cpp:223:Report: Vulkan: 1.4.354

## Acceptance scope

Bonneton resume platform, camera turned to face the Odyssey; not the open town area; FPS may be optimistic versus open-area play.

Temporary native guest P1 → Korri Seat P2; shipped default remains Seat P1.

`bubblewrap: absent — core gap #184`

# rpminiv2: repeat

Status: PASS

Game: `wl4`; runner: `@korri:mgba/mgba`; launch: `9bedc57faabf9457bdd0e501ab9be2b4`.
System: `/nix/store/hp7kgka5q3abwy25n48p0a511j6kxqjl-nixos-system-rpminiv2-sd-card-26.11.20260923.4975466`; kernel `7.2.0`.
Running korrid: `/nix/store/nvs92ijqg09cranbzg1d0f2whybvvr32-korrid-0.0.0/bin/korrid`.
Warmup: 3 s after input script; measured: 5 s.
Spot: Unspecified; validation launch only. Script execution is not proof of visual position.

## FPS

Source: X11 Present CompleteNotify, kind Pixmap, Skip excluded, one game window.
Counts game presentations to Gamescope's Xwayland, not repeated compositor refreshes.
Bins use X Present's monotonic UST completion timestamps, not observer wakeup time.
This does not prove physical panel scanout or emulated game simulation rate.
Window: 8388610; one-second FPS bins; p10/p1 use nearest rank; zero bins included.

| median | p10 | p1 | min |
|---:|---:|---:|---:|
| 60.00 | 60.00 | 60.00 | 60.00 |

## Launch and cleanup

Gamescope observed: True; bubblewrap observed: False. bubblewrap not observed; ADR 0015 implementation/acceptance is not proved by this run.
Launch settings: `settings.json`; actual command chain: `processes.json`, `unit.txt`.
Exact cgroup empty: True; new game/Gamescope processes absent: True.
Cleanup error: none. System and boot unchanged: True / True.
No sysfs, system or generation writes by the bench.
Cemu-native controller profile: not changed. See `controller-profile.json` when used.
A/B selects existing launch profiles through RPC and restores the original selection.
Korri performs its normal play-log/save effects. uinput device is destroyed.
InputPlumber runtime management: not changed (no input script). See `input-observer.json` and `seat-events.json`.
Bench-only synthetic gamepad identity: `{'name': 'Korri bench gamepad', 'bus': 5, 'vendor': 1118, 'product': 721, 'version': 276, 'phys': 'korri-cemu-bench/input0'}`.
InputPlumber 0.75.2 src/input/manager.rs:1232-1267 admits virtual Bluetooth (bus 0005); installed 60-xbox_one_gamepad.yaml matches 045e:02d1 and sets auto_manage:true. This is a test route, not a product route.
Seat P2 event admission does not prove game navigation; RetroArch normally reserves P1.

## CPU / GPU and thermals

One-second CPU policy kHz, GPU Hz, and all zones: `telemetry.jsonl`.
Unreadable zones are null, not zero. Peaks include warmup.

| zone | peak °C |
|---|---:|
| thermal_zone0/aoss0-thermal | 44.600 |
| thermal_zone1/cpu0-thermal | 47.700 |
| thermal_zone10/cpu7-top-thermal | 48.400 |
| thermal_zone11/cpu4-bottom-thermal | 48.000 |
| thermal_zone12/cpu5-bottom-thermal | 49.600 |
| thermal_zone13/cpu6-bottom-thermal | 49.200 |
| thermal_zone14/cpu7-bottom-thermal | 48.000 |
| thermal_zone15/gpu-top-thermal | 43.400 |
| thermal_zone16/aoss1-thermal | 45.500 |
| thermal_zone17/wlan-thermal | 44.000 |
| thermal_zone18/video-thermal | 45.100 |
| thermal_zone19/mem-thermal | 45.900 |
| thermal_zone2/cpu1-thermal | 48.400 |
| thermal_zone20/q6-hvx-thermal | 45.100 |
| thermal_zone21/camera-thermal | 43.200 |
| thermal_zone22/compute-thermal | 45.500 |
| thermal_zone23/npu-thermal | 44.000 |
| thermal_zone24/gpu-bottom-thermal | 44.400 |
| thermal_zone25/battery | 30.000 |
| thermal_zone3/cpu2-thermal | 47.700 |
| thermal_zone31/pm8150-thermal | 45.210 |
| thermal_zone32/pm8150b-thermal | 41.480 |
| thermal_zone33/pm8150l-thermal | 45.859 |
| thermal_zone4/cpu3-thermal | 47.300 |
| thermal_zone5/cluster0-thermal | 48.800 |
| thermal_zone6/cluster1-thermal | 49.200 |
| thermal_zone7/cpu4-top-thermal | 47.700 |
| thermal_zone8/cpu5-top-thermal | 47.300 |
| thermal_zone9/cpu6-top-thermal | 50.400 |

| clock | min | median | max |
|---|---:|---:|---:|
| cpu/policy0/kHz | 691200 | 787200 | 1248000 |
| cpu/policy4/kHz | 940800 | 1056000 | 1478400 |
| cpu/policy7/kHz | 844800 | 2841600 | 2841600 |
| gpu/3d00000.gpu/Hz | 305000000 | 305000000 | 305000000 |

## Cemu evidence

Not applicable: non-Cemu validation launch.

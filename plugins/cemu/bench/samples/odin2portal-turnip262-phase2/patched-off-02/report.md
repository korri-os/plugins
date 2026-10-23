# odin2portal: baseline

Status: PASS

Game: `the-legend-of-zelda-breath-of-the-wild-usa-dlc-v208`; runner: `@<publisher>:cemu/cemu`; launch: `14ff45fe1451e2efef3e368ef6099bb7`.
System: `/nix/store/xqbqdwrn3ws25z9dpnhb3nwl47366m8q-nixos-system-odin2portal-sd-card-26.11.20260923.4975466`; kernel `7.2.0`.
Running korrid: `/nix/store/nvs92ijqg09cranbzg1d0f2whybvvr32-korrid-0.0.0/bin/korrid`.
Warmup: 100 s after verified gameplay and input completion; requested sample: 180 s.
Spot: Unspecified; validation launch only. Script execution is not proof of visual position.

## Gameplay gate

Offsets are seconds after launch starts.
- title at: 9.272286393001195
- loading at: 45.063635637001425
- gameplay at: 65.07476300900089
- end gameplay at: 347.1426896310004

## Save safety

Save safety: restored and verified.
Original head: `sha256:906b66b921e67640e7372b1115f948b885bd72f2ed552ededddc19c8470e29fd`; restored continuation: `sha256:9d20ef4db6f0d22df81406b8e737e655ce45af33c113df1c58ea89c90e4e126a`.
Payload equal: True; original in ancestry: True.
Additional snapshots before restore: 1; restore snapshots: 1.
See private `save-safety.json` for payload verification and backup. Additional records can include peer arrivals.
Risk: bench and restore snapshots still enter real history and count toward retention. No supported guest/skip-snapshot launch exists.

## FPS

Source: one-second X11 Present Pixmap completion bins; Skip excluded.
Game presentations to Gamescope, not compositor refresh or simulation rate.
p10/p1 use nearest rank; zero bins included.

| median | p10 | p1 | min |
|---:|---:|---:|---:|
| 40.00 | 40.00 | 39.00 | 39.00 |

## Launch and cleanup

Gamescope observed: True; bubblewrap observed: False. bubblewrap not observed; ADR 0015 implementation/acceptance is not proved by this run.
Launch settings: `settings.json`; actual command chain: `processes.json`, `unit.txt`.
Exact cgroup empty: True; new game/Gamescope processes absent: True.
Cleanup error: none. System and boot unchanged: True / True.
Exact-stop warnings: none.
No sysfs, system or generation writes by the bench.
Cemu-native controller profile: {'path': '/var/lib/korri/users/<account>/.config/Cemu/controllerProfiles/controller0.xml', 'originalSha256': '738dffbb744252cd1a089411cc54640626e7157984fa263db3e7b697610ba25a', 'templateSha256': '195356532834db07bc63fcf5907d61742ee4079d3afe1efac277eff6e36c5686', 'restored': True, 'applied': True, 'afterSha256': '195356532834db07bc63fcf5907d61742ee4079d3afe1efac277eff6e36c5686'}. See `controller-profile.json` when used.
A/B selects existing launch profiles through RPC and restores the original selection.
Korri performs its normal play-log/save effects. uinput device is destroyed.
InputPlumber runtime management: {'before': False, 'after': False, 'managementUnchanged': True, 'compositesRestored': True, 'builtinUnchanged': True, 'seatP1Unchanged': True}. See `input-observer.json` and `seat-events.json`.
Bench-only synthetic gamepad identity: `{'name': 'Korri bench gamepad', 'bus': 5, 'vendor': 1118, 'product': 721, 'version': 276, 'phys': 'korri-cemu-bench/input0'}`.
InputPlumber 0.75.2 src/input/manager.rs:1232-1267 admits virtual Bluetooth (bus 0005); installed 60-xbox_one_gamepad.yaml matches 045e:02d1 and sets auto_manage:true. This is a test route, not a product route.
Seat P2 event admission does not prove game navigation; RetroArch normally reserves P1.

## CPU / GPU and thermals

One-second CPU policy kHz, GPU Hz, and all zones: `telemetry.jsonl`.
Unreadable zones are null, not zero. Peaks include warmup.

| zone | peak °C |
|---|---:|
| thermal_zone0/aoss0-thermal | 78.400 |
| thermal_zone1/cpuss0-thermal | 85.200 |
| thermal_zone10/cpu5-bottom-thermal | 94.700 |
| thermal_zone11/cpu6-top-thermal | 81.600 |
| thermal_zone12/cpu6-bottom-thermal | 91.100 |
| thermal_zone13/cpu7-top-thermal | 93.500 |
| thermal_zone14/cpu7-middle-thermal | 97.100 |
| thermal_zone15/cpu7-bottom-thermal | 93.900 |
| thermal_zone16/aoss1-thermal | 78.500 |
| thermal_zone17/cpu0-thermal | 84.400 |
| thermal_zone18/cpu1-thermal | 80.900 |
| thermal_zone19/cpu2-thermal | 82.100 |
| thermal_zone2/cpuss1-thermal | 83.600 |
| thermal_zone20/video-thermal | 78.100 |
| thermal_zone21/mem-thermal | 79.300 |
| thermal_zone22/modem0-thermal | 68.600 |
| thermal_zone23/modem1-thermal | 65.900 |
| thermal_zone24/modem2-thermal | 65.500 |
| thermal_zone25/modem3-thermal | 69.400 |
| thermal_zone26/camera0-thermal | 65.100 |
| thermal_zone27/camera1-thermal | 67.800 |
| thermal_zone28/aoss2-thermal | 77.600 |
| thermal_zone29/gpuss-0-thermal | 74.400 |
| thermal_zone3/cpuss2-thermal | 85.600 |
| thermal_zone30/gpuss-1-thermal | 73.200 |
| thermal_zone31/gpuss-2-thermal | 74.400 |
| thermal_zone32/cdsp0-thermal | 72.800 |
| thermal_zone33/cdsp1-thermal | 80.400 |
| thermal_zone34/cdsp2-thermal | 77.600 |
| thermal_zone35/cdsp3-thermal | 74.800 |
| thermal_zone36/gpuss-7-thermal | 75.200 |
| thermal_zone37/pm8550-thermal | 37.000 |
| thermal_zone38/pm8550b-thermal | 37.000 |
| thermal_zone39/pm8550ve-thermal | 37.000 |
| thermal_zone4/cpuss3-thermal | 84.800 |
| thermal_zone40/battery | 32.000 |
| thermal_zone5/cpu3-top-thermal | 93.100 |
| thermal_zone6/cpu3-bottom-thermal | 94.300 |
| thermal_zone7/cpu4-top-thermal | 86.400 |
| thermal_zone8/cpu4-bottom-thermal | 92.700 |
| thermal_zone9/cpu5-top-thermal | 88.800 |

| clock | min | median | max |
|---|---:|---:|---:|
| cpu/policy0/kHz | 556800 | 2016000.0 | 2016000 |
| cpu/policy3/kHz | 940800 | 2803200.0 | 2803200 |
| cpu/policy7/kHz | 1977600 | 2956800.0 | 2956800 |
| gpu/3d00000.gpu/Hz | 680000000 | 680000000.0 | 680000000 |

## Cemu evidence

```text
[21:57:31.849] Recompiler initialized
[21:57:31.850] ------- Init Vulkan graphics backend -------
[21:57:31.856] Vulkan instance version: 1.4
[21:57:31.858] Driver version: Mesa 26.2.5
[21:57:31.858] Vulkan: present_wait extension: supported
[21:57:31.858] VulkanLimits: UBAlignment 64 nonCoherentAtomSize 64
[21:57:31.863] Vulkan device memory info:
[21:57:35.291] CPU-Mode: Multi-core recompiler
```

# Mini V2: read-only observation

Observed over `root@10.42.3.1:2222` at 2026-10-23 00:11 UTC.
Absent from this host's Tailscale listing. Recovery TCP 22 timed out.
The Cemu worker was running a RetroArch validation bench. No emulator was
launched, no content was copied, and no clock/temperature samples were taken.
These facts describe that concurrent worker's boot, not a clean Eden baseline.

## System and execution prerequisites

| Fact | Observed value |
|---|---|
| Host | `rpminiv2`, aarch64 |
| Kernel | `7.2.0`, PREEMPT, build timestamp 2026-08-16 |
| Booted and current system | `/nix/store/hp7kgka5q3abwy25n48p0a511j6kxqjl-nixos-system-rpminiv2-sd-card-26.11.20260923.4975466` |
| NixOS | 26.11 (Zokor), `26.11.20260923.4975466` |
| Active Vulkan ICD | `/run/opengl-driver/share/vulkan/icd.d/freedreno_icd.aarch64.json` |
| ICD library | `/nix/store/nc0xr281k1wwf7g5f06vkj4l5xcyhs0s-mesa-26.2.3/lib/libvulkan_freedreno.so` |
| Mesa | 26.2.3 from active ICD (25.3.2 also present, not active ICD) |
| Vulkan ICD API | 1.4.354 (not a live Vulkan probe) |
| Running Gamescope | 3.16.18, `/nix/store/d44ibgx6klr0230z2lvm4cjyr25vikcg-gamescope-3.16.18/bin/.gamescope-wrapped` |
| `getconf PAGE_SIZE` | 4096 |
| `vm.memfd_noexec` | 0 |
| `vm.max_map_count` | 1048576 |
| Kernel uclamp | `CONFIG_UCLAMP_TASK=y`, `CONFIG_UCLAMP_BUCKETS_COUNT=5`, `CONFIG_CGROUP_SCHED=y`, `CONFIG_UCLAMP_TASK_GROUP=y` |
| Korri limits | `korri-limits.service` and `korri-limits.socket` both active |
| korrid limits | NOFILE 524288; MEMLOCK 8388608; Nice 0; CPUWeight/IOWeight not set |
| Signature enforcement | `require-sigs = true` |
| Builder key trust | `korri-cache-<builder-1>-1:E8MOww6FoNRlVavEll8JPc2XHYC4HhZnrhqQcd64OtQ=` is in `trusted-public-keys` |

Page size and memfd policy do not rule out NCE. This does not prove NCE works.
No Eden launch has tested it. The limits helper being active does not prove a
particular launch received limits.

`free -m` during the other worker's bench:

```text
               total        used        free      shared  buff/cache   available
Mem:            5559        1295         197         234        4491        4263
Swap:              0           0           0
```

## CPU policies

All policies: `qcom-cpufreq-hw`, governor `schedutil`. Available governors:
`ondemand powersave performance schedutil`. Values below are advertised kHz,
not measured clocks.

| Policy | CPUs | Minimum | Maximum |
|---|---|---:|---:|
| policy0 | 0 1 2 3 | 300000 | 1804800 |
| policy4 | 4 5 6 | 710400 | 2419200 |
| policy7 | 7 | 844800 | 2841600 |

```text
policy0: 300000 403200 518400 614400 691200 787200 883200 979200 1075200 1171200 1248000 1344000 1420800 1516800 1612800 1708800 1804800
policy4: 710400 825600 940800 1056000 1171200 1286400 1382400 1478400 1574400 1670400 1766400 1862400 1958400 2054400 2150400 2246400 2342400 2419200
policy7: 844800 960000 1075200 1190400 1305600 1401600 1516800 1632000 1747200 1862400 1977600 2073600 2169600 2265600 2361600 2457600 2553600 2649600 2745600 2841600
```

## GPU devfreq

`/sys/class/devfreq/3d00000.gpu`, governor `simple_ondemand`.
Available governors: `userspace powersave performance simple_ondemand`.
Minimum 305000000 Hz; maximum 925000000 Hz. Advertised steps:

```text
305000000 400000000 441600000 490000000 525000000 587000000 650000000 670000000 700000000 725000000 750000000 800000000 855000000 905000000 925000000
```

The other devfreq device is `1d84000.ufshc` (storage), not GPU.

## Thermal zone names

```text
0 aoss0-thermal
1 cpu0-thermal
2 cpu1-thermal
3 cpu2-thermal
4 cpu3-thermal
5 cluster0-thermal
6 cluster1-thermal
7 cpu4-top-thermal
8 cpu5-top-thermal
9 cpu6-top-thermal
10 cpu7-top-thermal
11 cpu4-bottom-thermal
12 cpu5-bottom-thermal
13 cpu6-bottom-thermal
14 cpu7-bottom-thermal
15 gpu-top-thermal
16 aoss1-thermal
17 wlan-thermal
18 video-thermal
19 mem-thermal
20 q6-hvx-thermal
21 camera-thermal
22 compute-thermal
23 npu-thermal
24 gpu-bottom-thermal
25 battery
26 xo-thermal
27 wifi-thermal
28 conn-thermal
29 skin-msm-thermal
30 pm8150l-pcb-thermal
31 pm8150-thermal
32 pm8150b-thermal
33 pm8150l-thermal
```

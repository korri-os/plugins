# Odin 2 Portal: read-only observation

Correction: the earlier Tailscale timeout did not rule out USB access. Verified
`root@10.42.4.1:2222` at **2026-10-23 00:36:10 UTC**. Tailscale remains offline
(parent observation). Before collection, `pgrep -a -f 'cemu|eden|bench'` found
no emulator or bench process. The check and facts ran in one SSH session.

Read the Cemu workflow's existing facts for reference, then checked this
running device independently. No files were imported from that branch.
No package, game, key, firmware or save was copied. Nothing was installed or
launched. No clock, temperature, partition, firmware or bootloader write ran.

## System and execution prerequisites

| Fact | Observed value |
|---|---|
| Host | `odin2portal`, aarch64 |
| Kernel | `7.2.0`, PREEMPT, build timestamp 2026-08-16 |
| Booted and current system | `/nix/store/xqbqdwrn3ws25z9dpnhb3nwl47366m8q-nixos-system-odin2portal-sd-card-26.11.20260923.4975466` |
| NixOS | 26.11 (Zokor), `26.11.20260923.4975466` |
| Root mount | `/dev/sda19` on `/` |
| Boot mount | `/dev/sda18` on `/boot` |
| Active Vulkan ICD | `/run/opengl-driver/share/vulkan/icd.d/freedreno_icd.aarch64.json` |
| ICD library | `/nix/store/nc0xr281k1wwf7g5f06vkj4l5xcyhs0s-mesa-26.2.3/lib/libvulkan_freedreno.so` |
| Mesa | 26.2.3 from the active ICD |
| Vulkan ICD API | 1.4.354 (not a new live Vulkan probe) |
| Installed Gamescope | 3.16.18; three store executables listed, including `/nix/store/d44ibgx6klr0230z2lvm4cjyr25vikcg-gamescope-3.16.18/bin/gamescope` |
| `getconf PAGE_SIZE` | 4096 |
| `vm.memfd_noexec` | 0 |
| `vm.max_map_count` | 1048576 |
| Kernel uclamp | `CONFIG_UCLAMP_TASK=y`, `CONFIG_UCLAMP_BUCKETS_COUNT=5`, `CONFIG_CGROUP_SCHED=y`, `CONFIG_UCLAMP_TASK_GROUP=y` |
| Korri limits | `korri-limits.service` and `korri-limits.socket` both active |
| korrid limits | NOFILE 524288; MEMLOCK 8388608; Nice 0; CPUWeight/IOWeight not set |
| Signature enforcement | `require-sigs = true` |
| Expected builder trust | `korri-cache-<builder-1>-1:E8MOww6FoNRlVavEll8JPc2XHYC4HhZnrhqQcd64OtQ=` is trusted |
| Approved test-delivery trust | `korri-cache-<build-host>-1:thKjQnMnPl8AqTuZWJTn+ej9BORTPqzleGue4ZfJ2u4=` is trusted |

The system name contains `sd-card`, but the observed root and ESP mounts are
on internal `sda19`/`sda18`. No storage or boot layout change belongs to this
bench. This current system path differs from the Cemu document's earlier
observation; the table records the device checked now.

Page size and memfd policy do not rule out NCE. They do not prove NCE gameplay.
An active limits helper does not prove that an Eden launch received limits.
Gamescope was not run to collect these facts.

`free -m`:

```text
               total        used        free      shared  buff/cache   available
Mem:            7149         992        1724         179        4791        6156
Swap:              0           0           0
```

## CPU policies

All policies: `qcom-cpufreq-hw`, governor `schedutil`. Available governors:
`ondemand powersave performance schedutil`. Values below are advertised kHz,
not sampled clocks. Scaling limits match the hardware minimum and maximum.

| Policy | CPUs | Minimum | Maximum |
|---|---|---:|---:|
| policy0 | 0 1 2 | 307200 | 2016000 |
| policy3 | 3 4 5 6 | 499200 | 2803200 |
| policy7 | 7 | 595200 | 2956800 |

```text
policy0: 307200 441600 556800 672000 787200 902400 1017600 1113600 1228800 1344000 1459200 1555200 1670400 1785600 1900800 2016000
policy3: 499200 614400 729600 844800 940800 1056000 1171200 1286400 1401600 1536000 1651200 1785600 1920000 2054400 2188800 2323200 2457600 2592000 2707200 2803200
policy7: 595200 729600 864000 998400 1132800 1248000 1363200 1478400 1593600 1708800 1843200 1977600 2092800 2227200 2342400 2476800 2592000 2726400 2841600 2956800
```

## GPU devfreq

`/sys/class/devfreq/3d00000.gpu`, governor `simple_ondemand`.
Available governors: `userspace powersave performance simple_ondemand`.
Current policy minimum **220000000 Hz**, maximum **680000000 Hz**. This is a
fresh observation, not the older Cemu document's 440000000 Hz minimum.
Advertised steps:

```text
220000000 295000000 348000000 401000000 475000000 550000000 615000000 680000000
```

The other devfreq device is storage, `1d84000.ufshc`, not GPU. It advertises
75000000, 150000000 and 300000000 Hz, with `simple_ondemand` governor.

## Thermal zone names

Only names were read, not temperatures or benchmark samples.

```text
0 aoss0-thermal
1 cpuss0-thermal
2 cpuss1-thermal
3 cpuss2-thermal
4 cpuss3-thermal
5 cpu3-top-thermal
6 cpu3-bottom-thermal
7 cpu4-top-thermal
8 cpu4-bottom-thermal
9 cpu5-top-thermal
10 cpu5-bottom-thermal
11 cpu6-top-thermal
12 cpu6-bottom-thermal
13 cpu7-top-thermal
14 cpu7-middle-thermal
15 cpu7-bottom-thermal
16 aoss1-thermal
17 cpu0-thermal
18 cpu1-thermal
19 cpu2-thermal
20 video-thermal
21 mem-thermal
22 modem0-thermal
23 modem1-thermal
24 modem2-thermal
25 modem3-thermal
26 camera0-thermal
27 camera1-thermal
28 aoss2-thermal
29 gpuss-0-thermal
30 gpuss-1-thermal
31 gpuss-2-thermal
32 cdsp0-thermal
33 cdsp1-thermal
34 cdsp2-thermal
35 cdsp3-thermal
36 gpuss-7-thermal
37 pm8550-thermal
38 pm8550b-thermal
39 pm8550ve-thermal
40 battery
```

## Keys and next stage

At this 00:36 UTC snapshot, keys were unavailable and only read-only facts were
authorized. Later user instructions supplied keys and authorized content staging
and a trivial non-Eden launch. The latest [content record](odin2portal-content.md)
and bench VERIFICATION.md supersede that earlier stage boundary. No Eden install
or SMO gameplay was performed.

Bench delivery uses <build-host>'s existing `korri-cache-<build-host>-1` signing route in the bench
README. The signed 0.2.1 closure was copied normally. Do not trust the builder's
unrelated automatic `<builder-1>-1` signature alone, add keys, disable checks, or change
the system for this test.

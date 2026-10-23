# Retroid Pocket Mini V2 — 2026-10-22

Verified over USB SSH: `ssh -o BatchMode=yes -p 2222 root@<device-usb-ip>`.
Port 22 did not answer. Tailscale initially did not provide a working route.

## Current image after the separate worker's update

| Fact | Verified value |
|---|---|
| System generation | 29 (reported by update worker) |
| Booted/current/system-profile target | `/nix/store/hp7kgka5q3abwy25n48p0a511j6kxqjl-nixos-system-rpminiv2-sd-card-26.11.20260923.4975466` |
| Running korrid | `/nix/store/nvs92ijqg09cranbzg1d0f2whybvvr32-korrid-0.0.0/bin/korrid` |
| Kernel / Gamescope / Mesa | `7.2.0` / `3.16.18` / Turnip `26.2.3` |
| korrid, portal, launch-limits | active |
| ManageAllDevices | false; bench leaves it untouched |
| Bubblewrap | not observed; core at `4e34b8a9e` does not implement ADR 0015 |

The `mini-update` worker performed this system update/reboot. Bench did not
activate a generation or write any boot file. The initial hardware inventory
below remains the baseline; per-run settings, clocks and temperatures are in the
sample artifacts. WUA digest was verified again after this update. Both devices'
54 staged save files are checked against `botw-save.sha256`.

## Initial system and trust evidence (before update)

```text
CURRENT
/nix/store/7yvsvmm3nszi2lrv3ry6rybk7c9swxs8-nixos-system-rpminiv2-sd-card-26.11.20260923.4975466
/nix/store/7yvsvmm3nszi2lrv3ry6rybk7c9swxs8-nixos-system-rpminiv2-sd-card-26.11.20260923.4975466
MOUNTS
/dev/sda22 ext4 NIXOS_RPMINIV2
/dev/sda21 vfat RPMINIV2
ESP
0b40f24cadbf43ccadf690d836e545525380fd8481fe8b5915fb8dcdc15691bf  /boot/loader/entries/nixos-generation-1.conf
2cbbf65577fbaea06b0d12573e90c8108b742671bbfab7f5aeb69e4d81c61797  /boot/ubootefi.var
31c8e3072922b24a36d719724011a9cde7b9d421840ab9ec02b0a38747d7cbb5  /boot/boot/grub/grub.cfg.20261022T201130Z.bak
358b2fd08b7c333d58e10ab9b8838f56d041b70cf129a418190943925fb6334f  /boot/boot/grub/grub.cfg.20261018T013625Z.bak
3692c7ea66cda7228d7755737318365252881e4d76ec9a7d5e0ae9508020aa3e  /boot/EFI/nixos/zz84y81zh6kb8jkgywmk9byvq6590lnp-linux-aarch64-unknown-linux-gnu-7.2-Image
39de9119311fa4274f27908a561f2b876133810325d9deff89a9461f832c838b  /boot/EFI/BOOT/BOOTAA64.EFI
3b73acf466fcd3d2e7b7ee64970acd6f2b2a473ff5de526303f65357eff13320  /boot/EFI/nixos/k7iqsb94nnfih2jpl4xpna9b3a923wcd-initrd-linux-aarch64-unknown-linux-gnu-7.2-initrd
43b82cd0ad28d1bc0416a3b9d37e3eb049e4b21f2d667b0c36ce54704f8695fb  /boot/EFI/nixos/x3b1msrllg4d0ldzy95yqrmlv7370c2m-initrd-linux-aarch64-unknown-linux-gnu-7.2-initrd
53abe644510292a5399bed66277e2ef558067789834084d58eeb72b400641543  /boot/EFI/nixos/4lllsfhslww6jx8xxx8309nd8ad0bx49-linux-aarch64-unknown-linux-gnu-7.2-sm8250-retroidpocket-rpminiv2.dtb
53abe644510292a5399bed66277e2ef558067789834084d58eeb72b400641543  /boot/EFI/nixos/bdilkc51nd59xca6k7bkqnivndc9mivc-linux-aarch64-unknown-linux-gnu-7.2-sm8250-retroidpocket-rpminiv2.dtb
53abe644510292a5399bed66277e2ef558067789834084d58eeb72b400641543  /boot/EFI/nixos/y48fgb5fc27lzpxzfq9l41v9abq1pw70-linux-aarch64-unknown-linux-gnu-7.2-sm8250-retroidpocket-rpminiv2.dtb
53abe644510292a5399bed66277e2ef558067789834084d58eeb72b400641543  /boot/EFI/nixos/zz84y81zh6kb8jkgywmk9byvq6590lnp-linux-aarch64-unknown-linux-gnu-7.2-sm8250-retroidpocket-rpminiv2.dtb
5951418c0b65755bee9e665787c83020897338fedf11f8f4c1ea4dbabb142373  /boot/boot/grub/grub.cfg
734f45a5b8c134b5cc161d02a9650fa7cf939abbab1a32f254bab8da201c9385  /boot/boot/grub/dejavu-mono.pf2
746ef802a81a3d5becd6840e4a7d211210d77ca8d8b464056204a5892364c0c1  /boot/EFI/nixos/4lllsfhslww6jx8xxx8309nd8ad0bx49-linux-aarch64-unknown-linux-gnu-7.2-Image
7b31f092549e1fcca7666172efa5a1726a951cf2bb1b4f202d70501e2a3d7a07  /boot/boot/grub/grub.cfg.20261022T014841Z.bak
89173229d4a734b2471772813b2048a154d3e47472e06b0a9a702606e26a36ac  /boot/EFI/nixos/r1i7iik6fygsv2z4883v7gx6izgrm695-initrd-linux-aarch64-unknown-linux-gnu-7.2-initrd
8aa28b0c2b6f613e313b1523f33c75441f4008e5f9bc47654c3ea8e5a07c379c  /boot/EFI/nixos/bdilkc51nd59xca6k7bkqnivndc9mivc-linux-aarch64-unknown-linux-gnu-7.2-Image
8ce1b4d2c9738f197c87a9418a31369a11093c5e0f7e78b24c0b268618198c4f  /boot/EFI/systemd/systemd-bootaa64.efi
99a6439127328de529fe18b184b1921ed9d2756859086b07da2742a8ac6c7636  /boot/boot/grub/grub.cfg.20261022T170814Z.bak
a6c7f5aafd644a48e48efb3f953c08f946cbf443f40ed74e108fb6c91dc127af  /boot/loader/loader.conf
cfcca9fa284e3f7288642013f6ed519cf2561590aa5cb394a4b9771952469670  /boot/EFI/nixos/y48fgb5fc27lzpxzfq9l41v9abq1pw70-linux-aarch64-unknown-linux-gnu-7.2-Image
d280b32a0fec452e079a0ed0cd687f94cf70c03f50695efa157b45bfa70deb5c  /boot/boot/grub/grub.cfg.20261022T083839Z.bak
d35629dfadecb1ec4d33df5241cf8f0f072df81508ff30008695d5a7866fbc79  /boot/boot/grub/grub.cfg.20261007T002155Z.bak
d35629dfadecb1ec4d33df5241cf8f0f072df81508ff30008695d5a7866fbc79  /boot/boot/grub/grub.cfg.20261007T002506Z.bak
d7aef92da7db65c0409a95e04165d3d02c76cae89c1b6ee17c9581de19cf1256  /boot/boot/grub/grub.cfg.20261022T024859Z.bak
db1a9000895c6d37c39b73b6cb29156844be400b7f58a765824f106a6314917e  /boot/boot/grub/grub.cfg.20261017T201039Z.bak
f9de4f9f3faa4b914901eab6eeb819a2dba79b6398c709bab73df5d3ddd317e9  /boot/EFI/nixos/s1yqrmp6xk30x8h7vbywkm73jnwpsmni-initrd-linux-aarch64-unknown-linux-gnu-7.2-initrd
SPACE
Filesystem        1B-blocks         Used   Available Use% Mounted on
/dev/sda22     122244853760 104533204992 11454693376  91% /
BOOT-ID
2487daf0-8b6c-452a-9ef2-316c63f45693
RUNNING
/nix/store/28jh4iv8mqjfh4wpbnj5wcalgv7l2csh-korrid-0.0.0/bin/korrid
```

Both devices trust `korri-cache-fuji-1` and `korri-cache-zao-1` for Nix imports.
The builder's actual automatic signature was `fuji-1`, which the Mini correctly
refused. Bench closures were then signed locally on zao with the existing
`~/.config/korri/cache-key.secret` and copied with `nix copy`; signature checks
remained enabled. No publisher configuration or system trust was changed.
Builder trust is not plugin-publisher authorization. `@korri` binds to
`korri-plugins-1`; `@<publisher>` binds to `<publisher-key-name>`.
Cemu plugin installation remains forge's work through normal inspect/install/enable.

## Hardware (frequency units: CPU kHz, GPU Hz)

```text
CPU
/sys/devices/system/cpu/cpufreq/policy0
affected_cpus=0 1 2 3
scaling_available_frequencies=300000 403200 518400 614400 691200 787200 883200 979200 1075200 1171200 1248000 1344000 1420800 1516800 1612800 1708800 1804800
scaling_available_governors=ondemand powersave performance schedutil
scaling_governor=schedutil
scaling_min_freq=300000
scaling_max_freq=1804800
/sys/devices/system/cpu/cpufreq/policy4
affected_cpus=4 5 6
scaling_available_frequencies=710400 825600 940800 1056000 1171200 1286400 1382400 1478400 1574400 1670400 1766400 1862400 1958400 2054400 2150400 2246400 2342400 2419200
scaling_available_governors=ondemand powersave performance schedutil
scaling_governor=schedutil
scaling_min_freq=710400
scaling_max_freq=2419200
/sys/devices/system/cpu/cpufreq/policy7
affected_cpus=7
scaling_available_frequencies=844800 960000 1075200 1190400 1305600 1401600 1516800 1632000 1747200 1862400 1977600 2073600 2169600 2265600 2361600 2457600 2553600 2649600 2745600 2841600
scaling_available_governors=ondemand powersave performance schedutil
scaling_governor=schedutil
scaling_min_freq=844800
scaling_max_freq=2841600
GPU
/sys/class/devfreq/1d84000.ufshc
name=1d84000.ufshc
available_frequencies=37500000 300000000
available_governors=userspace powersave performance simple_ondemand
governor=simple_ondemand
min_freq=37500000
max_freq=300000000
/sys/class/devfreq/3d00000.gpu
name=3d00000.gpu
available_frequencies=305000000 400000000 441600000 490000000 525000000 587000000 650000000 670000000 700000000 725000000 750000000 800000000 855000000 905000000 925000000
available_governors=userspace powersave performance simple_ondemand
governor=simple_ondemand
min_freq=610000000
max_freq=925000000
THERMALS
/sys/class/thermal/thermal_zone0 aoss0-thermal 36800
/sys/class/thermal/thermal_zone1 cpu0-thermal 39100
/sys/class/thermal/thermal_zone10 cpu7-top-thermal 45700
/sys/class/thermal/thermal_zone11 cpu4-bottom-thermal 38400
/sys/class/thermal/thermal_zone12 cpu5-bottom-thermal 39900
/sys/class/thermal/thermal_zone13 cpu6-bottom-thermal 42600
/sys/class/thermal/thermal_zone14 cpu7-bottom-thermal 44600
/sys/class/thermal/thermal_zone15 gpu-top-thermal 35200
/sys/class/thermal/thermal_zone16 aoss1-thermal 36600
/sys/class/thermal/thermal_zone17 wlan-thermal 36600
/sys/class/thermal/thermal_zone18 video-thermal 37000
/sys/class/thermal/thermal_zone19 mem-thermal 37400
/sys/class/thermal/thermal_zone2 cpu1-thermal 40300
/sys/class/thermal/thermal_zone20 q6-hvx-thermal 37000
/sys/class/thermal/thermal_zone21 camera-thermal 35500
/sys/class/thermal/thermal_zone22 compute-thermal 37000
/sys/class/thermal/thermal_zone23 npu-thermal 35900
/sys/class/thermal/thermal_zone24 gpu-bottom-thermal 36600
/sys/class/thermal/thermal_zone25 battery 26000
/sys/class/thermal/thermal_zone26 xo-thermal
/sys/class/thermal/thermal_zone27 wifi-thermal
/sys/class/thermal/thermal_zone28 conn-thermal
/sys/class/thermal/thermal_zone29 skin-msm-thermal
/sys/class/thermal/thermal_zone3 cpu2-thermal 39100
/sys/class/thermal/thermal_zone30 pm8150l-pcb-thermal
/sys/class/thermal/thermal_zone31 pm8150-thermal 36808
/sys/class/thermal/thermal_zone32 pm8150b-thermal 34732
/sys/class/thermal/thermal_zone33 pm8150l-thermal 38301
/sys/class/thermal/thermal_zone4 cpu3-thermal 39900
/sys/class/thermal/thermal_zone5 cluster0-thermal 41800
/sys/class/thermal/thermal_zone6 cluster1-thermal 42200
/sys/class/thermal/thermal_zone7 cpu4-top-thermal 39100
/sys/class/thermal/thermal_zone8 cpu5-top-thermal 40300
/sys/class/thermal/thermal_zone9 cpu6-top-thermal 44200
DISPLAY
1080x1240
PUBCONFIG
#! /nix/store/idnyqaaix26szkvhs1mjgi7990jajz9a-bash-5.3p15/bin/bash -e
export KORRI_PLUGIN_NIX='/nix/store/lz2w1as1p0c2lajnvy2iif1i3vqh189a-nix-2.34.8/bin/nix'
export KORRI_PLUGIN_SYSTEMCTL='/nix/store/gnadg5slifq2r638xvz4pv6vrsdl9xkj-systemd-261.2/bin/systemctl'
export KORRI_PLUGIN_IPTABLES='/nix/store/2gl1g8549r89ah0n4r69bw4yga2wigcq-iptables-1.8.13/bin/iptables'
export KORRI_PLUGIN_IP6TABLES='/nix/store/2gl1g8549r89ah0n4r69bw4yga2wigcq-iptables-1.8.13/bin/ip6tables'
export KORRI_PLUGIN_CURL='/nix/store/xrpn2mzijwrl6rvi8h1rg73c3dr8i4d0-curl-8.22.0-bin/bin/curl'
exec -a "$0" "/nix/store/lkga8p06v4m4y04sxkinqlh6viqd2q7b-korri-plugin-host-0.0.0/bin/.korri-plugin-wrapped"  "$@"
PACKAGES
/nix/store/d44ibgx6klr0230z2lvm4cjyr25vikcg-gamescope-3.16.18/bin/gamescope
/nix/store/im9nvnfnnkgcgd2i3yk3kwrwk5d9a8f8-gamescope-debug-3.16.18/bin/gamescope
/nix/store/iw35i62ccjdirpd5z99837rpx08rnhf9-gamescope-3.16.18/bin/gamescope
/nix/store/phn1raivkackkbx7f84knankjfyyq5wr-gamescope-3.16.18/bin/gamescope
SD
NAME    TYPE   SIZE FSTYPE MOUNTPOINTS
```

## Vulkan

Prebuilt `vulkan-tools-1.4.328.0` was copied as a signed Nix closure; no target
build ran. `vulkaninfo --summary` reports Turnip Mesa **26.2.3**,
Adreno **650**. Gamescope is **3.16.18**.
Both `CONFIG_UCLAMP_TASK=y` and `CONFIG_UCLAMP_TASK_GROUP=y`; `korri-limits`
is active. The physical panel mode is 1080×1240; Sway logical 1240×1080.

## Content and admission

WUA destination: `/var/lib/korri/games/wiiu/The Legend of Zelda - Breath of the Wild (USA) (DLC) (v208).wua`.
Transfer completed; destination SHA-256 matched the source before the device update handoff.
SHA-256 at source: `064e512446009a42e6de6399b6665c96abe820be039cb3b5a968e40591d8c9ff`.
Size: **13,660,330,872 bytes**.
Source access: read-only `ssh -o BatchMode=yes <owner-storage-login>`;
`<owner-storage>` plus the exact basename above.
No Thor fallback was needed.

Save staging: `/var/lib/korri/cemu-bench-staging/save/00050000/101c9400/`.
Boss staging: `/var/lib/korri/cemu-bench-staging/boss/00050000/101c9400/` (empty source).
54 file hashes match unzen, zao staging, and this device; exact relative paths
and SHA-256 are in [`botw-save.sha256`](botw-save.sha256).
Manifest SHA-256: `d23810a3d84be864492d6c912c846f93e693572fd7b0b96ee5ed09a23c8b3b68`.
Source root: `<owner-storage>`.
The `save/…/user/80000001/0/caption.jpg` was inspected: Link is already standing
inside a shrine. This is visual save-preview evidence, not a verified Cemu load.
All source files, including existing Syncthing conflict copies, are preserved;
we did not pick a conflict winner or invent the plugin's final saveRoot layout.
No `101c9500` data was supplied by these two source directories.

The live library has explicit `device.yaml` storage/source pairs (e.g. `gba`),
not an implicit scan of every `games/` child. **No `wiiu` source is paired yet.**
The file location follows the device's existing `games/<system>/` convention;
it is staging until the enabled Cemu declaration supplies system `wiiu`, an
existing source/storage pair is configured for this directory, and
`app.discovery.rescan` admits it. No library schema or record was invented.
A microSD path can be a source's storage root under that same contract; this
worker did not create a mount or a source definition.

## Exact existing catalog admission path

`services/korrid/src/catalog_cli.rs` defines the operator command:
`korrid catalog pair <directory> <system>`. Once an enabled Cemu plugin declares
`wiiu`, run it as korrid for `/var/lib/korri/games/wiiu` and `wiiu`, with
`KORRID_STORAGE_ROOT=/var/lib/korri` and
`KORRID_PRIVATE_STATE_ROOT=/var/lib/korrid`. **The daemon must be stopped during
this offline catalog change**, then started normally. This writer creates the
existing storage/source records; do not hand-author a new schema. It rejects
an unknown system. No pair command was run before Cemu was installed.
A mounted microSD directory uses the same existing command; the actual mount
and directory must first be established, not assumed or invented.

## Final benchmark and restoration proof

[Default 100 + 180 second report](../samples/rpminiv2/report.md),
[final audit](../samples/rpminiv2/final-audit.json), and native clock/thermal ranges
in [the sample README](../samples/rpminiv2/README.md). Final profile link was
`system-29-link`; booted/current/profile resolved to the table's same toplevel.
Final available filesystem bytes: **11,959,754,752**.

The final prebuilt tool also passed a 15-second real RPC lifecycle smoke.
No emulator/Gamescope/observer process, active game/acquisition unit, populated
games cgroup, bench pad or active recovery journal remained. Only original
CompositeDevice0 remained, ManageAllDevices was false, and the full-run input
observer confirmed unchanged built-in sources and P1 state.

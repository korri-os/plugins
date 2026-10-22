# Mini V2 update checkpoint — 2026-10-22

System update **not performed by bench**. The owner approved GC and an update,
but required a documented internal-UFS update path first. At core
`4e34b8a9ed859560acac59c218c7af872221d3ed`, neither
`nix/devices/rpminiv2/README.md` nor `INTERNAL.md` documents refreshing the
installed GRUB entry. README explicitly leaves updates outside its milestone.
The worker stopped before activation. A separate `mini-update` worker owns the
reviewed procedure and any later update/reboot. No boot files, system profile,
partition, firmware, GPT or generation were changed by bench.

Read from scratch checkout `/tmp/forgerie-scratch/f-21aa8556/bench-mini-update`,
not by changing the shared core checkout.

## Before (read-only)

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

## Approved GC only

`nix-collect-garbage` ran **without `-d`**. It removed 3,377 unrooted Nix store
paths and reported **5.0 GiB freed**. The earlier `--print-dead` dry run summed
**5,413,103,760 NAR bytes**; NAR size is not allocated filesystem space.
All 24 system generations remained, with generation 24 current.
Free root space rose from **11,454,693,376** to **17,119,956,992 bytes**.
No content or caches were manually deleted. No GC ran on Odin.
Full deletion log on zao: `/tmp/cemu-bench-evidence/mini-gc.txt`.

| Existing data before GC | `du -xh --max-depth=2` |
|---|---:|
| `/var/lib/korri` | 68 GiB |
| `users/<person>` | 51 GiB |
| `games/xbox-360` | 15 GiB |
| `cache/proton` | 2.1 GiB |
| `cache/mega-man-maker` | 159 MiB |
| `/var/lib/korrid` | 2.3 MiB |
| `/var/cache` | 12 KiB |

A microSD slot exists (README boot/recovery path). No `mmcblk` device or
mounted content card was present in `lsblk`. The current library uses explicit
source/storage pairs; mounting a card alone does not register Wii U content.
No automount configuration or card was added.

# FAKE-08 producer

`korri-plugin-fake08` is the ordinary catalogue-generated `@korri:fake08`
plugin. Its runner is `@korri:fake08/fake08`; its system is `pico8`.
It owns its RetroArch program, checked settings, seat autoconfig and core.
It uses the existing protected launch helper without changes.

| Item | Pin / installed path |
|---|---|
| FAKE-08 | `jtothebell/fake-08`, `814991a2571ad3970e386cef48f3b148aa1c27b9` |
| Recursive z8lua | `jtothebell/z8lua`, `e6928578d46b61fd5ea30cfcf547e855a30a0553` |
| Recursive source NAR hash | `sha256-+2jhG4hMc5P1it1/ksTlWDRKAvRZUpkq2CZ2NxcEITg=` |
| Core (inside its native output) | `lib/retroarch/cores/fake08_libretro.so` |
| Core information | `lib/retroarch/cores/fake08_libretro.info` |
| Original licenses and credits | `share/doc/libretro-fake08/` |
| Source provenance | `nix-support/libretro-fake08/manifest.txt` |

Only `make -C platform/libretro platform=unix` runs. No standalone player,
Vita postcard, platform art, sample games or official PICO-8 runtime is
installed. The upstream `.info` and ABI version strings disagree; the source
revision, not either version string, identifies this build.

## Cartridge loading and limits

Discovery declares exactly `p8` and `p8.png`, never arbitrary `png`.
Core's scanner must support compound suffixes for the latter claim to work.
This producer does not change Core or implement dependency approval/install.

Inspected implementation, at the pinned source revision:

- `platform/libretro/libretro.cpp:retro_load_game` sets the cartridge directory
  from the initial content path, then queues memory-backed or path loading.
- `source/cart.cpp:Cart` resolves relative names against that directory. An
  extensionless name tries `.p8`, then `.p8.png`. A `#` BBS name is stripped;
  the core expects a local file, not a BBS network download.
- `source/picoluaapi.cpp:load` calls `Vm::vm_load`; `source/vm.cpp` loads and
  runs the next cart. `source/PicoRam.h:Reset` leaves upper memory intact.
- `retro_load_game_special` is unsupported. Local Lua `load()` is distinct
  from libretro's special/multi-ROM interface.

Into Ruins needs the author's unchanged offline `intoruins.p8.png` and
`intoruins_main.p8.png` together. Launch the first. It writes game data to
upper memory before loading the second. Root packaging proof is
`/tmp/korri-into-ruins-packaging.md`; the author's source is
https://github.com/Woflox/intoruins/tree/25fd2e196f9cf970de6ee7aa2ba211bcbb94bfe3/carts/offline.
Do not substitute the BBS revision files or resave/optimize the PNGs.

The ABI check runs authored `.p8` and `.p8.png` fixtures and a local PNG
multicart handoff with retained upper memory. The pinned upstream emits a
`__addbreadcrumb` warning on that handoff; the framebuffer and upper memory
tests still pass.

A separate x86_64 headless smoke test ran the unchanged author offline pair
for 2,400 frames with simulated X presses. Cart 2 raised
`[string "--iNTO rUINS cART 2..."]:62: attempt to concatenate field '?' (a nil value)`.
It also emitted the breadcrumb warning. Into Ruins is therefore **not verified
playable on this pin**; this is a concrete compatibility issue, not a passing
game test. No emulator or cartridge workaround is included. All 24 games,
reset-to-title, sound, save states and device performance remain unverified.

## Licensing

Read the installed original `LICENSE.MD`, `THIRD-PARTY.md` and
`original-notices/`. MIT alone does not describe the linked code: it includes
WTFPL 2, zlib-style, Unicode ConvertUTF, and upstream-declared CC BY-SA 3.0
oval-drawing code. The latter's Stack Overflow answer also credits a Michael
Abrash algorithm; upstream's declaration is not independent legal clearance.
No publication or signing is part of this producer work.

## Checks

Run for `x86_64-linux` and `aarch64-linux` on build machines:

```sh
nix build --no-link .#packages.x86_64-linux.korri-plugin-fake08 \
  .#checks.x86_64-linux.korri-fake08-package \
  .#checks.x86_64-linux.korri-fake08-admission
```

Replace `x86_64-linux` with `aarch64-linux` for the other build. The package
check loads the real `.so`, typechecks the real generated source, reads the
real plugin manifest and exercises its unchanged launch/settings helper.
Admission uses the normal Core host's local `seed` check, like Sunshine's
existing admission check. It does not establish publisher trust or approve a
real device install.

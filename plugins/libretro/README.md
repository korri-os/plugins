# The libretro core catalogue

One catalogue produces one plugin package per core. Installing mGBA does not
install every core, and removing it does not disturb the others.

| File | What it holds |
|---|---|
| `cores.nix` | The catalogue. One entry per core |
| `systems.nix` | One content definition per system, shared across cores |
| `groups.nix` | Related-system groups |
| `core-plugin.nix` | Turns one entry into one plugin package |
| `retroarch.ts` | The shared launch helper every generated core uses |
| `example-check.nix` | Proves the committed mGBA example still matches the generator |
| `frontend-override-check.nix` | Proves one core can name its own frontend build |
| `nix/libretro-typecheck.nix` | Typechecks supported generated plugins and the helper; runs `content-check.ts` |
| `default.nix` | Maps the catalogue to `korri-plugin-<name>` packages |

## Adding a core

Add an entry to `cores.nix`:

```nix
gambatte = {
  title = "Gambatte";
  description = "Runs Game Boy and Game Boy Color content with the Gambatte libretro core.";
  core = pkgs.libretro.gambatte;
  coreFile = "${pkgs.libretro.gambatte}/lib/retroarch/cores/gambatte_libretro.so";
  systems = [ "gb" "gbc" ];
};
```

That is the whole change. The package `korri-plugin-gambatte` appears, with the
plugin id `@korri:gambatte`, the runner `@korri:gambatte/gambatte`, its own
`controls`, each system's `content` rules, and the `gameboy` group. A core
contributes a group when it runs at least two members. Groups keep their full
member lists; Core ignores members no enabled plugin declares.

Name the core file exactly. A file name is not derived from a package name,
because the two disagree: `beetle-pce-fast` ships
`mednafen_pce_fast_libretro.so`.

Add new system content rules to `systems.nix`, not to a core entry. Extensions
are the union of the catalogue's former per-core lists. NES and FDS are separate
systems. Only FCEUmm, Mesen and Nestopia run both; QuickNES runs NES only.

Keep extensions conservative. An extension owned by several systems, such as
`bin`, stays out until a real library needs it. Do not add general archive
extensions or Lynx `o` object files. Mega Drive keeps `md`; an explicit source
pairing scopes it to content rather than arbitrary README files.

`content-check.ts` checks all systems and all four groups from the generated
modules. On x86_64 this covers all 91 cores. Other targets keep nixpkgs' platform
restrictions and check only supported cores.

The shared table cites the header detectors for NES, FDS, Lynx, Atari 7800 and
SNES, and the GBA logo evidence. Systems without an explicit layout use Core's
`**/{title}.{ext}` default. Content rules identify files without requiring an
enabled runner.

## Netplay metadata

`core-plugin.nix` matches each `coreFile` basename to its upstream info file in
`pkgs.libretro-core-info`, pinned through the publisher's Nixpkgs lock. The
current source is libretro-core-info **v1.22.2**, with Nixpkgs' fixed source hash.
Only `savestate_features = "deterministic"` grants a runner `netplay`.
Missing info, a missing flag, and other flag values grant none. There is no
hand-written eligibility list.

`generate-netplay.py` loads the built core on the native build machine and calls
`retro_get_system_info`, without initializing the core or running content. It
writes only `{ library, version }` from `library_name` and `library_version`.
It does not use `display_version` or the plugin version. A missing symbol,
unloadable library, or empty name/version fails the deterministic core's build.
Installed plugins remain effect-free TypeScript source. Cross builds that cannot
execute the core's architecture are refused; publication uses native builders.

```sh
nix build --no-link .#checks.x86_64-linux.korri-libretro-netplay
```

This focused gate imports the installed Snes9x 2010 and FAKE-08 declarations.
An independent C probe reads Snes9x 2010's actual `.so` and compares both facts;
FAKE-08's upstream `serialized` flag produces no `netplay`. It also tests generator
boundaries and typechecks both generated modules and the helper against the
pinned launch contract. The RetroArch settings gate tests both launch roles and
keeps password-file contents out of argv and generated files.

Generating declarations now needs the core artifacts, including for the broad
catalogue typecheck. Run this focused gate for netplay work instead of building
all cores merely to test the shared helper. No test here proves device gameplay
or determinism across CPU types.

## Naming a different frontend

An entry may add `frontend` to choose the RetroArch build that core runs:

```nix
mgba-nightly = {
  title = "mGBA (nightly frontend)";
  description = "Runs Game Boy Advance content on a pinned RetroArch build.";
  core = pkgs.libretro.mgba;
  coreFile = "${pkgs.libretro.mgba}/lib/retroarch/cores/mgba_libretro.so";
  frontend = pinnedRetroarch;
  systems = [ "gba" ];
};
```

Omit it and the core takes nixpkgs' RetroArch, which is what every entry does
today. The override selects the **build**, never the protections: Korri's
read-only, non-interactive netplay and launch-overlay patches and their native
regressions still run against whatever is chosen. A fork the patches cannot
apply to fails the build rather than quietly losing those protections.

The settings evidence follows the selected binary. A core answering
`settings.describe` from the default build's schema while running a different
build would report keys its program does not have, so the schema is re-derived
from the exact program.

Overriding one core changes that core only. `frontend-override-check.nix`
builds three cores and reads their manifests to hold all of it: the program and
the settings evidence move, the libretro core does not, and a second core keeps
the default frontend.

## What a generated plugin is, and is not

A generated plugin is an ordinary plugin. It is built by the same builder,
admitted by the same rules, and has no interface a hand-written plugin lacks.

Each core carries **its own RetroArch** inside its own closure. Two cores
installed together share one store path, so the disk cost is paid once, but
neither can break the other by being removed. `@korri:retroarch` names a
settings family, not a package a core depends on.

Two cores may run one system. Genesis Plus GX and PicoDrive both run Mega
Drive. Their content rules combine and the player chooses the runner.

## Nintendo DS panes and melonDS layouts

Nintendo DS declares `upper` and `lower` panes, arranged `upper-above-lower`.
The melonDS runner offers `Top/Bottom`, `Left/Right`, `Top Only` and `Bottom
Only`. These are native `melonds_screen_layout` values in the pinned libretro
melonDS source (`66b5d2634cd0a79030562811e6e05f5532f800ba`,
`src/libretro/libretro_core_options.h`). Its `screenlayout.cpp` and
`opengl.cpp` give equal halves for the two-pane layouts with screen gap zero.
Reversed layouts (`Bottom/Top`, `Right/Left`) do not serve the first display
arrangement case. Hybrid layouts remain outside this slice.

Every melonDS launch uses `input_driver = "x"` in the existing launch-owned
`retroarch.cfg`, while `input_joypad_driver` stays `udev` for Korri's shared
controller seats. On the RG DS, the game user cannot open the physical Goodix
touchscreens; Xwayland supplies compositor-routed pointer input without new
input permissions. The owner's verified `x` + `Mouse` launch had offset taps;
`x` + `Touch` hit the tapped location. The latter is melonDS's absolute pointer
mode (`melonds_touch_mode` in the same pinned core-options header).

The handler uses its existing rendered configuration, not another append file:
it emits one assignment per key and does not alter netplay's password-config
arguments or native duplicate-key ordering. The launch requires the `x` driver
even if authored settings name another input driver. It does not edit those
settings, and `config_save_on_exit` remains false. Other cores retain their
existing input-driver behavior.

The handler provisions `melonds-layout.opt` beside that configuration with
`melonds_threaded_renderer = "enabled"` and `melonds_touch_mode = "Touch"`.
The core's default single-threaded renderer cannot keep the DS rate (59.9 fps)
on the RG DS. Measured unthrottled on 2026-10-28 with GL output across both
displays at 1.992 GHz, the core ran at 45 fps without the render thread and 62 fps
with it (korri-os/korri#340). Like the other overlay keys, it applies to one
launch and is never saved to the person's options file. When korrid supplies a layout, the same overlay
also contains `melonds_screen_layout` and `melonds_screen_gap` (zero). The plan
passes its path through `KORRI_RETROARCH_CORE_OPTIONS_OVERLAY`. Accepted layout
ids come from the generated runner declaration.

The Korri-specific RetroArch patch applies the overlay in memory after native
source selection and parsing. Native precedence stays unchanged: game-specific,
then folder-specific options (when enabled), then the existing per-core file
(when enabled), then `core_options_path` or `retroarch-core-options.cfg` beside
the frontend configuration. A missing per-core file is initialized from the
custom/global source. The native config-directory setting still applies.
Every other option comes from exactly the source RetroArch normally selects;
no lower-priority files are merged.

For every overlaid key, the patch keeps the original native value, including
its absence or invalid raw value. Exit flushes and menu saves use that original,
not the overlay value, even if the menu changed that key during the launch.
Other option edits save normally. The overlay file is never a save destination.
Build-host tests compile the real option manager, parser and native source
selector. They check all five source types, missing per-core initialization,
legacy and v2 options, menu and exit saves, and compare no-overlay results and
serialized files byte-for-byte against unpatched RetroArch.

Without a layout, melonDS still gets absolute touch but does not override native
layout or gap. Other cores keep their plans byte-identical; the regression
compares 54 complete serialized plans with candidate `2f5aedc`, including custom
input drivers, option routing and netplay. The native regression also proves
that `Touch` never replaces the original saved `Mouse`, missing or invalid raw
value. Without an overlay, the patched frontend keeps native behavior.
The handler performs no reads or writes; korrid provisions its returned plan.
Native builds and checks run on build hosts, never on a device.

The pinned Core contract supplies `PluginLaunchInput.layout` directly. The
`korri-melonds-admission` check runs that Core's typed registry parser against
the actual packaged plugin and evaluates each layout through its real sandbox.
Older hosts without the panes/layouts parser cannot admit this candidate.
Publication scopes the overlay gate to RetroArch packages and adds typed Core
admission when the selected package is melonDS.

## The runner owns its settings

`settings.ts` is generated beside the plugin from the pinned RetroArch source:
the keys that build actually reads, and their types. The runner answers
`settings.describe` and `settings.validate` from it, and leaves out of the
native configuration anything this build cannot apply. korrid holds no key
table and reads no settings file; it reports what the runner says as launch
warnings and never rewrites what a person authored.

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
read-only patch and its compiled source regression still run against whatever
is chosen, and a fork the patch cannot apply to fails the build rather than
quietly losing the protection.

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

## The runner owns its settings

`settings.ts` is generated beside the plugin from the pinned RetroArch source:
the keys that build actually reads, and their types. The runner answers
`settings.describe` and `settings.validate` from it, and leaves out of the
native configuration anything this build cannot apply. korrid holds no key
table and reads no settings file; it reports what the runner says as launch
warnings and never rewrites what a person authored.

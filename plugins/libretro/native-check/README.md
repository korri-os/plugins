# Native fantasy-console runners

Each catalogue entry generates an independent plugin with its own selected
RetroArch frontend and core in one closure. No provider is needed for local
files. No game, browser or remote JavaScript evaluator is installed.

| Plugin / runner | System / original format | Native source pin |
| --- | --- | --- |
| `@korri:tic80/tic80` (existing) | `tic80`, `.tic` | nixpkgs `libretro/tic-80` `cef5c5be6658106c9ca7a98b3e9a1e5e2ff30888` |
| `@korri:wasm4/wasm4` | `wasm4`, `.wasm` | `aduros/wasm4` v2.7.1, `92490f261659921d8b724f10b5b842cdf5a0a1bb` |
| `@korri:lowresnx/lowresnx` | `lowresnx`, `.nx` | `timoinutilis/lowres-nx` `63d5988f74e1eea2ecd6ea0445a8ce260b0a9822` |
| `@korri:pzretro/pzretro` | `puzzlescript`, `.pz` | `amberwhitehead/pzretro` `6d859b47092f585a7ec05804c1d51a1676a06531` |

The existing TIC-80 declaration is unchanged. It comes from the publisher's
locked nixpkgs, not the initially researched nesbox release. The new recipes
build only native libretro backends on x86_64/aarch64 **build hosts**. Devices
receive prebuilt closures. Fixed recursive source hashes pin submodules too.

WASM-4 uses wasm3, pinned by its upstream submodule. pzretro uses embedded
QuickJS-NG and its bundled PuzzleScript engine, not a browser. Its recursive
source pins include QuickJS-NG `670492dd342dace0bb7bd6fbfbde8f0bc5651224`,
PuzzleScript `005920fcbd07a4413b8fda4affcd84a178faa0b1`, PuzzleScriptPlus
`d7be4d6f214b2eea2631428375b1dc851824ea80`, libretro-common
`76a3d54feb0ee0ce9d59b90aa24694f3782063d3`, and the unused QuickJS source
`3f81070e573e3592728dbbbd04c84c498b20d6dc`. No `.pzp`, Pattern:Script or
experimental Plus compatibility is promised by the discovery declaration.

## Controls, saves and limits

The existing shared RetroArch declaration owns presentation, input, sound,
save paths and lifecycle. Start alone is game input; Select+Start is native
quit, L3+R3 is the existing native menu command. Korri's host Start behavior
is not changed. Guide remains host-owned. No runner shell interpolates media
or account names. SRAM, states and screenshots use the supplied account/game
save root, never the media folder.

| Core | Persistence and known limits |
| --- | --- |
| TIC-80 | Native persistent memory; serialization is not full interpreter state. |
| WASM-4 | Native disk API persisted as frontend save RAM (uint16 length + 1024 bytes). |
| LowRes NX | Persistent RAM works; no standard savestates or virtual disk integration. |
| pzretro | Native serialized state; large undo histories can be truncated. Compatibility and real-time performance are game-dependent. |

Missing selected files must fail, not open a chooser. The native parsers remain
responsible for syntax errors. These checks do not establish that every malformed
program is rejected at load time; some cores show errors as game frames.
WASM's API is not a security guarantee against native interpreter defects.

## Notices

New cores carry upstream notices under `share/doc/libretro-{wasm4,lowresnx,pzretro}`.
WASM-4 is ISC with MIT wasm3/libretro notices. LowRes NX is zlib with libretro
notices. pzretro and its interpreter/engines are MIT, but its compiled optional
saxmono font has this additional license (preserved with the source notices):

> You may download this font, circulate it und use it freely. You may not alter rename, change copyrights or modify this font in any way.

The pzretro derivation therefore declares `unfreeRedistributable` **in addition
to** MIT. Default-off does not remove the compiled font. Do not describe its
whole closure as MIT-only or modify the font. Runtime licenses do not grant
rights to downloaded games. Original CC0 fixtures are check inputs only.

## Focused checks and live interface

`./check.nix { inherit pkgs contract; packages = selected; }` takes an attribute
set named `tic80`, `wasm4`, `lowresnx`, `pzretro`, containing their generated
plugin packages. It typechecks only those four declarations/helpers. Original
`.tic`, `.wasm`, `.nx`, `.pz` programs exercise actual native cores for 180
frames with input/audio callbacks and nonuniform framebuffer content. The real
packaged frontend then runs exactly the selected content with a bounded clean
exit, native save persistence and separate accounts. Source media is read-only.
Start is injected at the core callback boundary; physical input is untested.

The optional `./probe.nix { inherit pkgs; }` exports a separate build-host tool:

```
korri-libretro-native-probe PLUGIN_PACKAGE ARCHITECTURE KORRID ACQUIRED_CONTENT
```

It passes the selected acquired file to the actual core and to the supplied
`korrid plugin-run`. Bounded frontend arguments use the existing composition
`args.append`; no Core schema or alternate runtime is needed. No game bytes
are transformed. This mode skips fixture-specific SRAM counter expectations.

Both checks run natively on the selected build architecture. Window tests use
Xvfb/software SDL, not target GPU/display/audio. Hardware controls, performance,
Start-to-host handling and return to the real portal remain separate acceptance.
No device operations or publication are authorized by a successful check.

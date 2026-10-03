# Solarus

`@korri:solarus` packages the Solarus 2.1.4 runtime for `x86_64-linux`
and `aarch64-linux`. Build machines compile the engine. Devices receive a
prebuilt native executable and an effect-free TypeScript declaration.
It includes no quests, editor, desktop launcher, ROMs, or game assets.

## Quest discovery and launch

The runner is `@korri:solarus/solarus`. It contributes the `solarus`
system and discovers files ending in `.solarus` in folders already selected
for Korri scanning. These are Solarus's native ZIP-format quest archives.
There is no automatic download or library-folder registration.

Solarus also accepts an unpacked quest directory or `data.solarus.zip` when
an existing library release explicitly points to it. The plugin deliberately
does not claim every `.zip` file or directory. Core's extension-based scanner
cannot distinguish arbitrary ZIPs from quests. Do not rename an unrelated
archive and expect it to become a Solarus quest.

The engine receives the absolute content path as one literal argument.
Spaces, quotes and shell syntax remain part of the filename. No shell parses
quest paths. Emulator cores and Korri launch overrides are rejected.
Use each quest's native settings instead. The plugin does not force fullscreen
or add RetroArch session controls. Display and audio defaults remain unchanged.

The packaged controller database corrects one upstream Linux Xbox 360 entry.
Its four D-pad hat bindings were inverted. This entry also matches Korri's
player seats on the Mini V2. The patch retains all button and stick bindings
and leaves other controller entries unchanged. It does not change A/B actions
chosen by a quest or repair the separate OpenGOAL/Jak input path.

Upstream 2.1.4 accepts quest formats 1.5, 1.6, 2.0 and 2.1 at its version gate.
That is not proof that every quest works. Older quests can still depend on
removed behavior, unavailable assets, or a different engine fork.

## Saves

The owner chose separate saves per Korri account. The launch declaration sets
`HOME` and cwd to the existing `PluginLaunchInput.accountRoot`; Core creates
that directory if needed. Solarus keeps its native `.solarus` directory there.
Each quest supplies its own `write_dir` and save filenames. The plugin does
not define another save layout or change quest data.

The plugin uses the account root that Core supplies. It does not add account
selection to Core. The checks exercise two distinct supplied roots. Launches
that receive the same root share that account's native save storage.

This also keeps native `error.txt` logging inside account storage rather than
the content folder. The plugin does not set `XDG_STATE_HOME`: upstream's Linux
save code uses PhysFS's user home, not that variable.

Existing desktop saves are not imported, deleted, or rewritten. Account
isolation does not separate two quests that reuse the same native `write_dir`
within one account. It is not an operating-system sandbox for quest scripts.
Only run quests you trust. Simultaneous launches using the same account and
quest retain upstream's save behavior; this plugin adds no save-file locking.

## Build and test

Run on a build machine, never a target device:

```sh
nix build --no-link .#packages.x86_64-linux.korri-plugin-solarus
nix build --no-link .#packages.aarch64-linux.korri-plugin-solarus
nix build --no-link .#checks.x86_64-linux.korri-solarus-plugin
nix build --no-link .#checks.aarch64-linux.korri-solarus-plugin
```

The checks use the actual packaged engine and Core's production
`plugin-launch` executor. They cover the generated manifest, strict launch
types, host seed/declaration validation, literal arguments, unsupported
overrides, native ELF architecture, archive/directory launch, persistent
save/reload across processes, two supplied account roots, and preservation
of desktop saves and quest bytes. An SDL lookup test loads the installed
controller database and checks D-pad, button, and stick bindings for the
Linux Xbox 360 GUID and four observed Korri-seat GUIDs. It fails on the original
inverted database. The test quest uses native save APIs and contains no
third-party assets.

A test-only launcher adds upstream's `-no-video` and `-no-audio` flags. These
headless checks do not establish display output, audible sound, physical
controller behavior, or compatibility with any complete game. Missing and
invalid archives are checked for upstream's diagnostic and unchanged saves.
Solarus itself returns exit code zero when no quest is found. That exit code
alone does not prove a successful game launch.

These checks do not publish binaries, configure trust, or install on devices.

For an interactive engine test on a build machine with a separate existing,
writable `TEST_HOME` and an absolute `QUEST` path:

```sh
nix build .#solarus --out-link result-solarus
HOME="$TEST_HOME" ./result-solarus/bin/solarus-run "$QUEST"
```

This invokes the standalone engine, not Core's account provisioning or launch
callback. It requires the build machine's normal graphics/audio setup.

## Packaging and licenses

`package.nix` reuses the pinned nixpkgs recipe and pins upstream `v2.1.4` with
the source hash from nixpkgs' newer recipe. The repository-wide lock is not
updated. The output retains upstream's GPL license and attribution document
under `share/licenses/solarus/`. Code is GPL-3.0-or-later; upstream assets carry
CC-BY-SA licenses. Quests have separate terms and are not included.

The pinned upstream engine source remains available through the package's `src`:

```sh
nix build .#solarus.src --out-link result-solarus-source
```

The local `xbox360-dpad.patch` and build recipe are also part of the patched
engine's corresponding source. Any binary publication must satisfy the
applicable source and asset license obligations. Packaging is not approval
to redistribute a quest.

## Installation boundary

This official producer declares only `@korri:solarus`. It provides no alias
for a previous publisher identity. The port does not migrate an installed
plugin, import saves, configure publisher trust, or install on a device.
Headless check coverage is not device or real-quest acceptance.

Installation still needs an approved delivery route and exact-package
approval. The cache must match the device's existing approved `@korri`
binding. The package must be the exact plugin store output, not the engine
or flake URL. A previous publisher's binding does not approve this identity.
Missing artifacts or signatures must fail without enabling local or remote
builds on the device. Keep normal plugin permissions and signature checks.

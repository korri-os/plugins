# Bitsybox

`@korri:bitsybox` provides the native SDL2 runner
`@korri:bitsybox/bitsybox` for Bitsy `.bitsy` text data, as named in upstream
`doc/MANUAL.txt`. It includes no games, browser, HTML extractor, chooser, or tune
demo. Acquisition is a separate blocked contract, not part of this runner.

## Native launch

Core's existing `launch.prepare` treaty supplies one selected absolute
`contentPath`. The effect-free TypeScript source returns that path as one literal
argument. It refuses other runners, emulator cores, launch overrides, relative
paths and NUL bytes. Core provisions the supplied account root as cwd, following
Solarus. This is not a new save layout. The engine only reads content; it creates
no games directory, config file, or native saves. It never copies games beside
the executable and never changes cwd to the executable or media directory.

The explicit `single-file.patch` changes upstream's entry point. It opens the
selected regular file before SDL, reads it without a fixed path buffer, rejects
empty/NUL-containing/unreadable files, and checks data with upstream's embedded
world parser. A parsed avatar and its starting room must exist. This is a basic
playability check, not a complete validator or a sandbox for malicious data.
The engine runs the retained bytes, so it does not reopen a different file after
validation. No shell parses filenames. Long paths and spaces are supported up
to the operating system's limits.

Keyboard and SDL gamepad mapping remain upstream's: arrows/WASD or D-pad move;
space/enter or face buttons confirm; Alt+Enter toggles fullscreen. Escape,
Ctrl+R, or gamepad Start now end the selected-file session instead of reopening
the chooser. A native reset/end also exits. Fullscreen and rendering defaults
remain upstream's; no extra UI is added.

## Licensing and publication block

**Bitsybox is not unrestricted open-source software. Publication requires
separate eligibility and redistribution approval and remains blocked.**

The pinned Bitsybox source uses the Anti-Capitalist Software License v1.4.
Eligible users must be individuals laboring for themselves, nonprofits,
educational institutions, or organizations that share profits with all members
and let nonmembers set their labor cost. Organizations with owners must make all
owners workers and all workers owners, with equal equity and/or equal vote.
Organizations must not be law enforcement, military, or work for or under them.
The copyright and permission notice must accompany copies or modified versions.
These restrictions also affect use, not only redistribution. Packaging does not
establish the publisher's or any recipient's eligibility.

The output preserves exact notices under `share/licenses/bitsybox/`:

- `Anti-Capitalist-1.4.txt`: the pinned source's root license.
- `Bitsy-MIT.txt` and `Bitsy-CREDITS.md`: the embedded Bitsy engine's MIT notice
  and credits from `le-doux/bitsy` commit
  `17d5b2acb704a904121e23e0d3639237769763f7` (the license's last change).
- `Duktape-notices.txt`: Duktape 2.6.0 MIT license and author notices, extracted
  without alteration from the bundled C source.
- `upstream-res-LICENSE.txt`: upstream's additional resource license, retained
  without treating it as permission to override the root license.

SDL2 remains a separate dynamically linked dependency with its own notices.
No third-party demo game is shipped. `fixture.bitsy` is original test data in
Bitsy's native format, grounded in the inspected upstream `hello.bitsy` grammar;
it is not installed in either shipping output.

## Focused checks (build hosts only)

```sh
nix build --no-link .#packages.x86_64-linux.korri-plugin-bitsybox \
  .#checks.x86_64-linux.korri-bitsybox-plugin
nix build --no-link .#packages.aarch64-linux.korri-plugin-bitsybox \
  .#checks.aarch64-linux.korri-bitsybox-plugin
```

The check covers strict launch types, real host admission and `plugin-run`,
negative launch inputs, native ELF architecture, pre-SDL invalid-file refusal,
bounded startup of original native data, paths longer than 256 bytes with shell
characters/spaces, keyboard menu-exit, and unchanged media bytes/directory.
It uses Xvfb on build hosts, never target devices. Physical gamepad, display,
audio and complete-game acceptance remain separate. No publication, image pin,
installation, device changes, or acquisition permission changes are authorized.
The standalone package is `bitsybox`; its source is available as `bitsybox.src`.

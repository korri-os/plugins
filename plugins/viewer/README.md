# Korri viewer

`@korri:viewer` is Korri's own stream viewer for Linux, as a removable,
permission-approved plugin (korri-os/korri ADR 0061, issue #435). Its code is
`clients/viewer` in the Korri repository, at the pinned `korri` input. This
repository builds it with its own package set. It is the only client since
2026-11-24 (Core ADR 0099). A device without it cannot stream.

Only the PC picture paths (X11 VA-API and the SDL software fallback) have a
proof. Korri's aarch64 `v4l2request` path has none on a bench device yet
(ADR 0063), so only `x86_64-linux` exports the plugin. No publication,
deployment or hardware acceptance follows from these package checks.

## What the plugin declares

| Name | Kind | What it is |
| --- | --- | --- |
| `viewer` | file | `bin/korri-viewer`, run by korrid in its exact-launch viewer unit |
| `mapping` | file | The controller database that korrid passes with `-mapping` |
| `identity-bootstrap` | file | Prints the public client certificate (below) |
| `treaty` | file | The viewer's wire contract, `contracts/generated/viewer.ts` |
| `viewer` | package | The viewer, GPL-3.0-only on x86_64: GPL-3.0-or-later code with nightjar-core, which is GPL-3.0-only |
| `source` | package | Its corresponding source (ADR 0059) |
| `korri-viewer-setup` | service | Creates the client identity directory |

### The version check

korrid compares `files.treaty` with its own copy of
`contracts/generated/viewer.ts`, byte for byte. Equal bytes: korrid uses this
viewer. Other bytes: korrid refuses the plugin and names both SHA-256 hashes.
No `treaty` file: korrid refuses the plugin and names only its own hash.
Any refusal is the start's error; no fallback client runs.

Cost: the treaty file holds the wire types only. A change to the launch
arguments, or to behaviour that keeps the wire types, is not caught before
start. The viewer then fails at start. If that happens, put the launch
arguments into the contract crate, so that the same check covers them.

### Corresponding source

`packages.source` is `share/korri-viewer/korri-viewer-source.tar.xz`. It holds
the Korri files that build the viewer, with its Nix recipe and its vendored
network core nightjar-core (GPL-3.0-only), the C network core
`moonlight-common-c` with its ENet, and the Rust crates of its `Cargo.lock`.
`BUILDING.txt` in it says how to build, with the cargo features of the
binary. It is in the same closure as the binary, so each archive that carries
the viewer carries its source too.

### Notices

The viewer package holds `share/licenses/korri-viewer/NOTICES.txt` beside
its `LICENSE` (korri-os/korri#521): the licences of what its recipe builds in
that other people wrote, for the binary's own features. The source archive
holds the same file as `licenses/NOTICES.txt`. The native check reads both.

### Network core and Rust parts

The viewer streams with nightjar-core, opens a Rust X11 window, and draws
pictures with bars through its Rust EGL presenter (a picture that fills the
window still goes through `vaPutSurface`, and the SDL fallback uses neither
Rust picture part): each measured equal to the C it replaced (korri-os/korri
ADR 0062, #391 steps E and F). It also plays the sound through its Rust
audio output, which became the default on the owner's call of 2026-11-18,
ahead of a quiet measurement (ADR 0062's amendment). `-networkcore c`,
`-audiooutput c`, `-eglpresenter c` and `-x11window c` keep the C. This
plugin passes none of these options, so korrid's launches take the
defaults. With nightjar-core the binary is GPL-3.0-only.

### Client identity

The setup unit creates `/home/korri/.config/moonlight`, mode 0700, owned by
`korri`. It preserves the existing protocol identity. korrid hides this path
from game units; certificate provisioning is unchanged. The viewer reads
`client.pem` and `key.pem`. Plugin removal keeps the identity directory.

`identity-bootstrap` is Moonlight's helper with one change: the viewer makes
its identity on `pair`, before it reads the server pin, so the helper runs
`korri-viewer pair` with an empty pin and the viewer stops before any host.
The viewer writes no `uniqueid.dat`. A `uniqueid.dat` that Moonlight left in
the directory is checked like the other files.

## Settings

The viewer owns `settings.ts` and keeps the existing schema, revision,
defaults, diagnostics and native arguments under `@korri:viewer/viewer`.
`settings.test.mts` checks all 15 leaves, rendering, validation and display
fallbacks. The source was moved intact from the removed plugin at
`e3343461a76eff0aa0e8ef7b8a8761d3c359918a`, changing only the runner ID.
Stored settings for the removed plugin do not carry over (Core ADR 0061).

## Checks (build machines only)

```sh
nix build --no-link .#checks.x86_64-linux.korri-viewer-plugin-native \
  .#checks.x86_64-linux.korri-viewer-picture \
  .#checks.x86_64-linux.korri-viewer-io \
  .#checks.x86_64-linux.korri-viewer-lifecycle
```

`korri-viewer-plugin-native` runs Core's admission, the identity helper
against a fixture and against the real viewer, the treaty bytes, the source
archive and the settings comparison. `korri-viewer-picture` and
`korri-viewer-io` are Korri's own checks of the binary.

`korri-viewer-lifecycle` is Korri's `services/korrid/viewer-vm-test.nix`, run
with these plugins on a cold NixOS guest. The plugin host installs both
viewers. korrid's own viewer selection starts this viewer against a private
Sunshine in the guest, observes and backgrounds it through its socket, stops
it, falls back to Moonlight when it is disabled, and refuses this plugin
rebuilt with one byte of its treaty changed. The federated path, the peer
request that makes korrid start a viewer in a real stream, is not part of
that test. The aka binary proof covers it first, then the owner's one game
after the autonomous proof (ADR 0063).

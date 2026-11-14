# Korri viewer

`@korri:viewer` is Korri's own stream viewer for Linux, as a removable,
permission-approved plugin (korri-os/korri ADR 0061, issue #435). Its code is
`clients/viewer` in the Korri repository, at the pinned `korri` input. This
repository builds it with its own package set. korrid uses it in place of
`@korri:moonlight` when it is installed and enabled. A device without it keeps
Moonlight.

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
| `viewer` | package | The viewer, GPL-3.0-or-later |
| `source` | package | Its corresponding source (ADR 0059) |
| `korri-viewer-setup` | service | Creates the client identity directory |

### The version check

korrid compares `files.treaty` with its own copy of
`contracts/generated/viewer.ts`, byte for byte. Equal bytes: korrid uses this
viewer. Other bytes, or no `treaty` file: korrid refuses the plugin, names
both SHA-256 hashes, and keeps Moonlight as the viewer. Without Moonlight the
refusal is the start's error.

Cost: the treaty file holds the wire types only. A change to the launch
arguments, or to behaviour that keeps the wire types, is not caught before
start. The viewer then fails at start. If that happens, put the launch
arguments into the contract crate, so that the same check covers them.

### Corresponding source

`packages.source` is `share/korri-viewer/korri-viewer-source.tar.xz`. It holds
the Korri files that build the viewer, with its Nix recipe, the network core
`moonlight-common-c` with its ENet, and the Rust crates of its `Cargo.lock`.
`BUILDING.txt` in it says how to build. It is in the same closure as the
binary, so each archive that carries the viewer carries its source too.

### Client identity

The setup unit creates `/home/korri/.config/moonlight`, mode 0700, owned by
`korri`, exactly as `@korri:moonlight` does. The two plugins share it: korrid
hides this one path from game units, its certificate provisioning is
unchanged, and the viewer reads Moonlight's `client.pem` and `key.pem`. A
device that installs both keeps one identity. Removal keeps the directory, as
Moonlight's does.

`identity-bootstrap` is Moonlight's helper with one change: the viewer makes
its identity on `pair`, before it reads the server pin, so the helper runs
`korri-viewer pair` with an empty pin and the viewer stops before any host.
The viewer writes no `uniqueid.dat`. A `uniqueid.dat` that Moonlight left in
the directory is checked like the other files.

## Settings

The viewer keeps Moonlight's settings (#435): the same schema, defaults,
diagnostics and arguments, under its own runner `@korri:viewer/viewer`. The
plugin source has no copy of them. `nix/default.nix` builds `settings.ts`
from `plugins/moonlight/settings.ts` with only the runner ID changed.
`settings.test.mts` compares the two plugins' answers for the same values and
displays. Settings stored for `@korri:moonlight` do not carry over (ADR 0061).
See `plugins/moonlight/README.md` for the table.

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

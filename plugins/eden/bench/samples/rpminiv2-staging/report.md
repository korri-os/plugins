# Mini signed staging and discovery — 2026-10-23 UTC

**Personal Eden is enabled and SMO is admitted. No Eden launch or performance
result yet at this checkpoint.**

SSH first succeeded at **14:23:17 UTC**, before the six-hour deadline. The
first idle watch was lost in a supervisor restart. Recovery found no owned
session and no native Eden INI/data directory; there was nothing from this
worker to restore. Cemu was active at 14:45, so this worker yielded. The fresh
watch reached 15 minutes empty at 15:02, with korrid PID 1925 stable. Every
inspection/install/enable step used an immediate process/PID recheck. Cemu
appeared again at 15:13, after content transfer completed; no Eden session
existed to stop. The next fresh 15-minute idle window completed at 15:54.

## Admission and trust

[Owner verification](owner-proof.json) checked the actual signed statement's
NIP-01 hash, BIP340 signature, kind and owned status. Owner fingerprint
`<account>` matches the existing account. No identity was created or
re-keyed. Native Eden profile discovery still waits for Eden's first launch.

The actual Mini personal binding is
`file:///var/lib/korri-private-cache.h6odJOu2/cache`, **not Odin's cache path**.
Its existing full public key matches the host's approved personal signing key.
The official binding was not changed. `require-sigs=true` remained enabled.
Signature-checked `nix copy` delivered the exact personal plugin, bench 0.2.2
and prebuilt `xwd` screenshot tool. No device compiled or dispatched a build.

[Inspect](inspection.json), exact-approval [install](install.json), enable and
[Enabled status](plugin-status.json) passed for
`/nix/store/24yf1xbs5213vqx2if3qlqsz1cz6qqfz-korri-plugin`. This is the Odin-tested
candidate whose sole source delta is the personal runner literal; see the
[host byte proof](../rpminiv2-preparation/host-source-proof.json). It is not an
official publication. The two custom cache records were added without changing
any of the **1,112** existing `.narinfo` records; before/after hashes remain in
host scratch. Dependencies arrived through signed `nix copy`, not a second
full cache on this nearly full device.

## Content and access

[Staging proof](staging-proof.json) records the account-local destinations and
sizes. SMO's read-only source, host copy and Mini copy match. All **167**
firmware files, **246,074,368 bytes**, and **214** descendant directories match,
including empty directories. Keys were copied only to this account's native
Eden keys directory. Private permissions and runtime ownership were checked;
no key contents or digests were reported.

The existing account is the one derived from the verified statement and Core's
account-root producer. Firmware is under its `.local/share/eden/nand/`, keys
under `.local/share/eden/keys/`, and the two-file recommended B520 save payload
is still under `.local/share/eden/korri-staging/smo-save/` in the same native
staging layout as Odin. It has **not** been bound to a Mini Eden profile or
loaded. No guessed `saves/<id>` was created before admission.

SMO is at the existing `/var/lib/korri/games/switch/` convention. The new folder
and game grant runtime `korri` and service `korrid` the required read/traverse
access; both read probes passed before discovery. Content is not executable.
After delivery and staging, `/dev/sda22` had **2.2 GiB available**. No existing
content was deleted and no garbage collection, swap/zram or system update ran.

## Offline discovery with the socket accounted for

Unlike the Odin attempt, **both** `korrid.service` and
`korrid-control.socket` were stopped during the offline CLI. Both had been
active and both were restored active afterward. The CLI ran as service user
`korrid`, using the existing storage/private roots. Protected device snapshots
of `device.yaml`, `catalog/library.yaml` and all discovery records bracket each
operation at `/var/lib/korri/eden-bench-staging/mini-20261023/discovery/`.

| Operation | Units | Hashed bytes | Added games | Removed locations | Diagnostics |
|---|---:|---:|---:|---:|---:|
| [pair Switch folder](ARCHIVE.sha256) | 38 | 5,611,009,601 | 1 | 0 | 0 |
| [rescan](ARCHIVE.sha256) | 38 | 0 | 0 | 0 | 0 |

[MainPID before](ARCHIVE.sha256) and [after](ARCHIVE.sha256) were both
**0** throughout this daemon-off interval; there was no socket reactivation.
[Semantic proof](discovery-proof.json) passes: all **76** pre-existing library
records and all existing device/discovery values are equal after parsing.
Only the Switch source/storage and SMO game/location/hash/origin/path were
added. The second rescan is semantically idempotent.

The old Odin proof initially rejected the new location's observed
`discovery.first-seen-at`. This was not an existing-record change. The actual
Core producer is `config/mod.rs:733–734` and
`discovery/reconcile/change.rs:692`; the new SMO record has
`2026-10-23T15:56:26Z`. The revised proof checks that exact observed value and
still requires every existing record to be equal. No schema or timestamp
exception for existing data was invented.

The admitted game is `super-mario-odyssey-0100000000010000-v0` and the admitted
runner is `@<publisher>:eden/eden`. The real localhost RPC idle proof and
`system.health` passed before the offline operation. A new stable-PID/idle
window is required before the first launch after daemon restoration.

## Remaining acceptance

Save profile binding/capture, first picture, silent Eden audio stream,
NCE/Dynarmic comparison, all measured ladder rungs, soak and temporary-setting
restoration remain pending. Native INI, performance settings and modifiers have
not been changed by this worker. The existing device Gamescope modifier is
already enabled; the observed panel output is 1240×1080 after rotation.
Speaker volume was observed at **0.00 [MUTED]** and was never changed.
Bubblewrap is the known Core gap #184, not yet a new Eden launch observation.

No push, merge or publication occurred. No firmware/boot-chain/GPT partition,
identity or trust policy was changed.

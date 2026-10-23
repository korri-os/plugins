# Odin content staging — 2026-10-23 UTC

All device steps first checked `pgrep -a -f 'cemu|eden|bench'`. The initial
Cemu run was busy, so this worker waited. Transfers began only after it ended.
No Eden plugin was installed and neither Eden nor SMO was launched. Mini was
left untouched in this stage by the supervisor's final instruction.

## Verified account, not a guessed directory

The actual signed statement is `/var/lib/korrid/identity/owner.event.json`.
Verified its NIP-01 event hash and BIP340 signature on <build-host> with coincurve 21.0.0;
required kind 30078 and status `owned`. Only this public statement was read,
not the device's private keys. Verified statement ID:
`<owner-statement-odin>`.

Owner public fingerprint: `<account>` (the full public identity is
also the exact account-directory component below).
Bound device public fingerprint: `<device-odin>`.

Core `services/korrid/src/host/mod.rs:488–495` loads that statement's owner;
`saves/mod.rs:47–59` derives `<storageRoot>/users/<owner>`;
`launcher/linux_plugin.rs:191–207` uses that account root and appends
`saves/<encoded playable_id>` for a game's save root. The running device's
storage root is `/var/lib/korri`. Existing account directory and its ownership
were checked, not inferred from the local signer or another device.

The local signer's public fingerprint differed at inspection (`<signer>`).
It was **not** used to guess an account. No identity, statement, signer or key
binding was created, changed or re-signed. The later real wl4 unit journal for
launch `f927719fbb1e98399c1ebb5f31b9ef86` independently confirms that korrid
supplied this same accountRoot to the runner after the daemon restart.

Define the following exact paths for the tables:

```text
ACCOUNT=/var/lib/korri/users/<account>
EDEN=$ACCOUNT/.local/share/eden
```

## Content present

| Data | Destination | Size / verification |
|---|---|---|
| SMO | `/var/lib/korri/games/switch/Super Mario Odyssey [0100000000010000][v0].nsp` | 5,611,009,601 bytes; source/destination SHA256 matched |
| prod.keys | `$EDEN/keys/prod.keys` | 14,612 bytes; mode 600 |
| title.keys | `$EDEN/keys/title.keys` | 1,292 bytes; mode 600 |
| User firmware | `$EDEN/nand/system/Contents/registered/` | 214 directories, 167 regular files, 246,074,368 regular-file bytes; all file hashes matched source |
| Converted save payload | `$EDEN/korri-staging/smo-save/user/save/0000000000000000/<eden-profile>/0100000000010000/` | Common.bin 1,036 bytes; File1.bin 2,097,164 bytes; source bytes matched |
| Staging explanation | `$EDEN/korri-staging/smo-save/README.txt` | 405 bytes |

Keys came directly from the user-supplied host paths:
`/home/<user>/.local/state/korri-eden-test-keys/prod.keys` (14,612 bytes)
and `title.keys` beside it (1,292 bytes). They were copied **only** to the
account's Eden keys directory. No key contents, checksums or diagnostic dumps
were logged or committed. Native data and key files are owned by verified
runtime UID/GID 1000:1000 (`korri`); key files have mode 600.

Firmware and SMO came only from the requested read-only `<user>@<content-host>` source.
No firmware was downloaded. The source's NCA directory layout, including its
empty directories, was preserved rather than treating 214 entries as 214
regular files. Firmware loading/decryption is not yet tested.

## Storage and save admission still pending

The `games/<system>` convention is grounded in Core's
`services/korrid/src/catalog_migrate.rs:372–386` (`root.join("games").join(system)`)
and the actual device's `device.yaml` GBA storage root. System `switch` is from
forge's actual Eden declaration. No catalogue or device.yaml record was edited.

The current device has **no Switch source/storage pairing or SMO playable**.
Thus this is a verified library-area file, not proof of admitted discovery.
Core requires an enabled declaration before source pairing
(`discovery/sources.rs:validate_pairing`). In the next stage, enable the plugin,
use the existing discovery pairing/rescan operations as needed, and obtain the
real playable ID/saveRoot. Installing a declaration alone is not proof that a
new unpaired folder is scanned.

The supervisor explicitly approved native Eden-data save staging because no
real SMO saveRoot exists before admission. No guessed `ACCOUNT/saves/<id>` was
created. After actual admission, move the payload beneath the real
`saveRoot/nand/user/save`, rebind the source profile to the actual Eden profile,
verify loading, then delete this staging copy. No profile or Bonneton location
has been invented or validated.


## First light follow-up — 2026-10-23 UTC

The approved personal test plugin `@<publisher>:eden` is enabled. Core admitted
SMO as `super-mario-odyssey-0100000000010000-v0`. Its real saveRoot, confirmed by
the actual launch input, is
`$ACCOUNT/saves/super-mario-odyssey-0100000000010000-v0`.
The staged `user/save` tree was moved into `saveRoot/nand/user/save`; the old
staging tree and its README were removed. The source profile directory remains
`<eden-profile>`; no profile rebind, game save load or relaunch
persistence is claimed. The native `save_directory` equals `saveRoot/nand`.

Correction to staging readiness: runtime access alone was insufficient. The
root-owned Switch folder/NSP admitted `korri` but not service user `korrid`.
Added only named `korrid` read/traverse access on that folder and read access on
SMO. The moved save also retained ACL masks that excluded the service. Added
named `korrid` directory read/write/traverse/default access and file read/write
access, with corresponding masks, only beneath this game's moved save tree.
The first launch had reproduced `SavesUnavailable` before that save correction.
Both users can read the content; korrid can traverse/read the imported save.
Keys stayed unchanged at mode 600 and the previously recorded sizes.

[The stage report](../samples/odin2portal-firstlight/report.md) retains the ACL
before/after evidence, discovery proof, install receipt and actual saveRoot.
The required no-picture graphics stop ended launches: Eden selected llvmpipe,
not Turnip. Launch settings were restored. No payload was committed.

# Public evidence redaction

Public copies replace real account/person and device fingerprints, owner-statement
IDs, Eden profile UUIDs, private host/user names, MACs/BSSIDs and serials with
stable placeholders (`<account>`, `<device-odin>`, `<eden-profile>`, `<bssid>`,
`<mac-N>`, `<builder-1>`, and similar). Identifying image metadata is removed from derivative copies without
changing the depicted scene. The unchanged Mini PNG contains only a generic
xwdump comment and capture dates. Documented USB links 10.42.4.1 (Odin), 10.42.3.1 (Mini)
and loopback 127.0.0.1 remain. Software version numbers are not IP addresses.

Placeholders are not executable paths or real signing-key names. Substitute local
values when following an administrative example. These are redacted copies,
not byte-identical raw evidence. Originals were preserved privately before any
redaction, under `~/.local/state/korri-eden-evidence/` (directories mode 700).
No private original belongs in a published repository.

This commit redacts the current tree. Earlier local Git history still contains
original evidence; publishing that history requires a separate history scrub or
publishing a clean snapshot. No history rewrite or push is performed here.

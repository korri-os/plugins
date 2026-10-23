# Exact stop can briefly report recovery blocked — 2026-10-22 campaign

**Verified:** a normal korrid exact-stop RPC stopped the existing Mega Man Arena
Proton runner, but returned `HostRecoveryBlocked`. No administrator reset was
needed. A later read-only status call let korrid reconcile its own failed unit.

- Updated Odin system generation 8, korrid
  `/nix/store/nvs92ijqg09cranbzg1d0f2whybvvr32-korrid-0.0.0/bin/korrid`.
- Launch: `92521d6a707008dc4af8607fd77dace2`, game `mega-man-arena`, runner
  `@<publisher>:mega-man-arena/proton`.
- The probe used `app.session.stop { expectedLaunchId }`, not direct signals.
  At 2026-10-23 00:30:56 UTC, systemd stopped that exact unit and reported wrapper
  exit status **143**, result `exit-code`.
- A subsequent status returned terminal `HostLaunchFailed` for the same ID.
  No game/acquire unit, FEX/Wine/game/Gamescope process, or populated game cgroup
  remained. `/var/lib/korrid/host-session/` was empty. `active.json` had already
  been consumed, so there was no journal file to copy.
- The input probe stopped its own empty InputPlumber composite **after** the
  stop RPC. Its policy stayed false, CompositeDevice0 retained its source paths,
  and seat P1's device number, keys and axes matched before/after.

## Inferred cause from core at `4e34b8a9e`

`services/korrid/src/host/session_state.rs::observe_stop` (about line 2390)
turns a final `backend.state` error into `RecoveryBlocked`, including
`UnitFailed`. `refresh_recovery` later calls `recover`; `recover_failed_unit`
(about line 1737) clears the failed unit, completes the save/play snapshot and
consumes the active journal, then retains the terminal failure.

This matches the observed stop → wrapper 143 → transient block → status recovery.
The evidence does not prove every internal race. It does show that the bench
used the normal stop path, not an identity/journal workaround.

## Smallest resolution and follow-up

No manual resolution was required. Bench did **not** stop/reset another unit,
edit a journal, restart korrid, change a generation, or reboot.

The bench now records the original stop warning and polls **read-only** status
for up to 10 seconds (plus bounded I/O). Cleanup succeeds only after korrid
leaves recovery-blocked state **and** systemd and actual cgroups prove idle.
A block that does not clear fails the run. This is a diagnostic mitigation, not
a core fix. Normal wrapper stops can still trigger the core defect.

Suggested issue for the parent to file at Land: distinguish a verified,
expected termination of an exactly owned wrapper (143 here) from an uncertain
recovery identity. Do not blanket-ignore `UnitFailed`; a real crash or unknown
unit must retain the existing protection. Cost: the distinction needs backend
and stop-race tests, not only a new client-side retry.

Private evidence on zao (not published):

- `/tmp/cemu-bench-evidence/odin-recovery-probe.txt`
- `/tmp/cemu-bench-evidence/odin-recovery-journal.log`
- `/tmp/cemu-bench-evidence/odin-recovery-files.txt`
- `/tmp/cemu-bench-evidence/odin-visible3/{launch.json,cleanup.json,input-observer.json}`

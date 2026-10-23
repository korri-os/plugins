# In-game save proof

Status: unproven: Save route unproven: no changed game_data.sav hash and mtime within 30 seconds; report: /var/lib/korri/cemu-bench-staging/gameplay-gate-20261023-final/save-01/write/report.md

Save safety: restored and verified.
Original head: `sha256:512aad8778239ec7be7470a5516e8fa28eb3f413844c1f4dc43a02e5287d7f55`; restored continuation: `sha256:2eb606e78df651f093e905e14d3ea0269c23fb158ea501e6eed17c5e98ff74ce`.
Payload equal: True; original in ancestry: True.
Additional snapshots before restore: 1; restore snapshots: 1.
See private `save-safety.json` for payload verification and backup. Additional records can include peer arrivals.
Risk: bench and restore snapshots still enter real history and count toward retention. No supported guest/skip-snapshot launch exists.

Run: write
## Gameplay gate

Offsets are seconds after launch starts.
- title at: 9.017700470999443
- loading at: 27.01116521899985
- gameplay at: 47.600802106999254
- end gameplay at: not observed

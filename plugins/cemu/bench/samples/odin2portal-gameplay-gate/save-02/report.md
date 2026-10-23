# In-game save proof

Status: unproven: Save route unproven: no changed game_data.sav hash and mtime within 30 seconds; report: /var/lib/korri/cemu-bench-staging/gameplay-gate-20261023-final/save-02/write/report.md

Save safety: restored and verified.
Original head: `sha256:2eb606e78df651f093e905e14d3ea0269c23fb158ea501e6eed17c5e98ff74ce`; restored continuation: `sha256:989fc95bcaf0d9aae12b549f50b3fafdefd394640724f6448032ca7e06eb3d21`.
Payload equal: True; original in ancestry: True.
Additional snapshots before restore: 1; restore snapshots: 1.
See private `save-safety.json` for payload verification and backup. Additional records can include peer arrivals.
Risk: bench and restore snapshots still enter real history and count toward retention. No supported guest/skip-snapshot launch exists.

Run: write
## Gameplay gate

Offsets are seconds after launch starts.
- title at: 10.992550883999684
- loading at: 28.732882972999505
- gameplay at: 50.099039446999996
- end gameplay at: not observed

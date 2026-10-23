# Odin gate findings — 2026-10-23

## Proven boundary

The device executed the signed 0.2.1 tool. The existing library route reserved
and started `wl4` through korrid as launch
`f927719fbb1e98399c1ebb5f31b9ef86`. Its actual launch input confirms the same
verified accountRoot used for Eden content staging. RetroArch PID 18425 and
its exact cgroup were observed.

The authoritative unit journal contains `"modifiers":[]` and a direct
RetroArch plan. No Gamescope process existed in that session. The collector
refused to measure a different pipeline and stopped only its exact launch.
The unit journal records exit **143**, consistent with this deliberate stop;
this is not evidence of a spontaneous emulator startup crash. The journal also
contains a GameMode D-Bus warning; it does not establish the cause of the
missing modifier.

No observer started and no FPS/telemetry samples were produced. The empty
`present.csv` and `observer.log` are preserved. `cleanup.json` proves the exact
cgroup and owned processes were empty, but the stop/reconciliation RPC returned
`HostRecoveryBlocked`. This is **not** a fully passed device benchmark.

## Which layer disables Gamescope?

Read-only observation at **2026-10-23 02:08:39 UTC**, after waiting for the
parallel Cemu bench to finish. Evidence: `final-diagnostics.json`.

| Modifier layer for wl4 | Gamescope record |
|---|---|
| device (`device.yaml`) | absent |
| runner `@korri:mgba/mgba` | absent |
| system `gba` | absent |
| game `wl4` (`catalog/library.yaml`) | absent |

There is **no explicit `enabled: false` layer**. There is no opt-in at any of
the four layers, so Gamescope resolves disabled by default. The game-layer
`enabled: true` seen in the earlier read-only snapshot is no longer present.
The current files alone cannot identify who removed it or precisely when.
Nothing in this workflow edited any of these settings.

Grounding, verified identical in Core `4e34b8a9e` and the inspected worktree:
`src/config/modifiers.rs::resolve` folds device → runner → system → game;
`src/launcher/linux_plugin.rs` includes only modifiers whose `enabled` is
`Some(true)`. `src/config/snapshot.rs::initial_document` seeds the product's
initial modifiers only when creating a device document, not as a fallback for
an existing one. The CPU/GPU launch-settings read RPC does not itself expose
the modifier cascade, so the four actual settings-file records were checked.

## Is recovery still blocking new launches?

At the same read-only observation, `app.session.status` returned:

```text
SessionCompleted: host launch 9e0ad09294554e745129f0685dbecaaa completed
```

It did **not** return `HostRecoveryBlocked` or an observation failure. The
current state is not a recovery refusal. Core permits a new prepare from
`Completed`, `Failed` or `NoActive` (`host/session_state.rs:1260–1284`); no new
launch was attempted to test that after the instruction to stop. A later Cemu
session had already run after this workflow's failure, so the stop-time block
did not persist across those subsequent operations.

This worker performed no manual state clearing, settings change or daemon restart.
Normal status observation can make Core retry its own recovery
(`refresh_recovery`/`recover`); that is its existing read-RPC behavior, not a
manual repair. If `HostRecoveryBlocked` returns, its generic producer says:

```text
host recovery identity is missing, tampered, or ambiguous; preserve all game units and require administrator resolution
```

Recovery requires a consistent durable active record/native unit observation
and successful completion processing. The earlier generic error alone does
not identify the failing predicate or a safe manual repair. Do not delete a
record, reset a unit, or restart the daemon merely to hide it. No such action
was needed for the currently observed `SessionCompleted` state.

## Preserved journal

`session.log` contains all **9** lines for
`korri-game-f927719fbb1e98399c1ebb5f31b9ef86.service`, including the actual
composition and the exit. `korrid-launch.log` is empty: the brain's journal
query for this exact ID returned **zero** matching lines. That absence is
reported, not replaced by another launch's logs.

The supervisor moved device FPS proof to the Odin stage, where SMO's own
game-layer settings are in scope. `wl4` is not this workflow's configuration
to change. Mini remains untouched; its content staging moves to its own stage
after the Cemu workflow finishes.

# odin2portal: Eden bench

Status: FAILED: RPC failed: SavesUnavailable
Game `super-mario-odyssey-0100000000010000-v0`; runner `@<publisher>:eden/eden`; launch `9558a987340dd810bd438f446b75b15d`.
Booted system: `/nix/store/xqbqdwrn3ws25z9dpnhb3nwl47366m8q-nixos-system-odin2portal-sd-card-26.11.20260923.4975466`; kernel `7.2.0`.

## Measurement

Source: game-window X11 Present CompleteNotify/Pixmap; Skip excluded. Neither Eden's counter nor MangoHud.
XRes server-owned PID selects only this renderer's windows inside Gamescope's Xwayland.
Discard 100 s after input replay; one-second FPS bins, zero bins included; nearest-rank p10/p1.
This counts game presentations to Gamescope, not compositor Hz, simulation speed or physical panel scanout.
Window: 0; duration: 180 s; bins: 0.
Input script: none; trivial launch only.

| median FPS | p10 FPS | p1 FPS |
|---:|---:|---:|
| unavailable | unavailable | unavailable |

## Launch and cleanup

Korrid exact session: `korri-game-9558a987340dd810bd438f446b75b15d.service`; renderer host PID: 0. Gamescope observed: False.
Bubblewrap: absent — core gap korri-os/korri#184 (ADR 0015 unimplemented). Not sandbox acceptance, not a bench failure.
Exact cgroup empty: True; no new emulator/wrapper leftovers: True; observer remaining: False.
Cleanup error: none. See cleanup.json and processes.json.
No env injection, wrapper bypass, policy writes, plugin installation or global kills. Normal korrid play/save effects apply.
Raw evidence on device: present.csv, observer.log, telemetry.jsonl, fps.json, cleanup.json, processes.json, idle.json.

## Retained earlier launch status

No retained HostLaunchFailed was accepted as idle.

## CPU/GPU clocks, temperature and memory

One-second read-only samples; peaks include warmup. Null sensors omitted, not replaced with zero.
RSS/swap sum the exact-session processes; shared RSS may be counted more than once.

| metric (native unit) | minimum | peak |
|---|---:|---:|

## Eden backend evidence

Backend: unproven. See backend.json.
No Eden log: trivial non-Eden launch or evidence unavailable.


## Operator provenance and acceptance boundary

This is the personal test build `@<publisher>:eden` from committed source
`fc795cdfc782bac0c649fec92f765ac7edc1d416`. Test-only composition replaced exactly
one literal, `@korri:eden/eden` → `@<publisher>:eden/eden`, with no other source
delta. Native Eden and the launcher were unchanged. This is not an official
publication or an accepted SMO performance result. No Bonneton input script
was supplied or verified. The generated template's "trivial launch only" text
must not be read as scene validation for this Eden attempt.

See [the stage report](../report.md) for installation, native diagnostics,
settings restoration and the mandatory graphics stop.

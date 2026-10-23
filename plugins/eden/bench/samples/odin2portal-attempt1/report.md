# odin2portal: Eden bench

Status: FAILED: <urlopen error [Errno 111] Connection refused>
Game `wl4`; runner `@korri:mgba/mgba`; launch ``.
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

Korrid exact session: ``; renderer host PID: 0. Gamescope observed: False.
Bubblewrap: absent — core gap korri-os/korri#184 (ADR 0015 unimplemented). Not sandbox acceptance, not a bench failure.
Exact cgroup empty: True; no new emulator/wrapper leftovers: True; observer remaining: False.
Cleanup error: none. See cleanup.json and processes.json.
No env injection, wrapper bypass, policy writes, plugin installation or global kills. Normal korrid play/save effects apply.
Raw evidence on device: present.csv, observer.log, telemetry.jsonl, fps.json, cleanup.json, processes.json.

## CPU/GPU clocks, temperature and memory

One-second read-only samples; peaks include warmup. Null sensors omitted, not replaced with zero.
RSS/swap sum the exact-session processes; shared RSS may be counted more than once.

| metric (native unit) | minimum | peak |
|---|---:|---:|

## Eden backend evidence

Backend: not applicable (non-Eden validation). See backend.json.
No Eden log: trivial non-Eden launch or evidence unavailable.

## Operator context

The daemon restarted outside this workflow around this attempt. Its observed PID changed from 1974 to 14635; systemd records the replacement active at 2026-10-23 01:23:30 UTC. This worker did not restart it. The exact external cause is unknown; a concurrent Cemu operation is possible, not verified. No session was reserved and no emulator or observer started. The failed device report is preserved unchanged at its original path. A retry uses a new directory only after a 120-second same-PID idle watch and a successful plugin-host admission query.

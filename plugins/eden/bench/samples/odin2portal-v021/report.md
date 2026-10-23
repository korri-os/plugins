# odin2portal: Eden bench

Status: FAILED: No exact-session X11 renderer under Gamescope
Game `wl4`; runner `@korri:mgba/mgba`; launch `f927719fbb1e98399c1ebb5f31b9ef86`.
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

Korrid exact session: `korri-game-f927719fbb1e98399c1ebb5f31b9ef86.service`; renderer host PID: 18425. Gamescope observed: False.
Bubblewrap: absent — core gap korri-os/korri#184 (ADR 0015 unimplemented). Not sandbox acceptance, not a bench failure.
Exact cgroup empty: True; no new emulator/wrapper leftovers: True; observer remaining: False.
Cleanup error: RPC failed: HostRecoveryBlocked. See cleanup.json and processes.json.
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

Backend: not applicable (non-Eden validation). See backend.json.
No Eden log: trivial non-Eden launch or evidence unavailable.

## Operator follow-up

See [findings.md](findings.md) for the read-only modifier-layer and recovery diagnosis, the nine exact-unit journal lines, and the decision to defer device FPS proof. No wl4 launch setting was changed. The original generated report remains unchanged on the device.

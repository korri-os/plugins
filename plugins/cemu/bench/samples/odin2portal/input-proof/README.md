# Visible P2 input proof — updated Odin

Verified with the existing `mega-man-arena` library route,
`@<publisher>:mega-man-arena/proton`. This was a normal korrid reservation/start.
The synthetic Bluetooth source was created after the game started. It was
admitted to P2 with `ManageAllDevices` unchanged; built-in CompositeDevice0 and
P1 stayed unchanged. This is **bench/test only**, not a product input route.

After a 65-second wait, the probe released a short L3 wake press and captured
the credits. Then it replayed these presses with releases (150 ms each):

| Step | Wait after press | Inspected screenshot | Observation |
|---|---:|---|---|
| Baseline | 2 s after L3 | [before.png](before.png) | Credits |
| Start | 3 s | [after-start.png](after-start.png) | Byte-identical credits |
| A | 2 s | [after-a.png](after-a.png) | Story intro |
| B | 2 s | [after-b.png](after-b.png) | Byte-identical story intro |
| A | 2 s | [after-a2.png](after-a2.png) | Title screen |

This provides visible game response, not just device admission: A advanced
credits → story → title; Start/B did not advance the corresponding screens.
The screenshots were read directly. SHA256SUMS preserves their original bytes.
`seat-events.json` records the ordinary P2 key events. `input-observer.json`
records the baseline and restored topology/policy/P1 state. This does not prove
BotW navigation or the future Cemu native controller profile.

Exact-stop RPC returned a transient recovery block because its Proton wrapper
exited 143. The original `cleanup.json` retains that error; it has not been
rewritten to imply a clean RPC reply. Subsequent status recovery left no unit,
process or cgroup member, and no active journal remained. See
[the core defect note](../../../devices/odin2portal-stop-143.md). No administrator
reset/restart or journal edit was used. The later full WL4 benchmark separately
proved the updated prebuilt tool's normal stop and cleanup.

`probe-source.txt` preserves the one-off probe exactly as executed, including
its temporary source import path. It is evidence, not an installed product
entry point. Do not execute its obsolete absolute paths without review.

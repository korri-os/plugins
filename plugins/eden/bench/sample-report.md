# Report format reference — not a measurement

Status: NOT RUN (format reference only). Real device results belong in
`samples/` and VERIFICATION.md. This file contains no invented FPS or telemetry.

## Measurement

Source: game-window X11 Present CompleteNotify/Pixmap, excluding Skip, selected
by the renderer's server-owned XRes PID. Neither Eden's counter nor MangoHud.
Warmup: 100 seconds after input replay. Measurement: 180 one-second FPS bins.
Soak: 15 minutes. Zero bins count; missing presentations or window replacement
fail instead of falling back to compositor refresh.

| median FPS | p10 FPS | p1 FPS |
|---:|---:|---:|
| unavailable | unavailable | unavailable |

CPU/GPU clocks, peak temperature, peak session RSS and swap: unavailable.

## Launch and cleanup

Actual reports name the korrid session and renderer and record observed
Gamescope/bubblewrap. An absent bubblewrap is **Core gap korri-os/korri#184**,
not sandbox acceptance and not an FPS failure. No wrapper is added to conceal it.

Cleanup requires the exact session cgroup to be empty, no newly surviving
emulator/wrapper process, and no owned observer process. The tool stops only
its recorded exact launch and its own observer, never a global emulator kill.

Eden Vulkan/backend evidence and Bonneton arrival are not applicable to a
trivial non-Eden launch. SMO installation/gameplay is a separate stage.

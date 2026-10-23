# NCE preparations and interrupted run — 2026-10-23 UTC

**No accepted baseline FPS. Further retries stopped for diagnosis.**

| Attempt | Exact failure | What actually ran |
|---|---|---|
| `r1-nce` | The administrative SDL discovery used bench Python 3.13/glibc 2.40, but Eden's SDL3 requires `GLIBC_2.43`. | No game launch or temporary INI change. Using Eden's actual wrapper Python 3.14 then enumerated all four seats successfully. The shipped wrapper already uses that interpreter; no product fix is needed. |
| `r1-nce-retry` | Bare assertion at controller line 105: `changed > 0`; **saw 0**. The temporary remap searched `p1_`, but Eden's actual native artifact/config use `player_0_`. | No game launch. Native file restored to its exact baseline hash. The corrected native prefix changed 23 SDL fields in the next preparation. |
| `r1-nce-ready` | No assertion failed. The controller reported `Cemu appeared; exact owned stop and yield`, then sent SIGTERM to its own collector. The collector reported `KeyboardInterrupt`. | Real library launch `2ed49314b125906f46c450f4a39627d6`, renderer PID 24828 under Gamescope. **938 non-Skip Present events** (32 Copy, 906 Flip), spanning 31.441504 seconds; **zero measurement bins**. Replay began, but no navigation screenshot/acceptance occurred before interruption. |

Fresh native log for the actual run: `Cpu.cpu_backend: Nce`, Turnip Adreno
(TM) 650, turnip Mesa driver 26.2.3, Vulkan 1.3.354. This is backend **selection**,
not instruction-execution proof; no measured runtime-map inference completed.
Bubblewrap was absent (Core gap #184).

The third controller did not retain the PID/identity behind its Cemu signal.
The independent 15-second watch did not observe Cemu in its samples. Therefore
actual Cemu contention is **not established**, nor is its absence proved. A
raw `pgrep -if '[c]emu'` can also match another read-only `pgrep` whose own
arguments contain `cemu|eden|bench`; that possible observer false positive must
be reproduced and excluded before retrying. Future yield evidence must name
the actual contender PID, executable and start identity, without saving argv.

The exact cgroup and observer are empty, with no new emulator/wrapper leftover.
The collector's post-stop idle RPC reported `HostRecoveryBlocked`; native unit
journal says it deactivated successfully. Do not call reconciliation fully
successful or an emulator crash. The native INI restored exactly to
`a2459bd8025e0d50e92f36cae7a38b904639212a98b8a7c6f042f19c20bbcba8`.
No CPU/GPU launch setting changed.

Kernel-journal filtering for 16:32–16:35 found no OOM, killed-process, GPU fault,
hang or reset line. The exact unit reported 4.5 GiB memory peak and 23.2 GiB
read over 97.274 seconds. SSH observations timed out during the run. Memory/I/O
pressure is a concern, **not proven OOM**. Future attempts need MemAvailable,
memory PSI and cgroup memory events, alongside the existing RSS telemetry.

## Checked fixes and native recovery

The observer false positive is now reproduced with a real, owned `pgrep`,
paused only to make scheduling overlap deterministic. The old detector matches
that probe. The corrected detector reads PID/executable/start identity, excludes
only the read-only `pgrep` executable, and still detects a real workflow-shaped
Python process. Both real-process tests, Ruff and mypy passed. This proves the
detector defect, not that it caused this particular interruption; its original
contender was not retained. No plugin or bench 0.2.2 product code changed.

The upcoming controller now reports expected and observed values in every
assertion. It also records MemAvailable, global/cgroup memory PSI, and cgroup
memory events. No swap/zram or system policy is changed.

The persistent Core blocker was separately diagnosed. The daemon journal
reported a systemctl timeout at 16:33:27, then input coordination fenced and
explicitly directed a korrid restart after resolving the exact session. The
retained `running` record named this stopped launch; all game/acquire units
were empty. Its protected copy/hash was retained. One service restart hit
systemd's 90-second stop timeout, which killed the old daemon; the new daemon
started at 16:47:05 and completed native recovery. [Recovery proof](recovery-proof.json)
shows RPC idle passed and the retained active record is now absent through
Core's own state machine. No session/history record was edited or cleared by
this worker. The native INI still matches the baseline hash. A fresh idle
window is required before the diagnosed retry.

## Later memory-first work

See [the memory-first report](../rpminiv2-memory/REPORT.md) for the diagnosed
NCE memory pressure, confirmed Dynarmic OOM, native recovery/save-content proof,
and the later 0.5× attempt. That report supersedes this earlier restoration status
for the current device state.

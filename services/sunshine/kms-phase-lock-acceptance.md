# RG35XX Pro vblank-lock measurements —2026-10-23

Owner approved shipping the exact package as is and stopped testing. Bad sessions
still occur. This record does not claim a passing six-session gate.

Exact ARM root: `/nix/store/ah6lyx1jg7fmdc4sfdv4jj66h8kd97bp-korri-plugin`.
Default offset0ms; capture-only FIFO5; native LimitRTPRIO5.
No source/encoder probes ship. Core permission ceca5b066 and documentation5410f88
must be reviewed onto Core main before a reachable publisher pin update and a
compatible consuming host. No pin update, publication or candidate install ran.

## Final exact-package measurements

**Owner approved shipping as is after reviewing the remaining bad sessions.**
This is not a passing six-session acceptance claim or a perfect-60 claim.
No new tests started after the stop decision. The immutable package below was
used throughout, with the native default offset0 and capture FIFO5.

Exactly the first10 seconds from first received frame are warm-up. The tables
retain every subsequent whole10-second window. Nothing is shifted or normalized.
Raw warm-up, including unreadable IDs, is retained separately. Receive time is
the primary clock; server PTS is not monotonic. Missing presented source IDs
count even if raw NV12 captured them. Source misses are separate. Every scored
frame passed decoding and source-ID CRC; H.264 decode errors/warnings were zero.

### Three90-second USB runs

| Run | New-frame windows, in order | Capture/downstream misses | Source misses | Raw warm-up new / unreadable |
|---|---|---|---|---|
| usb1 | 600/600/600/601/598/599/600/600/600 | 0/0/0/0/2/0/0/0/0 | 0/0/0/0/0/1/0/0/0 | 525 / 0 |
| usb2 | 600/600/600/600/600/600/600/599/600 | 0/0/0/0/0/0/0/1/0 | 0/0/0/0/0/0/0/0/0 | 568 / 0 |
| usb3 | 600/600/600/600/600/599/600/599/600 | 0/0/0/0/0/1/0/1/0 | 0/0/0/0/0/0/0/0/0 | 545 / 1 |

Combined: **59.981481fps (59.98fps)** over270 scored seconds. Misses are **2/1/2**;
source misses **1/0/0**. Every window is **at least598**. Two runs exceed a literal
one-miss limit; the owner accepted the approximate-rate shape, not that limit.
These five omissions were absent from raw acquisition, with five skipped
hardware sequences in total. There were no reused sequences, RT guard events,
nominal fallbacks, compositor guard trips, client frame-number gaps or decode
errors. The vblank lock and FIFO5 remained active.

### Owner-stopped60-second batch: bad sessions still occur

| Run | New-frame windows, in order | Capture/downstream misses | Source misses | Raw warm-up new / unreadable |
|---|---|---|---|---|
| s1 | 600/599/596/599/600/600 | 0/1/4/1/0/0 | 0/0/0/0/0/0 | 521 / 0 |
| s2 | 522/600/538/600/600/599 | 77/0/62/0/0/1 | 0/0/0/0/0/0 | 378 / 0 |
| s3 | 493/584/600/600/599/600 | 107/16/0/0/1/0 | 0/0/0/0/0/0 | 581 / 1 |
| s4 | 600/599/600/600/600/539 | 0/1/0/0/0/61 | 0/0/0/0/0/0 | 544 / 0 |
| s5 | 599/600/600/600/600/600 | 1/0/0/0/0/0 | 0/0/0/0/0/0 | 571 / 0 |

S1 has one **596** window. S2 has **522/538** windows. These are bad sessions,
not merely the deferred last bit. S3 also has493/584; S4 has539. Four of the five
sessions scored before the stop fail the597 floor; S5 meets it.

**Stop chronology:** the owner asked to endS3 and not startS4–S6. That message
arrived afterS4/S5 had completed andS6 had already started. The controller was
sent SIGTERM at03:49:09UTC. S6 had recorded its stream, but source scoring was
interrupted. S6 has no invented acceptance result. No further session started.
The published service was restored at03:49:45UTC. All partial evidence survives.

| Session | Missing raw acquisition IDs | Raw NV12 present, absent client | Skipped / reused vblank sequences | Client frame-number gaps, whole recording | Guard events |
|---|---:|---:|---|---:|---:|
| s1 | 5 | 1 | 5 / 0 | 0 | 0 |
| s2 | 1 | 139 | 1 / 0 | 352 | 0 |
| s3 | 1 | 123 | 1 / 0 | 128 | 0 |
| s4 | 1 | 61 | 1 / 0 | 64 | 0 |
| s5 | 1 | 0 | 1 / 0 | 0 | 0 |

**S2 classification:** all77+62 burst IDs were present in raw NV12 but absent
from the received stream. Only its later single miss was a raw-acquisition
omission. Thus the bursts are downstream of acquisition. The recording also
has352 client frame-number gaps, including warm-up. This probe does not prove
whether encoder/handoff, transport or the receiving client discarded them.
No V4L2 encoder-input probe was resumed. S3 andS4 also have downstream bursts.
All five scored sessions retained FIFO5 and active lock, without fallback,
reused sequence, compositor timeout, RT guard event or decode error.

### Per-miss, stage, memory and thermal evidence

`services/sunshine/kms-phase-lock-misses.csv` commits338 individual scored
missing-ID records from the three90-second and five scored60-second sessions.
It records classification, presented/acquired sequences, plane/FB ID, read
wall/CPU and conversion/DMA-sync times, adjacent acquisition times, client
frame-number gap, and frequency/temperature where actually sampled. Blank
fields mean unmeasured, not zero. It is diagnostic data, not a product schema.
The complete raw stage, scheduler, allocation, source and1Hz startup-through-
teardown vmstat files remain in `/tmp/h700-sun` on zao. The1Hz memory intervals
can overlap neighboring windows; they are not millisecond-causal proof.

Frequency/temperature was **not collected duringS1–S4's missed frames**.
Read-only nice19 telemetry started03:45:17UTC. Only S5's one miss has covered
telemetry; earlier values cannot be reconstructed. The observed tail used
schedutil,1416000kHz maximum/current, temperatures near53C and cooling states0.
Those later readings do not exclude earlier heat or frequency changes.

| Run | Startup CMA success/fail | Startup migration success/fail | Startup available/CMA-free minimum KiB | Scored CMA success/fail | Scored direct scan | Scored migration success/fail |
|---|---|---|---|---|---|---|
| usb1 | 51/0 | 3865/123 | 291788/4000 | 0/0 | 0 | 0/0 |
| usb2 | 51/0 | 4083/50 | 326932/34228 | 0/0 | 0 | 0/0 |
| usb3 | 51/0 | 4307/115 | 315372/33460 | 0/0 | 0 | 0/0 |
| s1 | 51/0 | 1594/217 | 305724/10520 | 0/0 | 0 | 299/101 |
| s2 | 51/0 | 4574/50 | 326996/27916 | 0/0 | 0 | 0/0 |
| s3 | 51/0 | 4518/45 | 322324/32648 | 0/0 | 0 | 23/2 |
| s4 | 51/0 | 4643/50 | 313572/35684 | 0/0 | 0 | 0/0 |
| s5 | 51/0 | 6418/50 | 323664/30576 | 0/0 | 0 | 0/2 |

Startup allocation events and perf roles are retained per session. The raw
1Hz gauges include CMA, available/free RAM, cache, dirty/writeback and kernel
workers. `/tmp` is ext4; old diagnostics are reclaimable page cache, not proof
of leaked RAM. Memory counters do not explain the downstream bursts by
correlation alone. No last-bit or new bad-session tuning was done after stop.

### Safety controls on this exact package

| Control | Result | Pacing / continuation | Maximum compositor reply |
|---|---|---|---:|
| Frozen reported vblank sequence after first acquisition | Demoted before third same-sequence acquisition | Full30s session continued as OTHER | 972.55ms, no1s guard trip |
| Timing unavailable plus250ms startup CPU | Kept FIFO5; no guard event | All1661 observed read-pairs blocked;1661 nominal sleeps | 31.044ms |
| Normal, no injection | Kept FIFO5; no guard event | All1671 observed read-pairs blocked in vblank waits | 30.834ms |

Forced stale-sequence decision:63594686792833ns;34.754ms after first acquisition
completion,66.488ms after first acquisition start,89.603ms after FIFO entry.
It logged three same sequences, three pacing calls,15.693ms diagnostic blocking.
The guard ran before another acquisition. The first capture-successor Sway
preemption was only0.663ms,285.7ms after demotion; none occurred before it.
The972.55ms IPC query began54.167ms before the decision and ended918.383ms after
it. Its longest Sway off-CPU interval was25.660ms and voluntary. That IPC delay
is **not972ms of RT capture preemption**. Its exact cause is not established.
No monitor timeout was relaxed; the compositor-response limit remained1second.

The real native guard also passed as UID1000, RTPRIO5 and CapEff0: normal and
passed-deadline calls at99.8%CPU retain FIFO5; slow/skip, fallback, no-call,
re-read, backwards/wrap, reset-on-fork demotion and actual seccomp-denied
sleep-only continuation all pass. Rejected CPU-share/minimum-block rules and
old safety failures remain historical failures, not acceptance evidence.

## Checks already completed — no more device tests

| Check | Result / retained log |
|---|---|
| ARM exact producer build | PASS `phase-call-plugin-build.log` |
| Capture checks on both architectures | PASS `phase-call-capture-checks.log`; C++ -Wall -Wextra -Werror, row-pair/pacing/guard |
| Runtime settings, base package and native plugin, both architectures; ARM V4L2 | PASS `phase-call-producer-checks.log` |
| Both architecture admission checks against committed local Core5410 | PASS `phase-call-admission-checks.log` |
| Native unprivileged RT guard | PASS `rt-guard-call-unprivileged-green.log` |
| Three exact-package safety controls | PASS `content-memory-phase-call-safety-run.log` |
| Final C++ upstream clang-format, changed Nixfmt, actual runtime/helper ShellCheck | PASS2026-10-23T03:38:28UTC |
| Core permission | Serial220 passed/16 ignored; check/fmt/libraryClippy, real-store graph, builder and plugin-host VM PASS |

There are11 focused Nix checks: capture2, package2, runtime2, native2, ARMV4L2 one,
admission2. No full-project suite is claimed. Core all-target Clippy remains
blocked by pre-existing `items_after_test_module`. Unified patch blank context
lines intentionally contain one space; inserted C++ lines have no trailing
whitespace. Commit secret hooks run normally, without bypass.

## Restoration and evidence preservation

Published `@korri:sunshine` is **Enabled**, active, MainPID332146, with its
unchanged published root `/nix/store/7q3fv7767vdzrbax2v2dz2chcvp2yf7r-korri-plugin`.
The fresh current-PID log at2026-10-23T03:49:45.209UTC says
`Found H.264 encoder: h264_v4l2m2m`. Only the published Sunshine process remains.
The final saved firewall rules compare identical; only iptables-save timestamp
comments were excluded. No owner game was stopped. The candidate was never
installed or automatically approved. No reboot, firmware/module/governor or
compositor-default change occurred. Sway seat idle notification wakes the panel;
normal idle policy is unchanged.

All732 regular files under the device's `/tmp/h700-*` were archived on zao and
SHA256-verified before deletion. `device-h700-before-cleanup.tar.gz` is177833784
bytes, SHA256`ef1fe49872e009dabe0a2bfe1dcf0cc3e5e817a40ccbe62364442483381d196f`.
The private archive is mode0600. `device-h700-before-cleanup.sha256` records every
file hash. Final device `/tmp/h700-*` count is **0**. Evidence under zao's
`/tmp/h700-sun` is retained. See `owner-stop-final-restoration.log`,
`device-h700-backup-verification.log` and `owner-authorized-device-cleanup.log`.

## Limits and follow-up

Bad sessions still occur. Downstream bursts are not solved or excused by clean
raw acquisitions. Last-bit/V4L2 input-ID investigation remains stopped and
backlogged (parent reference#186). No issue was filed by this child. Capture
can still delay Sway for about14ms. Inherited FIFO authority is not limited by
the kernel to the capture thread. Calls/sequence guard bounds detected pacing
faults; it is not a general CPU budget or proof against every driver failure.

Acceptance scope is this Linux RG35XX Pro,640x480/H.264/60Hz/USB slice. It does
not cover arbitrary loads, other modes/matrices, HDR, visible cursors, multiple
clients, Wi-Fi or physical input latency. Offset0 reads current content far
more consistently than13ms queued-state reads, but observed receipt latency
costs roughly4–5ms (bridge uncertainty about3ms/run). Physical scanout FB ID
is not independently exported by the presentation protocol. A capture-successor
Sway off-CPU interval does not prove every microsecond was capture CPU time.
All earlier failed experiments remain failures, not evidence of a fix.

Full patch headers, hashes, publication commands and restoration evidence:
`/tmp/h700-sun/ship.md` on zao. Raw data remains outside Git.

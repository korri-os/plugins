# Odin gameplay gate proof — 2026-10-23

Verified with prebuilt bench
`/nix/store/092bcnlgn7w4vbbp5cknp30j72cv2h32-korri-cemu-bench-0.1.0`.
ARM built on yari through zao, signed on zao, copied over USB. No target build,
plugin installation, system/firmware change or permission bypass occurred.
The installed personal Cemu test runner used Mesa 25.3.2; async was false.

| Case | Result | Title / loading / gameplay / end, seconds after launch request | median / p10 / p1 |
|---|---|---|---|
| [normal](normal/report.md) | PASS; 100 s warmup + 180 complete gameplay bins | 11.04 / 36.60 / 68.80 / 350.87 | 37 / 37 / 36 |
| [broken, no scripted or owner input](broken/report.md) | not measured; exit 1; loading gate deadline | 9.87 / not observed / not observed / not observed | — |
| [save route 1](save-01/report.md) | unproven; no changed game-data hash and mtime | 9.02 / 27.01 / 47.60 / not sampled | — |
| [save route 2](save-02/report.md) | unproven; same bounded failure | 10.99 / 28.73 / 50.10 / not sampled | — |

Normal minimum: 36 FPS. Peak recorded thermal zone: 95.9 °C, including warmup.
The old async-off baseline was 39 / 38 / 36; this is comparable in range, not a
controlled driver A/B or a claim of improvement. Current launch limits remained
device defaults, CPU/GPU 0–100 and schedutil. Native settings were 1280×720,
FPS++ normal 45 with retained advanced 40, VSync 0, async off, draw-done sync and
accurate barriers off. No scripted movement followed load. No named scene is
claimed.

`normal/save-read.json` proves an actual Cemu read of slot 3's game_data.sav,
SHA-256 `34726184bf791cea4714e7847b111e56a5475cf1d4103c4e576c7a5fc475abea`.
The reader was installed after launch materialization and before input. Raw
Present events reproduce all 180 bins in `normal/fps.json`; compressed telemetry
and numeric frame fingerprints retain their raw bytes. No images are committed
or displayed.

Every case restored and verified its original 54-file payload through supported
`app.saves.restore`: one session record plus one restore continuation each.
[The independent final audit](final-audit.json) checks the whole campaign's
original head `466882dd…` against final continuation `989fc95b…`: payload equal,
all 54 files complete, original in ancestry. IDs cannot remain equal because
restore appends. The final four cases added **eight** history records; including
the earlier refused normal/title diagnostic launches, the campaign added
**14 records across seven sessions**. The initial preflight refusal launched
nothing. A private complete backup remains outside Git.

The owner ended WL4 at 20:15:12 UTC (2417 s, not interrupted), producing current
head `c1cf7c18…`. Its 69 records and selected head remained unchanged throughout;
its status was Synced, not Split. No WL4 save write/restore/choice was issued.

Library bytes, native settings (`AsyncCompile=false`), P1, launch limits and
mute were restored. Both cache directories were restored from preserved copies;
generated caches were moved aside, not deleted. Final boot/system are unchanged.
No game unit, Cemu/Gamescope/Eden/observer, bench pad or test process survived.

## Diagnostic run that is not a proof case

The [owner-driven sequence](owner-driven-sequence/README.md) began as a no-input
label-capture run. The owner then pressed physical controls and played briefly.
The gate observed title → loading → gameplay, but that is **not** an automated
normal or broken proof case. Only its labelled numeric fingerprints are kept
here; its one-second performance result is not published or accepted.

## Remaining risk / note for #212

No supported guest/test launch or snapshot opt-out exists. Payload restoration
is **not history isolation**: bench and restore records still sync and count
toward retention. This does not fix #208 or prove all older payloads complete.
The manual-save route remains unproven after exactly two attempts; its relaunch
branch was not exercised. No save was fabricated and no menu guess followed.

Public copies redact the personal runner namespace, account path and private
backup location. Checksums describe these public copies. Full private operational
and restoration evidence remains outside Git. See the device report for handoff.

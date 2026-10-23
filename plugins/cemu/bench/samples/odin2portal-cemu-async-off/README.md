# Odin BotW — async off, 2026-10-23 UTC

[Campaign report and restoration](../../devices/odin2portal-async-off-2026-10-23.md).
These are Cemu gameplay runs, not the earlier WL4 validation. No screenshot,
game/save content, core, key, capability or fabricated record is included.

| Sample | Warmup / measurement | median / p10 / p1 FPS | Peak temperature |
|---|---|---|---|
| [Baseline](baseline/report.md) | 100 / 180 s | 39 / 38 / 36 | 96.7 °C |
| [Soak](soak/report.md) | 100 / 900 s | 40 / 38 / 34 | 97.5 °C |

Both use the same installed personal test composition, unchanged production
source from `a944c7f`: Cemu `29f2f1fae4631e2317977debd9eacd55cc28dd7d`,
Cemu-only Turnip 25.3.2, Gamescope on system Mesa 26.2.3. Native test settings:
720p, async compile off, GX2DrawDone sync off, accurate barriers off, VSync 0,
FPS++ normal 45 / advanced 40; game-layer CPU/GPU minima 100 through korrid RPC.
No affinity or cooling change. Native settings and launch limits were restored.

| Artifact | Store path |
|---|---|
| Bench | `/nix/store/ycx1s593595i2c2hyax3l5i58d6iqcw8-korri-cemu-bench-0.1.0` |
| Cemu | `/nix/store/3qks80jgqy1p6i01914n9pnjnhj8kygk-cemu-0-unstable-2026-10-22-29f2f1f` |
| Personal test plugin | `/nix/store/g7adybv05pxjyi1klapk19xrjbm7b0ql-korri-plugin` |
| Cemu Mesa | `/nix/store/jqr5bd0qqwq14pzi6jf0c1y9ljbkqgj7-mesa-25.3.2` |

This stage reused the previously signed/inspected/installed/enabled package;
there was no new installation or build. Exact identity and trust receipts are
in the linked Turnip campaign. Every launch used the library through real korrid.
Both actual renderer and Gamescope driver mappings were retained privately.
Screenshots were checked numerically, never opened. A named fixed position was
not independently verified visually. The route loads the newest staged Zora's
Domain save, with no movement. A new manual save was **not** proven.

Each sample retains its complete report, resolved settings, FPS bins, exact-stop
cleanup, native-profile restoration and input ownership evidence. Gzip files
preserve the original raw Present and telemetry bytes. `soak/minutes.json` gives
all 15 per-minute FPS/temperature summaries. These are one-second presentation
counts, not panel Hz or simulation-speed measurements. The report's `PASS`
means the bench completed, not that every stage acceptance target passed.

Reproduce every stored bin, percentile and maximum temperature from repo root:

```sh
python3 - <<'PY'
import csv, gzip, io, json, sys
from pathlib import Path
sys.path.insert(0, 'plugins/cemu/bench')
from metrics import fps_bins, summarize
root = Path('plugins/cemu/bench/samples/odin2portal-cemu-async-off')
for name in ['baseline', 'soak']:
    p = root / name
    f = json.loads((p / 'fps.json').read_text())
    rows = csv.DictReader(io.StringIO(gzip.decompress((p / 'present.csv.gz').read_bytes()).decode()))
    events = [(int(r['ust_us']) / 1e6, int(r['window']), int(r['mode'])) for r in rows]
    bins = fps_bins(events, f['window'], f['measurementStart'], f['seconds'])
    assert bins == f['fps']
    assert all(f[k] == v for k, v in summarize(bins).items())
    telemetry = [json.loads(line) for line in gzip.decompress((p / 'telemetry.jsonl.gz').read_bytes()).splitlines()]
    peak = max(v for row in telemetry for k, v in row.items() if k.startswith('temp/') and v is not None) / 1000
    print(name, summarize(bins), 'peak C', peak)
PY
```

The campaign retains interrupted and menu-only attempts separately in private
evidence; their incomplete/short samples are not substituted for these runs.

[Restoration proof](restoration.json) and [independent final audit](final-audit.json)
show defaults restored, no test/game process or pad, unchanged boot/system, and
speaker left at **0.40 muted**, as the owner required. The original 0.95 level
was deliberately not reinstated.

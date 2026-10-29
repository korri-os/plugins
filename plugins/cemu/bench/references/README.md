# Numeric gameplay references

No images or save contents live here. JSON contains 31×27 RGB statistics,
sparse title-foreground pixel indexes, original capture SHA-256s, calibrated
mean-absolute-difference boundaries, and recorded classification checks.

| Reference | Real source | Aspect and resolution | Limits |
|---|---|---|---|
| `botw-1920x1080.json` | Odin async-off and first-light diagnosis, 2026-10-22/23: two pre-input title frames, known loading frame, stationary gameplay frames at 100/160 s | 16:9, compositor 1920×1080, game 1280×720 | The same staged save, not a named-location claim. Historic title captures share a background; live validation must exercise the foreground gate. |
| `botw-1240x1080.json` | Mini ladder and private gated patched retry, 2026-10-23: two pre-input title frames, post-title +30 s loading frame, three verified gameplay captures | 31:27, compositor 1240×1080, game 1028×896 / 827×720 / 620×540 | Numeric classifier calibration only here; no new Mini launch or soak validation. |

`*-checks.json` contains statistics from those real captures, not generated
lookalike images. Every capture must classify as its recorded state before
calibration can write the files. Tests run without decoding or displaying an
image. References are tied to the existing library game ID and exact output
size. They are not general scene-recognition models.

## BotW Clarity and 960×540 runs, 2026-10-29 (no new reference)

Four Odin runs used the Enhancements pack's Clarity preset "Serfrost's Preset
(Recommended)" with FPS++ "No FPS Limit": `uncapped-20261029` (game
1280×720) and `probe540`, `probe540b`, `probe540fsr3` (game 960×540, Shadows
Low). The compositor output stayed 1920×1080. Their `frames.jsonl`
descriptors were checked against `botw-1920x1080.json`:

| State | Result with Clarity |
|---|---|
| Title | Matches: distance 0.0–3.3, foreground coverage 1.00, in all four runs. |
| Loading | Matches: distance 0.6–2.8 in three runs. `probe540` never reached loading; after the title its frames kept coverage 0.99–1.00, which is another screen, and the gate correctly refused it. |
| Gameplay | Does not match: distance 37–60 against the 35.5 threshold. |

A Clarity gameplay reference cannot be calibrated from these frames. The
frames after loading are not one stationary scene. Across the three runs that
loaded, the largest distance between two of these frames is 82.3, and between
two frames of `uncapped-20261029` alone it is 69.6. The smallest distance from
any of them to a title or loading frame is 45.8 (54.0 in
`uncapped-20261029`). `calibrate` refuses that overlap, and a threshold wide
enough to accept these frames would also accept title-like frames. The gate
was therefore not relaxed. A Clarity reference first needs runs whose
post-loading frames are stable, as in the 2026-10-23 calibration (largest
gameplay distance 3.8). Find out why the scene changes after loading with
Clarity and the uncapped frame rate before capturing again.

See the bench README for `korri-cemu-bench-reference capture` and `calibrate`.
Capture multiple title backgrounds, loading and the intended stationary scene.
Retain the private PNGs outside Git and never open them in an image viewer.
Recalibrate for another game, scene, output size or aspect. Validate additional
negative frames, including pause/save-selection menus. False refusal is safer
than admitting a title/menu as gameplay. Do not choose thresholds from the
performance result you want.

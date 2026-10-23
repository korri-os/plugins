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

See the bench README for `korri-cemu-bench-reference capture` and `calibrate`.
Capture multiple title backgrounds, loading and the intended stationary scene.
Retain the private PNGs outside Git and never open them in an image viewer.
Recalibrate for another game, scene, output size or aspect. Validate additional
negative frames, including pause/save-selection menus. False refusal is safer
than admitting a title/menu as gameplay. Do not choose thresholds from the
performance result you want.

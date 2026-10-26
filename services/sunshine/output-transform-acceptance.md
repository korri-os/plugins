# KMS output transforms — issue 273

Patch 0033 now handles every `wl_output.transform`, not only 270. Normal,
missing/unknown transforms and non-identity DRM plane rotation keep the direct
capture path. Transformed RAM capture still requires a full-size plane with no
offset. The privileged DRM worker and capability sites are unchanged.

The protocol defines counter-clockwise rotation and an initial vertical-axis
flip for the flipped variants. The table gives destination-to-source normalized
GL sampling coordinates `(u,v)`. Texture row order is preserved by readback.
The cursor uses the inverse of the same signed permutation, not a separate
rotation table. This also corrects the old 270 cursor mapping, which did not
invert the shader's sampler.

| wl_output transform | Sampler | Output size for raw W×H |
| --- | --- | --- |
| NORMAL (0) | `(u,v)`; no draw | W×H |
| 90 (1) | `(v,1-u)` | H×W |
| 180 (2) | `(1-u,1-v)` | W×H |
| 270 (3) | `(1-v,u)` | H×W |
| FLIPPED (4) | `(1-u,v)` | W×H |
| FLIPPED_90 (5) | `(1-v,1-u)` | H×W |
| FLIPPED_180 (6) | `(u,1-v)` | W×H |
| FLIPPED_270 (7) | `(v,u)` | H×W |

`output-transform-test.cpp` samples a labelled non-square image at pixel
centres using the production coefficients. It checks explicit expected images,
an independent flip-then-CCW-rotation construction, all cursor pixels and
clipping on all edges, and invalid transform values. `capture-check.nix` runs
it on both architectures. Patch 0035 and 0036 contexts were refreshed for the
renamed transform state; 0037 has only refreshed hunk offsets. Patch 0034 is
unchanged. The approved per-patch hashes and ordered digest were recomputed.

## Verification, 2026-10-26

Hardware used implementation commit `834f473d0e64f06c43ece62cc08eeff51fe4fb51`,
plugin `/nix/store/n6v97iajf3qrwjwm7g7h27jwxsicg8xa-korri-plugin`.
The later `db03ccf7ebce9333cacab2db04c3ed45c1b838a8` change only removes extra
spaces before table comments and refreshes provenance hashes. Its plugin,
`/nix/store/8nxfgikp1yld31fbf7i5ypvx4jfkld20-korri-plugin`, passed off-device
checks only. It was copied to the devices but never started.

All six requested checks built: `sunshine-korri-capture`,
`sunshine-korri-package`, and `korri-sunshine-plugin-native`, on both
`x86_64-linux` and `aarch64-linux`. The ARM plugin package also built.
The source derivations applied the complete ordered patch set with GNU
`patch -p1 --fuzz=0`. Capture tests passed all eight image/cursor mappings and
the existing pacing, scheduling, row-pair and privilege-site checks.
`nixfmt --check`, the C++ test's `clang-format --dry-run --Werror`, the helper's
upstream Sunshine clang-format check, and `git diff --check` passed.

### Odin

The recorded stream decoded all 1,605 frames at 1280×720 with zero decode
errors. Its picture is upright and fills the frame, like the 1920×1080 `grim`
screenshot captured during that run. Captions differ because the still and
screenshot are from different instants in the same game scene.

```text
KMS rotation probe decision: Wayland output=DSI-1 transform=1 chosen_transform=1 CRTC=107 plane=47 DRM rotation=1 expected_rotate_0=true raw=1080x1920 capture=1080x1920 offset=0,0
KMS RAM capture rotation probe: Wayland output=DSI-1 CRTC=107 plane=47 raw=1080x1920 output=1920x1080 wl_output transform=1 rotated=1
```

Local evidence:

| Before | Fixed stream | grim during fixed run |
| --- | --- | --- |
| `/tmp/odin-rotation/odin-before.png` | `/tmp/odin-rotation/odin-new/still.png` | `/tmp/odin-rotation/odin-new/grim.png` |

Side-by-side: `/tmp/odin-rotation/odin-before-after-grim.png`.
The before image is the parent's earlier v2026.914 recording, copied from
`/tmp/p3/view/odin-new/still.png`.

### Mini regression

```text
KMS rotation probe decision: Wayland output=DSI-1 transform=3 chosen_transform=3 CRTC=95 plane=47 DRM rotation=1 expected_rotate_0=true raw=1080x1240 capture=1080x1240 offset=0,0
KMS RAM capture rotation probe: Wayland output=DSI-1 CRTC=95 plane=47 raw=1080x1240 output=1240x1080 wl_output transform=3 rotated=1
```

The output size and 270 sampler are unchanged. All 1,267 recorded frames
decoded without errors. A visible frame, `/tmp/odin-rotation/mini-new/visible.png`,
shows upright text. Issue 272 still causes black frames; this test does not
qualify that separate defect or use blank counts to judge rotation.

### Restore and later real pairing state

Both completed hardware runs ended with `ab-device.sh restore`. The installed
Odin Sunshine was active, and both devices had no A/B drop-in or pairing-state
file at that check. The Mini plugin was then disabled again; its original
package and Disabled state were verified, with no drop-in or state file.

Before a second Odin run, `prepare` refused newly created pairing state. The
supplied wrapper's EXIT trap nevertheless called `restore` and saved that
state to `/tmp/sun-ab/test-state-1793050745.json`. Installed Sunshine recreated
live pairing state. On the parent's instruction, all further Odin tests stopped.
The live file was left intact and the saved copy retained. Installed Sunshine
remains active with its original ExecStart and no A/B drop-in. The original
policy drop-in is unchanged. Do not remove this real pairing state to meet a
test-cleanup assertion.

The journal does not identify the state writer. Sunshine logged
`SSL Verification error :: Client certificate identity is not paired` at
21:29:01 during test pairing. No certificate-provision lines appeared in the
requested Sunshine/korrid journal window; korrid's next entry was
`korrid save contact: SavePeerUnavailable` at 21:41:44. Provisioning by korrid
is inferred, not verified. Raw investigation logs are under
`/tmp/odin-rotation/odin-{state-investigation,provision,state-confirmation}.log`.

The other six transforms have host-side coverage, not hardware coverage.
No changes were pushed, merged, published, or made in Korri Core.

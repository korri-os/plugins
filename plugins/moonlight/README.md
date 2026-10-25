# Moonlight viewer

A removable, permission-approved plugin. The native setup unit creates only
`/home/korri/.config/moonlight` with mode 0700, owned by the runtime account.
Ordinary disable/removal stops the unit and retains the client identity, like
Sunshine. korrid resolves declared files through the enabled package registry
and runs each viewer in the hardened exact-launch systemd unit. No PIN is used.
No publication, deployment or hardware acceptance is implied by package checks.

Harvest: legacy `product/plugins/moonlight/packages/moonlight-embedded-korri/`
and `product/plugins/moonlight/removability.test.ts`. Patches document re-cuts.
Only base 0001/0001a/0002 and adapted 0013/0014/0015 ship. No touch, local
control, live stream settings, tracing or pacing patches ship.

Only controllers connected and bound to local seats at stream start are forwarded.
A controller connected later needs a stream restart. No occupied seats starts a
watch-only stream. X11 software decoding uses evdev input, never SDL joystick
auto-discovery; Qualcomm V4L2 M2M uses the same explicit seat paths.

## Server certificate pinning (new Korri security patch)

Patch 0020 is new code, not a legacy harvest. The private keydir holds only
stock identity files: `client.pem`, `key.pem` and `uniqueid.dat`. It remains
0700, with 0600 files. korrid never opens it. A bounded named viewer-sandbox
bootstrap unit runs the declared `identity-bootstrap` helper as `korri`. The
helper suppresses Moonlight output and emits exactly the public `client.pem`
on stdout through `systemd-run --wait --pipe`. The private key never crosses
that boundary. A deliberately invalid pin prevents bootstrap network access.

The broker-authorized host certificate enters each viewer unit through a
systemd credential. systemd expands the credential directory for
`KORRI_MOONLIGHT_SERVER_CERTIFICATE`; Moonlight verifies its TLS chain and pins
its public key. There are no per-launch pin files or stale-pin cleanup in the
keydir. Game units still cannot read the identity directory.

## Typed launch settings

Runner `@korri:moonlight/moonlight` declares `program: moonlight` and no
systems or releases. It is a stream viewer, not a local runner choice.
Device and game launch settings use nested objects; dots below name leaf
paths, not literal YAML keys. `settings.describe`, `settings.validate` and
`settings.render` own the schema, diagnostics and argument rendering.
Validation reports path segments; korrid warns and skips bad values.

Grounding: ADR 0037 and the approved settings-vocabulary brief; native flags
come from moonlight-embedded `775444287305849ebdf4736c75298ad0713e2d5d`,
`src/config.c` (`long_options`, `parse_argument`). Integers are positive signed
32-bit values. Resolution width and height must be set together.

| Setting path | Type / choices | Native argument / unset behavior |
|---|---|---|
| `video.resolution.width` | integer | `-width`; display width when unset |
| `video.resolution.height` | integer | `-height`; display height when unset |
| `video.fps` | integer | `-fps`; unset lets Moonlight choose (60) |
| `video.bitrate-kbps` | integer | `-bitrate`; unset lets Moonlight choose from size and fps |
| `video.codec` | auto, h264, h265, av1 | `-codec`; schema default **h264** |
| `video.hdr.enable` | boolean | true: `-hdr` |
| `video.rotation-degrees` | 0, 90, 180, 270 | `-rotate` |
| `video.optimize-game-settings` | boolean | false: `-nosops` |
| `video.allow-unsupported-resolution` | boolean | false: `-nounsupported` |
| `audio.channels` | stereo, 5.1, 7.1 (strings) | `-surround 5.1` / `7.1`; stereo emits nothing |
| `audio.play-on-host` | boolean | true: `-localaudio` |
| `input.mouse-emulation` | boolean | false: `-nomouseemulation` |
| `network.remote-optimizations` | auto, on, off | `-remote auto` / `yes` / `no` |
| `network.packet-size-bytes` | integer | `-packetsize` |
| `logging.level` | info, verbose, debug | nothing / `-verbose` / `-debug` |

Except for codec and display fallback, an unset path emits no argument.
There are no ranges or live changes during a stream.

### Options with no typed setting

| Native options / legacy settings | Why excluded |
|---|---|
| `720`, `1080`, `4k` | Use the explicit resolution pair |
| `app`, `keydir`, `mapping`, `platform`, `input`, `viewonly`, `port` | korrid owns stream identity, transport and seat-bound input |
| `windowed`, `autowindowresize`, `noautowindowresize` | korrid owns the viewer window |
| `quitappafter`, `pin` | korrid owns session lifetime and trust |
| `audio` | Korri routes audio through PipeWire |
| `config`, `save` | No arbitrary native configuration or config writes |
| Legacy `command`, `environment`, `platform`, `input.devices`, `input.mappingFile`, `input.viewOnly`, `input.touch`, `audio.device`, `window.*`, `control.*`, `stream.keyDir`, `stream.quitAppAfter`, `extraArgs` | Same Korri-owned boundaries; not settings escape hatches |

### Focused checks (build machines only)

```sh
bun test plugins/moonlight/settings.test.mts
nix build --no-link .#checks.x86_64-linux.korri-moonlight-plugin-native
```

The native check also typechecks the handlers and runs their unit tests.

Tests use `.mts` so the pinned builder does not ship the test modules in its
plugin source inventory. Production source remains TypeScript `.ts`.

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

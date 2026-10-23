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

Patch 0020 is new code, not a legacy harvest. korrid writes the authenticated
broker's server certificate to `server-<exact launch id>.pem` in the private
keydir, mode 0600. `KORRI_MOONLIGHT_SERVER_CERTIFICATE` makes Moonlight verify
its TLS chain and pin its public key. The viewer always supplies it, including
identity bootstrap; a missing pin refuses network requests. Each confirmed
stop removes its pin. Startup and each stream start remove pins with no live
launch unit. Live launch pins remain until confirmed stop.

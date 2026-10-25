# Sunshine streaming host plugin

`@korri:sunshine` is the removable Linux streaming-host integration. The package ships three native systemd units:

- `korri-sunshine.service` runs the reviewed Sunshine build as `korri`.
- `korri-sunshine-certificate-control.socket` gives korrid the private certificate-trust channel.
- `korri-sunshine-input-setup.service` owns the temporary group and runtime UHID permission rule. The core `korri-input-seat-receiver.service` owns persistent shared seats independently of this plugin.

The plugin requests KMS capture, broad device visibility, `CAP_SETPCAP`, and `CAP_SYS_ADMIN`. Approval binds those requests, both root helper commands, the named udev rule artifact, every native unit, and the exact package closure. The plugin host starts all three units before it opens the declared Sunshine ports. It never opens the administrative TCP port `47990`.

Removal stops all three plugin units, checks native cleanup, removes the runtime UHID rule and temporary group, closes the firewall rules, and releases the package selection. It does not stop the core receiver or change persistent seat permissions. It preserves `/home/korri/.config/sunshine`, including Sunshine identity, settings, and paired-client state. Korrid remains the only owner of the bounded stream-client trust effect.

The plugin uses globally unique systemd names. It does not replace a host `sunshine.service`, add a NixOS module, or keep a disabled host unit in the image.

## New real-time scheduling permission (candidate)

The native service now requests **`LimitRTPRIO=5`**. `runtime.sh` sets the
Sunshine config key `capture_rt_priority=5`. Only the guarded ARM RAM-KMS
backend requests FIFO 5, after establishing its vblank lock, with reset-on-fork.
Every other backend stays SCHED_OTHER even with this configuration. EPERM logs
and continues. RAM-KMS restores SCHED_OTHER before returning to another backend.
No `CAP_SYS_NICE` or service-wide scheduling policy is requested. This limit
still permits any thread in the service to request RT priority up to 5.
Lower-priority input/compositor work can be delayed; measured responsiveness
and exact-build re-approval are required, not implied by the limit.

The locked Core is reviewed main `eab74c96134abed6453ff74c6c80bf4ebca5c52f`.
It admits canonical decimal LimitRTPRIO=1..20 (no leading zeros), makes the
request visible in the warning/approval digest, and withdraws the host's
`RestrictRealtime` filter for only that unit. A compatible Core must also be
on the consuming host before approval. See the
[producer record](../../services/sunshine/README.md#rg35xx-pro-linear-kms-60-fps-candidate)
for scope, evidence and removal conditions. This branch does not install or
automatically approve the changed plugin.

## Typed launch service settings

Settings live under `services.'@korri:sunshine/sunshine'.settings` in launch
places, including runner-scoped places (ADR 0038). They are nested objects;
dots in the table name leaf paths, not literal YAML keys. The service has no
`enabled` setting and does not wrap the game's command. korrid resolves the
settings before the game starts, validates them, warns and skips bad paths,
then calls `settings.render`. It atomically writes changed arguments to
`/run/korri-launch-services/korri-sunshine.args` and restarts Sunshine only
when the bytes change. Restarting Sunshine ends its existing stream.

`runtime.sh` reads the optional file at startup and appends each valid
`key=value` line as one argument, after its own arguments. Keys must match
`^[a-z0-9_]+$`; malformed lines are ignored. Values are never evaluated as
shell syntax. An absent or empty file adds nothing. There is no hard-coded
`encoder=auto`. `ProtectSystem=strict` leaves `/run` readable; this adds no
service write permission. korrid owns file creation and restart authority.

Grounding: the approved settings-vocabulary brief and Sunshine
`v2025.924.154138` `docs/configuration.md` / `src/config.cpp`; patch 0037 adds
the vblank offset and patches 0021/0022 add the ARM encoder names. All settings
are optional; an unset path emits nothing and Sunshine keeps its native
behavior. No plugin schema defaults replace Sunshine's own defaults.

| Setting path | Type / choices | Native key |
|---|---|---|
| `logging.level` | none, fatal, error, warning, info, debug, verbose | `min_log_level` |
| `input.controller` | boolean | `controller` |
| `input.gamepad` | auto, ds5, switch, xone | `gamepad` |
| `input.motion-as-ds4` | boolean | `motion_as_ds4` |
| `input.touchpad-as-ds4` | boolean | `touchpad_as_ds4` |
| `input.ds5-random-mac` | boolean | `ds5_inputtino_randomize_mac` |
| `input.back-button-timeout-ms` | integer ≥ -1; -1 disables Guide emulation | `back_button_timeout` |
| `input.keyboard` | boolean | `keyboard` |
| `input.key-repeat.delay-ms` | integer ≥ 0 | `key_repeat_delay` |
| `input.key-repeat.rate-hz` | finite number ≥ 0 | `key_repeat_frequency` |
| `input.right-alt-as-windows-key` | boolean | `key_rightalt_to_key_win` |
| `input.mouse` | boolean | `mouse` |
| `input.high-resolution-scrolling` | boolean | `high_resolution_scrolling` |
| `input.pen-touch` | boolean | `native_pen_touch` |
| `audio.enable` | boolean | `stream_audio` |
| `video.max-bitrate-kbps` | integer ≥ 0; 0 uses the client's request | `max_bitrate` |
| `video.minimum-fps` | integer 0..1000; 0 uses half the stream's fps | `minimum_fps_target` |
| `video.encoder.name` | nvenc, quicksync, amdvce, vaapi, software, v4l2m2m, rkmpp | `encoder` |
| `video.encoder.fec-percent` | integer 1..255 | `fec_percentage` |
| `video.encoder.qp` | integer ≥ 0 | `qp` |
| `video.encoder.min-threads` | integer ≥ 1 | `min_threads` |
| `video.encoder.hevc` | auto, off, main, main10 → 0, 1, 2, 3 | `hevc_mode` |
| `video.encoder.av1` | auto, off, main, main10 → 0, 1, 2, 3 | `av1_mode` |
| `video.encoder.software.preset` | ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow | `sw_preset` |
| `video.encoder.software.tune` | film, animation, grain, stillimage, fastdecode, zerolatency | `sw_tune` |
| `video.capture.vblank-offset-ms` | integer 0..1000 | `capture_vblank_offset_ms` |
| `network.address-family` | ipv4, both | `address_family` |
| `network.external-ip` | string without NUL or line breaks; empty = automatic | `external_ip` |
| `network.lan-encryption` | off, supported, required → 0, 1, 2 | `lan_encryption_mode` |
| `network.wan-encryption` | off, supported, required → 0, 1, 2 | `wan_encryption_mode` |
| `network.ping-timeout-ms` | integer ≥ -1; -1 leaves the native timeout unchanged | `ping_timeout` |

Booleans render as `enabled` / `disabled`. Integer maxima are signed 32-bit
unless the table gives a smaller bound. Choosing an encoder does not promise
that a given device has it; Sunshine still owns hardware capability checks.

### Options with no typed setting

The brief excludes these 56 native options, not hidden settings.

| Native options | Why excluded |
|---|---|
| `file_apps`, `credentials_file`, `pkey`, `cert`, `file_state`, `log_path` | Korri owns files and identity |
| `capture`, `capture_rt_priority` | Set by this plugin's runtime |
| `adapter_name`, `output_name` | Korri chooses the capture device |
| `audio_sink`, `virtual_sink` | PipeWire routing |
| `port`, `upnp`, `origin_web_ui_allowed` | Exposure belongs to plugin firewall rules |
| `global_prep_cmd` | Runs commands; not a typed setting |
| `sunshine_name` | Korri's device label |
| `locale`, `system_tray`, `notify_pre_releases` | No Sunshine UI on the device |
| `always_send_scancodes`, `install_steam_audio_drivers`, `ds4_back_as_touchpad_click`, ten `dd_*` options | Windows only |
| Eight `nvenc_*`, three `qsv_*`, seven `amd_*`, three `vt_*`, `vaapi_strict_rc_buffer` | Hardware no Korri device has; inferred in the brief, not checked per SoC |
| `keybindings` | No list setting kind yet |

### Focused checks (build machines only)

```sh
bun test plugins/sunshine/settings.test.mts
python3 plugins/sunshine/test-runtime.py
nix build --no-link .#checks.x86_64-linux.korri-sunshine-plugin-native
```

The runtime test needs Bash, jq and coreutils in `PATH`; it executes the full
script against local sockets and controlled native commands. The native check
also typechecks the handlers and runs both test files.

Tests use `.mts` so the pinned builder does not ship the test modules in its
plugin source inventory. Production source remains TypeScript `.ts`.

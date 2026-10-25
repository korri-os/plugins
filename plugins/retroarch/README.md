# `@korri:retroarch`

This Linux plugin owns the shared RetroArch family and frontend package.
`plugin.ts` declares the family. `plugin.nix` owns the patched prebuilt
executable, checked settings evidence, and InputPlumber autoconfig payload.
Korrid consumes only administrator-approved installed selections.

Libretro cores are independent plugins. Each generated core package carries
its selected RetroArch frontend, core library, settings evidence, nested policy
and pure cfg renderer in one Nix closure. Installing a core does not install or
approve the `@korri:retroarch` family package.

## Linux typed settings

`policy.ts` preserves the legacy nested policy's fields and constraints, with
only the vocabulary changes in ADR 0037 and the 2026-10-25 settings brief.
Its representation is now dependency-free JSON Schema, not Effect builders:
the empty plugin sandbox evaluates TypeScript source with no external imports.
Renderer types derive from that schema. There is no second user-settings schema.
`settings.describe({ id })` returns the nested schema and this frontend's
version as `revision`. Objects reject additional properties; leaves carry titles,
descriptions, types, limits, choices and the existing safe lifecycle defaults.

The runner receives a nested tree at `launch.prepare.overrides.settings` and
renders it through `render-settings.ts`. Korrid merges one leaf at a time.
`settings.validate({ values, revision })` reports path-segment diagnostics, never
rewrites authored values, and never logs values. An error diagnostic means korrid
skips that path and shows a launch warning, not that the launch stops. The runner
also skips invalid or unverified paths when called directly. A revision mismatch
is informational. RetroArch accepts `video.scaling.scaler: auto | integer`;
`fit`, `fill`, and `stretch` produce diagnostics and no scaler assignment.

A legacy nullable string's null now means "not set". Use the editor's Default or
Inherit. YAML null in a place is a **Cleared setting**: korrid handles it and never
passes it to the plugin. The brief's null examples (camera, location, wallpaper,
camera-device) are cleared values; the resolved schema exposes scalar strings.
The renderer omits absent leaves, just as legacy omitted null.

### Constraint preservation

This table maps every legacy Effect constraint form to the resolved JSON Schema
form. The table below it lists each retained leaf's resulting constraint.

| Legacy Effect constraint | Resolved JSON Schema / behaviour |
| --- | --- |
| `Schema.Struct` with strict excess-property decode | `type: object`, `additionalProperties: false` at every object |
| `Schema.optional` | No leaf is required; absent leaves are omitted |
| `Schema.Boolean` | `type: boolean` |
| `Schema.Number` | `type: number`; JSON numbers are finite |
| `Schema.Int` | `type: integer`, safe-integer bounds (the retained integer fields are non-negative) |
| `PositiveInteger` | `minimum: 1`, `maximum: 9007199254740991` |
| `NonNegativeInteger` | `minimum: 0`, `maximum: 9007199254740991` |
| `PositiveNumber` | `exclusiveMinimum: 0` |
| `NonNegativeNumber` | `minimum: 0` |
| `finiteNumberRange(0, 1)` | `minimum: 0`, `maximum: 1` (axis threshold, deadzone, overlay opacity) |
| `finiteNumberRange(0, 99)` | `minimum: 0`, `maximum: 99` (frame delay) |
| `NonEmptyString` | `type: string`, `minLength: 1` |
| `NullableNonEmptyString` | Same scalar string constraint; Clear/Inherit is handled by korrid, as above |
| Aspect-ratio and gamepad-combo literals | Same named choices and native index mappings |
| Positive-decimal input-port record keys | `patternProperties: ^[1-9][0-9]*$`, closed port objects |
| Environment, generated-config policy, path policy, HTTPS updater URL constraints | Removed under R8, not silently relaxed |
| Integer-coded choice fields | Named choices under R7, retaining the native indices listed below |
| Independent fullscreen width/height | Paired `video.resolution.width/height` under R5 |

The R7 names follow RetroArch **1.22.2** native enums:

| Setting path | Choices in native index order | Pinned source |
| --- | --- | --- |
| `audio.resampler-quality` | `dont-care`, `lowest`, `lower`, `normal`, `higher`, `highest` (0..5) | `libretro-common/include/audio/audio_resampler.h`, `enum resampler_quality` |
| `input.poll-type-behavior` | `early`, `normal`, `late` (0..2) | `retroarch_types.h`, `enum poll_type` |
| `input.auto-game-focus` | `off`, `on`, `detect` (0..2) | `input/input_types.h`, `enum input_auto_game_focus_type` |
| `input.ports.<port>.analog-dpad-mode` | `none`, `left-analog`, `right-analog`, `left-analog-forced`, `right-analog-forced` (0..4) | `input/input_defines.h`, `enum analog_dpad_mode` |
| `logging.core-level` | `debug`, `info`, `warning`, `error` (0..3) | `libretro-common/include/libretro.h`, `enum retro_log_level` |

Each named choice carries a schema title. `logging.level` accepts `info` and
`verbose`. `verbose` emits both legacy `-v` and `log_verbosity = "true"`;
`info` emits no `-v` and sets `log_verbosity = "false"`. No core-level or global
logging level is inferred when absent.

### Typed-setting table

Paths are dotted here for readability; authored values are nested objects, never
dotted property names. `<port>` is a positive decimal port number. The native
column describes rendering, not source admission: the selected program's own
evidence still decides whether each assignment is permitted. Unless stated,
there is no schema default and the runner's baseline or RetroArch decides.

| Setting path | Type / accepted values | Native assignment | Schema default |
| --- | --- | --- | --- |
| `logging.level` | string: `info`, `verbose` | `log_verbosity` | — |
| `logging.core-level` | string: `debug`, `info`, `warning`, `error` | `libretro_log_level` | — |
| `lifecycle.auto-overrides` | boolean | `auto_overrides_enable` | false |
| `lifecycle.auto-remaps` | boolean | `auto_remaps_enable` | false |
| `lifecycle.game-specific-options` | boolean | `game_specific_options` | false |
| `lifecycle.auto-shaders` | boolean | `auto_shaders_enable` | false |
| `lifecycle.show-hidden-files` | boolean | `show_hidden_files` | — |
| `lifecycle.load-dummy-on-core-shutdown` | boolean | `load_dummy_on_core_shutdown` | — |
| `lifecycle.history-list` | boolean | `history_list_enable` | — |
| `lifecycle.performance-counters` | boolean | `perfcnt_enable` | — |
| `lifecycle.all-users-control-menu` | boolean | `all_users_control_menu` | — |
| `lifecycle.suspend-screensaver` | boolean | `suspend_screensaver_enable` | — |
| `lifecycle.sustained-performance-mode` | boolean | `sustained_performance_mode` | — |
| `lifecycle.game-mode` | boolean | `gamemode_enable` | — |
| `drivers.input` | string; non-empty | `input_driver` | — |
| `drivers.joypad` | string; non-empty | `input_joypad_driver` | — |
| `drivers.video` | string; non-empty | `video_driver` | — |
| `drivers.audio` | string; non-empty | `audio_driver` | — |
| `drivers.resampler` | string; non-empty | `audio_resampler` | — |
| `drivers.camera` | string; non-empty | `camera_driver` | — |
| `drivers.location` | string; non-empty | `location_driver` | — |
| `drivers.record` | string; non-empty | `record_driver` | — |
| `video.fullscreen` | boolean | `video_fullscreen` | — |
| `video.windowed-fullscreen` | boolean | `video_windowed_fullscreen` | — |
| `video.refresh-rate-hz` | number; > 0 | `video_refresh_rate` | — |
| `video.vsync` | boolean | `video_vsync` | — |
| `video.aspect-ratio` | string: `config`, `square`, `core-provided`, `custom`, `full` | `aspect_ratio_index` | — |
| `video.aspect-ratio-value` | number; > 0 | `video_aspect_ratio` | — |
| `video.force-aspect` | boolean | `video_force_aspect` | — |
| `video.crop-overscan` | boolean | `video_crop_overscan` | — |
| `video.smooth` | boolean | `video_smooth` | — |
| `video.shader.enable` | boolean | `video_shader_enable` | — |
| `video.shader.path` | string; non-empty | `video_shader` | — |
| `video.shader.watch-files` | boolean | `video_shader_watch_files` | — |
| `video.hdr.enable` | boolean | `video_hdr_enable` | — |
| `video.hdr.max-nits` | number; > 0 | `video_hdr_max_nits` | — |
| `video.hdr.paper-white-nits` | number; > 0 | `video_hdr_paper_white_nits` | — |
| `video.hdr.contrast` | number; > 0 | `video_hdr_contrast` | — |
| `video.hdr.expand-gamut` | boolean | `video_hdr_expand_gamut` | — |
| `video.recording.post-filter` | boolean | `video_post_filter_record` | — |
| `video.recording.gpu` | boolean | `video_gpu_record` | — |
| `video.gpu-screenshot` | boolean | `video_gpu_screenshot` | — |
| `video.sync.hard-sync` | boolean | `video_hard_sync` | — |
| `video.sync.hard-sync-frames` | integer; ≥ 0; ≤ 9007199254740991 | `video_hard_sync_frames` | — |
| `video.sync.frame-delay-ms` | number; ≥ 0; ≤ 99 | `video_frame_delay` | — |
| `video.sync.frame-delay-auto` | boolean | `video_frame_delay_auto` | — |
| `video.resolution.width` | integer; ≥ 0; ≤ 9007199254740991 | `video_fullscreen_x` | — |
| `video.resolution.height` | integer; ≥ 0; ≤ 9007199254740991 | `video_fullscreen_y` | — |
| `video.scaling.scaler` | string: `auto`, `integer` | `video_scale_integer` | — |
| `video.scaling.factor` | number; > 0 | `video_scale` | — |
| `video.stats.fps` | boolean | `fps_show` | — |
| `video.stats.memory` | boolean | `memory_show` | — |
| `video.stats.frame-count` | boolean | `framecount_show` | — |
| `audio.enable` | boolean | `audio_enable` | — |
| `audio.menu-sounds` | boolean | `audio_enable_menu` | — |
| `audio.mute` | boolean | `audio_mute_enable` | — |
| `audio.mixer-mute` | boolean | `audio_mixer_mute_enable` | — |
| `audio.latency-ms` | number; ≥ 0 | `audio_latency` | — |
| `audio.output-rate-hz` | integer; ≥ 1; ≤ 9007199254740991 | `audio_out_rate` | — |
| `audio.sync` | boolean | `audio_sync` | — |
| `audio.rate-control.enable` | boolean | `audio_rate_control` | — |
| `audio.rate-control.delta` | number; > 0 | `audio_rate_control_delta` | — |
| `audio.max-timing-skew` | number; > 0 | `audio_max_timing_skew` | — |
| `audio.volume-db` | number | `audio_volume` | — |
| `audio.mixer-volume-db` | number | `audio_mixer_volume` | — |
| `audio.resampler-quality` | string: `dont-care`, `lowest`, `lower`, `normal`, `higher`, `highest` | `audio_resampler_quality` | — |
| `input.autodetect` | boolean | `input_autodetect_enable` | — |
| `input.max-users` | integer; ≥ 1; ≤ 9007199254740991 | `input_max_users` | — |
| `input.poll-type-behavior` | string: `early`, `normal`, `late` | `input_poll_type_behavior` | — |
| `input.axis-threshold` | number; ≥ 0; ≤ 1 | `input_axis_threshold` | — |
| `input.analog-deadzone` | number; ≥ 0; ≤ 1 | `input_analog_deadzone` | — |
| `input.analog-sensitivity` | number; > 0 | `input_analog_sensitivity` | — |
| `input.remap-binds` | boolean | `input_remap_binds_enable` | — |
| `input.descriptors.label-show` | boolean | `input_descriptor_label_show` | — |
| `input.descriptors.hide-unbound` | boolean | `input_descriptor_hide_unbound` | — |
| `input.overlay.enable` | boolean | `input_overlay_enable` | — |
| `input.overlay.path` | string; non-empty | `input_overlay` | — |
| `input.overlay.opacity` | number; ≥ 0; ≤ 1 | `input_overlay_opacity` | — |
| `input.overlay.scale` | number; > 0 | `input_overlay_scale` | — |
| `input.overlay.behind-menu` | boolean | `input_overlay_behind_menu` | — |
| `input.overlay.hide-in-menu` | boolean | `input_overlay_hide_in_menu` | — |
| `input.auto-game-focus` | string: `off`, `on`, `detect` | `input_auto_game_focus` | — |
| `input.menu-toggle-combo` | string: `none`, `down-y-l-r`, `l3-r3`, `l1-r1-start-select`, `start-select`, `l3-r`, `l-r`, `hold-start`, `hold-select`, `down-select`, `l2-r2` | `input_menu_toggle_gamepad_combo` | — |
| `input.quit-combo` | string: `none`, `down-y-l-r`, `l3-r3`, `l1-r1-start-select`, `start-select`, `l3-r`, `l-r`, `hold-start`, `hold-select`, `down-select`, `l2-r2` | `input_quit_gamepad_combo` | — |
| `input.ports.<port>.libretro-device` | integer; ≥ 0; ≤ 9007199254740991 | `input_libretro_device_p<port>` | — |
| `input.ports.<port>.joypad-index` | integer; ≥ 0; ≤ 9007199254740991 | `input_player<port>_joypad_index` | — |
| `input.ports.<port>.analog-dpad-mode` | string: `none`, `left-analog`, `right-analog`, `left-analog-forced`, `right-analog-forced` | `input_player<port>_analog_dpad_mode` | — |
| `menu.show-start-screen` | boolean | `menu_show_start_screen` | — |
| `menu.pause-core` | boolean | `menu_pause_libretro` | — |
| `menu.mouse` | boolean | `menu_mouse_enable` | — |
| `menu.pointer` | boolean | `menu_pointer_enable` | — |
| `menu.clock` | boolean | `menu_timedate_enable` | — |
| `menu.battery-level` | boolean | `menu_battery_level_enable` | — |
| `menu.core-name` | boolean | `menu_core_enable` | — |
| `menu.dynamic-wallpaper` | boolean | `menu_dynamic_wallpaper_enable` | — |
| `menu.wallpaper` | string; non-empty | `menu_wallpaper` | — |
| `menu.screensaver-timeout-seconds` | integer; ≥ 0; ≤ 9007199254740991 | `menu_screensaver_timeout` | — |
| `saves.autosave-interval-seconds` | integer; ≥ 0; ≤ 9007199254740991 | `autosave_interval` | — |
| `saves.auto-load-state` | boolean | `savestate_auto_load` | — |
| `saves.auto-save-state` | boolean | `savestate_auto_save` | — |
| `saves.auto-index` | boolean | `savestate_auto_index` | — |
| `saves.max-keep` | integer; ≥ 0; ≤ 9007199254740991 | `savestate_max_keep` | — |
| `saves.thumbnail` | boolean | `savestate_thumbnail_enable` | — |
| `saves.sort-savefiles` | boolean | `sort_savefiles_enable` | — |
| `saves.sort-savestates` | boolean | `sort_savestates_enable` | — |
| `saves.block-sram-overwrite` | boolean | `block_sram_overwrite` | — |
| `saves.save-file-compression` | boolean | `save_file_compression` | — |
| `saves.state-file-compression` | boolean | `savestate_file_compression` | — |
| `rewind.enable` | boolean | `rewind_enable` | — |
| `rewind.granularity` | integer; ≥ 1; ≤ 9007199254740991 | `rewind_granularity` | — |
| `rewind.buffer-size-mb` | integer; ≥ 1; ≤ 9007199254740991 | `rewind_buffer_size` | — |
| `rewind.buffer-size-step-mb` | integer; ≥ 1; ≤ 9007199254740991 | `rewind_buffer_size_step` | — |
| `rewind.auto-stride` | boolean | `rewind_auto_stride` | — |
| `playback.pause-when-inactive` | boolean | `pause_nonactive` | — |
| `playback.pause-on-disconnect` | boolean | `pause_on_disconnect` | — |
| `playback.slowmotion-ratio` | number; > 0 | `slowmotion_ratio` | — |
| `playback.fastforward-ratio` | number; ≥ 0 | `fastforward_ratio` | — |
| `playback.fastforward-frameskip` | boolean | `fastforward_frameskip` | — |
| `latency.run-ahead.enable` | boolean | `run_ahead_enabled` | — |
| `latency.run-ahead.frames` | integer; ≥ 0; ≤ 9007199254740991 | `run_ahead_frames` | — |
| `latency.run-ahead.secondary-instance` | boolean | `run_ahead_secondary_instance` | — |
| `latency.run-ahead.hide-warnings` | boolean | `run_ahead_hide_warnings` | — |
| `latency.preemptive-frames.enable` | boolean | `preemptive_frames_enable` | — |
| `latency.preemptive-frames.frames` | integer; ≥ 0; ≤ 9007199254740991 | `preemptive_frames` | — |
| `achievements.enable` | boolean | `cheevos_enable` | — |
| `achievements.username` | string; non-empty | `cheevos_username` | — |
| `achievements.hardcore` | boolean | `cheevos_hardcore_mode_enable` | — |
| `achievements.badges` | boolean | `cheevos_badges_enable` | — |
| `achievements.rich-presence` | boolean | `cheevos_richpresence_enable` | — |
| `achievements.test-unofficial` | boolean | `cheevos_test_unofficial` | — |
| `haptics.vibrate-on-keypress` | boolean | `vibrate_on_keypress` | — |
| `haptics.device-vibration` | boolean | `enable_device_vibration` | — |
| `playlists.use-old-format` | boolean | `playlist_use_old_format` | — |
| `privacy.camera-device` | string; non-empty | `camera_device` | — |
| `privacy.camera` | boolean | `camera_allow` | — |
| `privacy.location` | boolean | `location_allow` | — |
| `updater.show-online-updater` | boolean | `menu_show_online_updater` | — |
| `updater.show-core-updater` | boolean | `menu_show_core_updater` | — |
| `updater.auto-extract-archive` | boolean | `core_updater_auto_extract_archive` | — |

### Options with no typed setting

| Native options / former policy fields | Reason |
| --- | --- |
| `environment` | The cascade's `env` kind owns environment variables. |
| `configFile` | The cascade's `config` kind owns native text; no second config-file policy. |
| `core.path`, `content.path` | Korrid supplies both paths. |
| `logging.logFile` | Korri owns diagnostic files. |
| `audio.device` / `audio_device` | Korri routes audio through PipeWire. |
| `paths.*` (system, save, state, screenshot, content, cache, assets, thumbnails, playlist, libretro, info, core assets/options, autoconfig, remapping, overlays, shaders, cheats, database, runtime log, recording output) | Korri owns storage and save sync. |
| `saves.savefiles-in-content-dir`, `saves.savestates-in-content-dir`, `saves.systemfiles-in-content-dir` | Korri owns the directories; content is not writable storage. |
| `updater.buildbot-url`, `updater.buildbot-assets-url` | Korri installs prebuilt plugin packages. |
| `config_save_on_exit`, `menu_driver` | Reserved kiosk protections; no authored setting. |
| `cheevos_password`, `cheevos_token`, `network_cmd_password`, `netplay_password`, `netplay_spectate_password`, `kiosk_mode_enable` | Reserved credentials and security policy; raw assignment also refused. |

## Per-program source evidence

`settings-types.json` records the **138** fixed cfg outputs of the renderer,
including fixed kiosk/content-browser defaults. The schema-driven test compares
it to the actual renderer. `settings-check.nix` inherits the selected frontend's
unpack/patch phases and checks its own `configuration.c`, never another core's
frontend. It generates `settings.json` and `settings.ts`; the core ships the latter
as source alongside the policy and renderer. Installed plugin code is never
compiled ahead of time.

The pinned **1.22.2** source admits **131** fixed keys. Seven are withheld:
`config_save_on_exit` is reserved; `input_overlay_scale`,
`menu_show_start_screen`, `preemptive_frames`, `rewind_auto_stride`,
`video_hdr_contrast`, and `video_shader` have no verified key. Dynamic input-port
outputs have no evidence yet and produce path-specific warnings. Policy fields
remain described, but unverified outputs are skipped. `libretro_log_level` now
renders a number and passes its source check. Source recognition does not prove
that an optional feature was compiled in.

The family registers this evidence as `packages.retroarch-settings` and
`files.retroarch-settings`. The evidence file is a path inside its package output,
not a bare output. Each core carries the evidence for its exact frontend; the
existing `program` binding chooses it. There is no new catalog or host schema.

## Native serialization and precedence

The runner emits one assignment per native key with precedence **baseline < typed
< raw prepend < raw append**. The last raw assignment wins. Baseline comments
remain; raw blank/comment-only lines are ignored. Raw keys require
`[A-Za-z0-9_]+`; raw values retain native syntax and inline comments. Raw text is
not JSON-decoded. Reserved assignments are rejected even if a later one hides
them. Save, state and screenshot paths remain Korri-owned even in raw text.

RetroArch's pinned `libretro-common/file/config_file.c` uses first-occurrence
lookup (479–488, 977–980). Appending duplicate native lines would not implement
those overrides. Its quote scanner (221–239) stops at the next double quote and
does not decode JSON escapes.

Booleans stay quoted and numbers bare. Quote-free strings are enclosed in native
double quotes without escaping. Literal backslashes, tabs, spaces, `#`, and
Unicode round-trip unchanged. A quote-bearing string uses native bare form only
when all characters are printable ASCII (`!`..`~`), it does not start with a
quote, and any first `#` lies inside the first complete quote pair. This preserves
`hw:"quoted"` and `hw:"dev#1"` without pretending native syntax supports JSON
escapes. NUL, CR, LF, unpaired UTF-16 surrogates and other quote-bearing strings
produce path diagnostics; they are skipped even when raw text would shadow them.
Generated baseline paths use the same safety rules and fail if invalid.

## Focused build-machine checks

```sh
nix run .#korri-retroarch-check
nix build --no-link .#checks.x86_64-linux.korri-retroarch-package
nix build --no-link .#checks.x86_64-linux.korri-retroarch-settings
nix build --no-link .#checks.x86_64-linux.korri-libretro-typecheck
```

The settings gate runs Python source-recognition tests and the nested callback
suite against the exact selected frontend's evidence. It compiles that program's
native config parser and file/path adapters with a **build-machine** compiler.
`plugin.sandbox-test.ts` sends emitted files through `config_file_new` and checks
`config_get_string` values, including precedence, named choices and native string
round-trips. `KORRI_TEST_RETROARCH_CONFIG_PARSER` makes those checks mandatory;
standalone Bun tests without it skip the native cases and do not replace this
gate. No parser logic is copied into the probe. The packaged declarations stay
source. No check boots a VM or runs a game; uncached program builds can be costly.
Never run builds or dispatch them from a target device.

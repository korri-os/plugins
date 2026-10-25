// Legacy cfg renderer with the approved nested setting paths (ADR 0037).
import { RetroArchPolicy as schema, type LaunchSettingValue, type RetroArchPolicy } from "./policy"

const SAFE_LIFECYCLE_DEFAULTS = {
  "auto-overrides": schema.properties.lifecycle.properties["auto-overrides"].default,
  "auto-remaps": schema.properties.lifecycle.properties["auto-remaps"].default,
  "game-specific-options": schema.properties.lifecycle.properties["game-specific-options"].default,
  "auto-shaders": schema.properties.lifecycle.properties["auto-shaders"].default,
}

const SAFE_CONTENT_BROWSER_DEFAULTS = {
  builtinImageViewer: false,
} as const

export function renderRetroArchSettings(
  policy: RetroArchPolicy,
  includeDefaults = true,
): readonly (readonly [string, LaunchSettingValue])[] {
  const writer = createTypedSettingsWriter()

  appendLifecycleSettings(writer, policy, includeDefaults)
  appendLoggingSettings(writer, policy)
  appendDriverSettings(writer, policy)
  appendVideoSettings(writer, policy)
  appendAudioSettings(writer, policy)
  appendInputSettings(writer, policy)
  appendMenuSettings(writer, policy)
  appendSaveSettings(writer, policy)
  appendRewindSettings(writer, policy)
  appendPlaybackSettings(writer, policy)
  appendLatencySettings(writer, policy)
  if (includeDefaults) appendContentBrowserSettings(writer)
  appendAdvancedSettings(writer, policy)

  return [...writer.settings]
}

interface TypedSettingsWriter {
  readonly settings: Array<readonly [string, LaunchSettingValue]>
  readonly seenKeys: Set<string>
}

function createTypedSettingsWriter(): TypedSettingsWriter {
  return { settings: [], seenKeys: new Set() }
}

function appendLifecycleSettings(
  writer: TypedSettingsWriter,
  policy: RetroArchPolicy,
  includeDefaults: boolean,
) {
  const lifecycle = { ...(includeDefaults ? SAFE_LIFECYCLE_DEFAULTS : {}), ...policy.lifecycle }

  if (includeDefaults) pushTypedSetting(writer, "config_save_on_exit", false)
  pushTypedSetting(writer, "auto_overrides_enable", lifecycle["auto-overrides"])
  pushTypedSetting(writer, "auto_remaps_enable", lifecycle["auto-remaps"])
  pushTypedSetting(writer, "game_specific_options", lifecycle["game-specific-options"])
  pushTypedSetting(writer, "auto_shaders_enable", lifecycle["auto-shaders"])
  pushTypedSetting(writer, "show_hidden_files", policy.lifecycle?.["show-hidden-files"])
  pushTypedSetting(
    writer,
    "load_dummy_on_core_shutdown",
    policy.lifecycle?.["load-dummy-on-core-shutdown"],
  )
  pushTypedSetting(writer, "history_list_enable", policy.lifecycle?.["history-list"])
  pushTypedSetting(writer, "perfcnt_enable", policy.lifecycle?.["performance-counters"])
  pushTypedSetting(writer, "all_users_control_menu", policy.lifecycle?.["all-users-control-menu"])
  pushTypedSetting(writer, "suspend_screensaver_enable", policy.lifecycle?.["suspend-screensaver"])
  pushTypedSetting(
    writer,
    "sustained_performance_mode",
    policy.lifecycle?.["sustained-performance-mode"],
  )
  pushTypedSetting(writer, "gamemode_enable", policy.lifecycle?.["game-mode"])
}

function appendLoggingSettings(writer: TypedSettingsWriter, policy: RetroArchPolicy) {
  pushTypedSetting(
    writer,
    "log_verbosity",
    policy.logging?.level === undefined ? undefined : policy.logging.level === "verbose",
  )
  pushTypedSetting(
    writer,
    "libretro_log_level",
    namedIndex(
      policy.logging?.["core-level"],
      schema.properties.logging.properties["core-level"].enum,
    ),
  )
  pushTypedSetting(writer, "fps_show", policy.video?.stats?.fps)
  pushTypedSetting(writer, "memory_show", policy.video?.stats?.memory)
  pushTypedSetting(writer, "framecount_show", policy.video?.stats?.["frame-count"])
}

function namedIndex(value: string | undefined, choices: readonly string[]): number | undefined {
  return value === undefined ? undefined : choices.indexOf(value)
}

function appendDriverSettings(writer: TypedSettingsWriter, policy: RetroArchPolicy) {
  pushTypedSetting(writer, "input_driver", policy.drivers?.input)
  pushTypedSetting(writer, "input_joypad_driver", policy.drivers?.joypad)
  pushTypedSetting(writer, "video_driver", policy.drivers?.video)
  pushTypedSetting(writer, "audio_driver", policy.drivers?.audio)
  pushTypedSetting(writer, "audio_resampler", policy.drivers?.resampler)
  pushTypedSetting(writer, "camera_driver", policy.drivers?.camera)
  pushTypedSetting(writer, "location_driver", policy.drivers?.location)
  pushTypedSetting(writer, "record_driver", policy.drivers?.record)
}

type RetroArchVideoPolicy = NonNullable<RetroArchPolicy["video"]>
type RetroArchAudioPolicy = NonNullable<RetroArchPolicy["audio"]>
type RetroArchInputPolicy = NonNullable<RetroArchPolicy["input"]>
type RetroArchMenuPolicy = NonNullable<RetroArchPolicy["menu"]>
type RetroArchSavesPolicy = NonNullable<RetroArchPolicy["saves"]>
type RetroArchRewindPolicy = NonNullable<RetroArchPolicy["rewind"]>
type RetroArchPlaybackPolicy = NonNullable<RetroArchPolicy["playback"]>
type RetroArchLatencyPolicy = NonNullable<RetroArchPolicy["latency"]>
type RetroArchAchievementsPolicy = NonNullable<RetroArchPolicy["achievements"]>
type RetroArchHapticsPolicy = NonNullable<RetroArchPolicy["haptics"]>
type RetroArchPlaylistsPolicy = NonNullable<RetroArchPolicy["playlists"]>
type RetroArchPrivacyPolicy = NonNullable<RetroArchPolicy["privacy"]>
type RetroArchUpdaterPolicy = NonNullable<RetroArchPolicy["updater"]>
type SettingSelector<T> = (source: T) => LaunchSettingValue | null | undefined

type SettingEntry<T> = readonly [string, SettingSelector<T>]

const RETROARCH_ASPECT_RATIO_INDEX: Record<RetroArchVideoPolicy["aspect-ratio"] & string, number> =
  {
    config: 20,
    square: 21,
    "core-provided": 22,
    custom: 23,
    full: 24,
  }

const RETROARCH_GAMEPAD_COMBO_INDEX: Record<
  RetroArchInputPolicy["menu-toggle-combo"] & string,
  number
> = {
  none: 0,
  "down-y-l-r": 1,
  "l3-r3": 2,
  "l1-r1-start-select": 3,
  "start-select": 4,
  "l3-r": 5,
  "l-r": 6,
  "hold-start": 7,
  "hold-select": 8,
  "down-select": 9,
  "l2-r2": 10,
}

const VIDEO_SETTINGS: readonly SettingEntry<RetroArchVideoPolicy>[] = [
  ["video_fullscreen", video => video.fullscreen],
  ["video_windowed_fullscreen", video => video["windowed-fullscreen"]],
  ["video_fullscreen_x", video => video.resolution?.width],
  ["video_fullscreen_y", video => video.resolution?.height],
  ["video_refresh_rate", video => video["refresh-rate-hz"]],
  ["video_vsync", video => video.vsync],
  ["aspect_ratio_index", video => mapRetroArchAspectRatio(video["aspect-ratio"])],
  ["video_aspect_ratio", video => video["aspect-ratio-value"]],
  ["video_force_aspect", video => video["force-aspect"]],
  ["video_scale", video => video.scaling?.factor],
  [
    "video_scale_integer",
    video => (video.scaling?.scaler === undefined ? undefined : video.scaling.scaler === "integer"),
  ],
  ["video_crop_overscan", video => video["crop-overscan"]],
  ["video_smooth", video => video.smooth],
  ["video_shader", video => video.shader?.path],
  ["video_shader_enable", video => video.shader?.enable],
  ["video_gpu_screenshot", video => video["gpu-screenshot"]],
  ["video_shader_watch_files", video => video.shader?.["watch-files"]],
]

const VIDEO_HDR_SETTINGS: readonly SettingEntry<NonNullable<RetroArchVideoPolicy["hdr"]>>[] = [
  ["video_hdr_enable", hdr => hdr.enable],
  ["video_hdr_max_nits", hdr => hdr["max-nits"]],
  ["video_hdr_paper_white_nits", hdr => hdr["paper-white-nits"]],
  ["video_hdr_contrast", hdr => hdr.contrast],
  ["video_hdr_expand_gamut", hdr => hdr["expand-gamut"]],
]

const VIDEO_RECORDING_SETTINGS: readonly SettingEntry<
  NonNullable<RetroArchVideoPolicy["recording"]>
>[] = [
  ["video_post_filter_record", recording => recording["post-filter"]],
  ["video_gpu_record", recording => recording.gpu],
]

const VIDEO_SYNC_SETTINGS: readonly SettingEntry<NonNullable<RetroArchVideoPolicy["sync"]>>[] = [
  ["video_hard_sync", sync => sync["hard-sync"]],
  ["video_hard_sync_frames", sync => sync["hard-sync-frames"]],
  ["video_frame_delay", sync => sync["frame-delay-ms"]],
  ["video_frame_delay_auto", sync => sync["frame-delay-auto"]],
]

const AUDIO_SETTINGS: readonly SettingEntry<RetroArchAudioPolicy>[] = [
  ["audio_enable", audio => audio.enable],
  ["audio_enable_menu", audio => audio["menu-sounds"]],
  ["audio_mute_enable", audio => audio.mute],
  ["audio_mixer_mute_enable", audio => audio["mixer-mute"]],
  ["audio_out_rate", audio => audio["output-rate-hz"]],
  ["audio_sync", audio => audio.sync],
  ["audio_latency", audio => audio["latency-ms"]],
  ["audio_rate_control", audio => audio["rate-control"]?.enable],
  ["audio_rate_control_delta", audio => audio["rate-control"]?.delta],
  ["audio_max_timing_skew", audio => audio["max-timing-skew"]],
  ["audio_volume", audio => audio["volume-db"]],
  ["audio_mixer_volume", audio => audio["mixer-volume-db"]],
  [
    "audio_resampler_quality",
    audio =>
      namedIndex(
        audio["resampler-quality"],
        schema.properties.audio.properties["resampler-quality"].enum,
      ),
  ],
]

const INPUT_SETTINGS: readonly SettingEntry<RetroArchInputPolicy>[] = [
  ["input_autodetect_enable", input => input.autodetect],
  ["input_max_users", input => input["max-users"]],
  [
    "input_poll_type_behavior",
    input =>
      namedIndex(
        input["poll-type-behavior"],
        schema.properties.input.properties["poll-type-behavior"].enum,
      ),
  ],
  ["input_axis_threshold", input => input["axis-threshold"]],
  ["input_analog_deadzone", input => input["analog-deadzone"]],
  ["input_analog_sensitivity", input => input["analog-sensitivity"]],
  ["input_remap_binds_enable", input => input["remap-binds"]],
  [
    "input_auto_game_focus",
    input =>
      namedIndex(
        input["auto-game-focus"],
        schema.properties.input.properties["auto-game-focus"].enum,
      ),
  ],
  [
    "input_menu_toggle_gamepad_combo",
    input => mapRetroArchGamepadCombo(input["menu-toggle-combo"]),
  ],
  ["input_quit_gamepad_combo", input => mapRetroArchGamepadCombo(input["quit-combo"])],
]

const INPUT_DESCRIPTOR_SETTINGS: readonly SettingEntry<
  NonNullable<RetroArchInputPolicy["descriptors"]>
>[] = [
  ["input_descriptor_label_show", descriptors => descriptors["label-show"]],
  ["input_descriptor_hide_unbound", descriptors => descriptors["hide-unbound"]],
]

const INPUT_OVERLAY_SETTINGS: readonly SettingEntry<
  NonNullable<RetroArchInputPolicy["overlay"]>
>[] = [
  ["input_overlay_enable", overlay => overlay.enable],
  ["input_overlay", overlay => overlay.path],
  ["input_overlay_opacity", overlay => overlay.opacity],
  ["input_overlay_scale", overlay => overlay.scale],
  ["input_overlay_behind_menu", overlay => overlay["behind-menu"]],
  ["input_overlay_hide_in_menu", overlay => overlay["hide-in-menu"]],
]

const MENU_SETTINGS: readonly SettingEntry<RetroArchMenuPolicy>[] = [
  ["menu_show_start_screen", menu => menu["show-start-screen"]],
  ["menu_pause_libretro", menu => menu["pause-core"]],
  ["menu_mouse_enable", menu => menu.mouse],
  ["menu_pointer_enable", menu => menu.pointer],
  ["menu_timedate_enable", menu => menu.clock],
  ["menu_battery_level_enable", menu => menu["battery-level"]],
  ["menu_core_enable", menu => menu["core-name"]],
  ["menu_dynamic_wallpaper_enable", menu => menu["dynamic-wallpaper"]],
  ["menu_wallpaper", menu => menu.wallpaper],
  ["menu_screensaver_timeout", menu => menu["screensaver-timeout-seconds"]],
]

const SAVE_SETTINGS: readonly SettingEntry<RetroArchSavesPolicy>[] = [
  ["autosave_interval", saves => saves["autosave-interval-seconds"]],
  ["savestate_auto_load", saves => saves["auto-load-state"]],
  ["savestate_auto_save", saves => saves["auto-save-state"]],
  ["savestate_auto_index", saves => saves["auto-index"]],
  ["savestate_max_keep", saves => saves["max-keep"]],
  ["savestate_thumbnail_enable", saves => saves.thumbnail],
  ["sort_savefiles_enable", saves => saves["sort-savefiles"]],
  ["sort_savestates_enable", saves => saves["sort-savestates"]],
  ["block_sram_overwrite", saves => saves["block-sram-overwrite"]],
  ["save_file_compression", saves => saves["save-file-compression"]],
  ["savestate_file_compression", saves => saves["state-file-compression"]],
]

const REWIND_SETTINGS: readonly SettingEntry<RetroArchRewindPolicy>[] = [
  ["rewind_enable", rewind => rewind.enable],
  ["rewind_granularity", rewind => rewind.granularity],
  ["rewind_buffer_size", rewind => rewind["buffer-size-mb"]],
  ["rewind_buffer_size_step", rewind => rewind["buffer-size-step-mb"]],
  ["rewind_auto_stride", rewind => rewind["auto-stride"]],
]

const PLAYBACK_SETTINGS: readonly SettingEntry<RetroArchPlaybackPolicy>[] = [
  ["pause_nonactive", playback => playback["pause-when-inactive"]],
  ["pause_on_disconnect", playback => playback["pause-on-disconnect"]],
  ["slowmotion_ratio", playback => playback["slowmotion-ratio"]],
  ["fastforward_ratio", playback => playback["fastforward-ratio"]],
  ["fastforward_frameskip", playback => playback["fastforward-frameskip"]],
]

const RUN_AHEAD_SETTINGS: readonly SettingEntry<
  NonNullable<RetroArchLatencyPolicy["run-ahead"]>
>[] = [
  ["run_ahead_enabled", runAhead => runAhead.enable],
  ["run_ahead_frames", runAhead => runAhead.frames],
  ["run_ahead_secondary_instance", runAhead => runAhead["secondary-instance"]],
  ["run_ahead_hide_warnings", runAhead => runAhead["hide-warnings"]],
]

const PREEMPTIVE_FRAME_SETTINGS: readonly SettingEntry<
  NonNullable<RetroArchLatencyPolicy["preemptive-frames"]>
>[] = [
  ["preemptive_frames_enable", preemptiveFrames => preemptiveFrames.enable],
  ["preemptive_frames", preemptiveFrames => preemptiveFrames.frames],
]

const ACHIEVEMENT_SETTINGS: readonly SettingEntry<RetroArchAchievementsPolicy>[] = [
  ["cheevos_enable", achievements => achievements.enable],
  ["cheevos_username", achievements => achievements.username],
  ["cheevos_hardcore_mode_enable", achievements => achievements.hardcore],
  ["cheevos_badges_enable", achievements => achievements.badges],
  ["cheevos_richpresence_enable", achievements => achievements["rich-presence"]],
  ["cheevos_test_unofficial", achievements => achievements["test-unofficial"]],
]

const HAPTIC_SETTINGS: readonly SettingEntry<RetroArchHapticsPolicy>[] = [
  ["vibrate_on_keypress", haptics => haptics["vibrate-on-keypress"]],
  ["enable_device_vibration", haptics => haptics["device-vibration"]],
]

const PLAYLIST_SETTINGS: readonly SettingEntry<RetroArchPlaylistsPolicy>[] = [
  ["playlist_use_old_format", playlists => playlists["use-old-format"]],
]

const PRIVACY_SETTINGS: readonly SettingEntry<RetroArchPrivacyPolicy>[] = [
  ["camera_device", privacy => privacy["camera-device"]],
  ["camera_allow", privacy => privacy.camera],
  ["location_allow", privacy => privacy.location],
]

const UPDATER_SETTINGS: readonly SettingEntry<RetroArchUpdaterPolicy>[] = [
  ["menu_show_online_updater", updater => updater["show-online-updater"]],
  ["menu_show_core_updater", updater => updater["show-core-updater"]],
  ["core_updater_auto_extract_archive", updater => updater["auto-extract-archive"]],
]

function appendVideoSettings(writer: TypedSettingsWriter, policy: RetroArchPolicy) {
  appendOptionalSettings(writer, policy.video, VIDEO_SETTINGS)
  appendOptionalSettings(writer, policy.video?.hdr, VIDEO_HDR_SETTINGS)
  appendOptionalSettings(writer, policy.video?.recording, VIDEO_RECORDING_SETTINGS)
  appendOptionalSettings(writer, policy.video?.sync, VIDEO_SYNC_SETTINGS)
}

function appendAudioSettings(writer: TypedSettingsWriter, policy: RetroArchPolicy) {
  appendOptionalSettings(writer, policy.audio, AUDIO_SETTINGS)
}

function appendInputSettings(writer: TypedSettingsWriter, policy: RetroArchPolicy) {
  appendOptionalSettings(writer, policy.input, INPUT_SETTINGS)
  appendOptionalSettings(writer, policy.input?.descriptors, INPUT_DESCRIPTOR_SETTINGS)
  appendOptionalSettings(writer, policy.input?.overlay, INPUT_OVERLAY_SETTINGS)
  appendInputPortSettings(writer, policy.input?.ports)
}

function appendMenuSettings(writer: TypedSettingsWriter, policy: RetroArchPolicy) {
  appendOptionalSettings(writer, policy.menu, MENU_SETTINGS)
}

function appendSaveSettings(writer: TypedSettingsWriter, policy: RetroArchPolicy) {
  appendOptionalSettings(writer, policy.saves, SAVE_SETTINGS)
}

function appendRewindSettings(writer: TypedSettingsWriter, policy: RetroArchPolicy) {
  appendOptionalSettings(writer, policy.rewind, REWIND_SETTINGS)
}

function appendPlaybackSettings(writer: TypedSettingsWriter, policy: RetroArchPolicy) {
  appendOptionalSettings(writer, policy.playback, PLAYBACK_SETTINGS)
}

function appendLatencySettings(writer: TypedSettingsWriter, policy: RetroArchPolicy) {
  appendOptionalSettings(writer, policy.latency?.["run-ahead"], RUN_AHEAD_SETTINGS)
  appendOptionalSettings(writer, policy.latency?.["preemptive-frames"], PREEMPTIVE_FRAME_SETTINGS)
}

function appendContentBrowserSettings(writer: TypedSettingsWriter) {
  // PICO-8 carts commonly use .p8.png; RetroArch's image viewer can otherwise
  // intercept those PNG carts before the selected fake-08 core sees them.
  pushTypedSetting(
    writer,
    "builtin_imageviewer_enable",
    SAFE_CONTENT_BROWSER_DEFAULTS.builtinImageViewer,
  )
}

function appendAdvancedSettings(writer: TypedSettingsWriter, policy: RetroArchPolicy) {
  appendOptionalSettings(writer, policy.achievements, ACHIEVEMENT_SETTINGS)
  appendOptionalSettings(writer, policy.haptics, HAPTIC_SETTINGS)
  appendOptionalSettings(writer, policy.playlists, PLAYLIST_SETTINGS)
  appendOptionalSettings(writer, policy.privacy, PRIVACY_SETTINGS)
  appendOptionalSettings(writer, policy.updater, UPDATER_SETTINGS)
}

function appendOptionalSettings<T>(
  writer: TypedSettingsWriter,
  source: T | undefined,
  entries: readonly SettingEntry<T>[],
) {
  if (source === undefined) return
  for (const [key, select] of entries) pushTypedSetting(writer, key, select(source))
}

function mapRetroArchAspectRatio(
  value: RetroArchVideoPolicy["aspect-ratio"] | undefined,
): number | undefined {
  return value === undefined ? undefined : RETROARCH_ASPECT_RATIO_INDEX[value]
}

function mapRetroArchGamepadCombo(
  value: RetroArchInputPolicy["menu-toggle-combo"] | undefined,
): number | undefined {
  return value === undefined ? undefined : RETROARCH_GAMEPAD_COMBO_INDEX[value]
}

function appendInputPortSettings(
  writer: TypedSettingsWriter,
  ports: RetroArchInputPolicy["ports"] | undefined,
) {
  if (ports === undefined) return

  for (const port of Object.keys(ports).sort(compareNumericStrings)) {
    const settings = ports[port]
    if (settings === undefined) continue
    pushTypedSetting(writer, `input_libretro_device_p${port}`, settings["libretro-device"])
    pushTypedSetting(writer, `input_player${port}_joypad_index`, settings["joypad-index"])
    pushTypedSetting(
      writer,
      `input_player${port}_analog_dpad_mode`,
      namedIndex(
        settings["analog-dpad-mode"],
        schema.properties.input.properties.ports.patternProperties["^[1-9][0-9]*$"].properties[
          "analog-dpad-mode"
        ].enum,
      ),
    )
  }
}

function compareNumericStrings(left: string, right: string): number {
  return Number(left) - Number(right)
}

function pushTypedSetting(
  writer: TypedSettingsWriter,
  key: string,
  value: LaunchSettingValue | null | undefined,
) {
  if (value === undefined || value === null) return
  if (writer.seenKeys.has(key)) {
    throw new Error(`Duplicate RetroArch typed cfg key rendered: ${key}`)
  }
  writer.seenKeys.add(key)
  writer.settings.push([key, value])
}

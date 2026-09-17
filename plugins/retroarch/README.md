# `@korri:retroarch`

This Linux plugin owns the shared RetroArch family and frontend package.
`plugin.ts` declares the family. `plugin.nix` owns the patched prebuilt
executable, checked settings evidence, and InputPlumber autoconfig payload.
Korrid consumes only administrator-approved installed selections.

Libretro cores are independent plugins. Each generated core package carries
its selected RetroArch frontend, core library, settings evidence, and launch
helper in one Nix closure. Installing one core does not install or approve the
`@korri:retroarch` family package.

## Linux typed settings

The nested schema in `policy.ts` is the unchanged legacy RetroArch policy
(`legacy:product/plugins/retroarch/src/policy.ts`, Effect `4.0.0-beta.78`).
`render-settings.ts` extracts only the pure cfg-pair renderer from legacy
`launch-spec.ts`; it retains nested names, enums, defaults and null omission.
It does not port argv, environment or persistence. The callback consumes
**rendered scalar pairs**, not a new flat user-settings schema. Supplying and
persisting nested policy through the host remains an unresolved integration
boundary; do not encode it in the scalar `overrides.settings` map.

`settings-types.json` is the kind-owned table of all 166 fixed renderer output
keys and their scalar types. The schema-driven test checks it against the
actual renderer. `settings-check.nix` accepts an instance's own `program`;
it inherits that program's unpack/patch phases and checks its
`configuration.c`. It derives the executable path as `${program}/bin/retroarch`,
like the existing manifest file producer. It does not compile plugin code. The installed declaration
remains TS source evaluated by korrid at runtime.

`plugin.nix` registers the generated evidence under the existing
`packages.retroarch-settings` and `files.retroarch-settings`. The evidence
is `settings.json` inside that package's output: the host names a file as a
path inside a store output and refuses a bare output at inspection. The generic
consumer derives the file key from the launcher's existing `program` file key.
Artifact fields have existing consumers: `program` is the exact callback
executable path; `version` and `keys` are `SourceCheckedSettings` evidence.
The consumer checks that executable before binding the enclosing installed
plugin package as `build`. It never reads evidence from the kind package for
another instance. No second catalog, manifest extension, `since` table, user
schema or runtime migration exists.

For the pinned 1.22.2 source, 155 keys match. Eleven are withheld:
`config_save_on_exit` and `menu_driver` are reserved; `libretro_log_level` is a
legacy String but a source Number; `content_directory`,
`core_updater_buildbot_url`, `input_overlay_scale`, `menu_show_start_screen`,
`preemptive_frames`, `rewind_auto_stride`, `video_hdr_contrast`, and
`video_shader` have no verified key. Dynamic input-port outputs also have no
evidence yet. These remain legacy policy fields; they are not silently renamed,
coerced or admitted. Requests produce warnings with setting, launcher, version
and exact build. Source recognition does not prove conditional feature support.

The callback rejects reserved keys in both typed and raw input, even when a
later assignment would hide them. It emits one native assignment per key with
precedence **baseline < typed < raw prepend < raw append**. The last assignment
within a raw block wins. Baseline comments remain; raw blank/comment-only lines
are ignored as before. Raw keys still require `[A-Za-z0-9_]+`; raw values retain
native syntax, including inline comments. Raw input is not JSON-decoded.

This corrects legacy serializer behavior, not the byte-identical legacy policy
input schema. New evidence from the pinned RetroArch 1.22.2
`libretro-common/file/config_file.c` shows first-occurrence lookup
(lines 479–488, 977–980), not last-occurrence lookup. Appending duplicate lines
did not implement the intended overrides. Its quote scanner (lines 221–239)
stops at the next double quote and does not decode JSON escapes. The old
`device "quoted"` input fixture therefore read as `device ` followed by a backslash,
not the supplied value.

Booleans stay quoted and numbers stay bare. Quote-free strings are enclosed in
native double quotes **without escaping**: literal backslashes, tabs, spaces,
`#`, and Unicode round-trip unchanged. A string containing double quotes uses
the native bare form only when all characters are printable ASCII (`!` through
`~`), it does not start with a double quote, and any first `#` is inside the
first complete quote pair. This preserves values such as `hw:"quoted"` and
`hw:"dev#1"` without pretending native syntax supports JSON escapes.

The callback rejects NUL, CR, LF, unpaired UTF-16 surrogates, and quote-bearing
strings that do not meet those bare-form rules (for example `device "quoted"`).
It throws `Unsupported RetroArch string setting: <key>` without including the
value. The same validation applies to generated baseline paths and to typed
values even when raw input would override them. No file declaration is returned
on failure. This is serializer validation, not a callback-output permission
change or nested-policy ingress implementation.

Focused build-machine verification uses the repository checks:

```sh
nix run .#korri-retroarch-check
nix build --no-link .#checks.x86_64-linux.korri-retroarch-package
nix build --no-link .#checks.x86_64-linux.korri-retroarch-settings
```

The settings check runs
the Python source-recognition tests and checks the pinned patched source. It
also compiles that program's actual native config parser and file/path adapters
with a **build-machine** compiler. `plugin.test.ts` sends the callback's emitted
files through `config_file_new` and asserts `config_get_string` values, including
precedence and string round-trips. The check supplies
`KORRI_TEST_RETROARCH_CONFIG_PARSER` to make these semantic tests mandatory;
standalone `bun test` without that executable skips the three native tests and
is not a substitute for the Nix gate. No parser logic is copied into the probe.

Building the plugin also requires this evidence. The packaged Rust callback
test reads the real manifest, evidence and shipped TS, then checks its emitted
configuration bytes. The focused Rust tests also check rejection through the
actual QuickJS callback evaluator. No check boots a VM or runs a game. An
uncached native program dependency can make this build-machine gate expensive;
it must never run on a target device.

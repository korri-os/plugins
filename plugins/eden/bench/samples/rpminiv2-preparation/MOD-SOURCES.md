# SMO mod source audit — 2026-10-23 UTC

**Candidates only. No mod was installed, benchmarked or bundled.**
Downloaded patch-only archives remain in host scratch
`/tmp/eden-mini-mods-20261023/`, outside Git. No proprietary game payload,
firmware or keys are there. Source availability does not establish a speedup.

## Archived patches inspected

Pinned archive repository:
[`yuzu-mirror/yuzu-mod-archive` at `26fe6b257e61ac96edfc3ad5839f41727a7d70b5`](https://github.com/yuzu-mirror/yuzu-mod-archive/tree/26fe6b257e61ac96edfc3ad5839f41727a7d70b5).
Its actual root `LICENSE` is **The Unlicense**; the README credits theboy181 for
these SMO mods. The archives contain no separate licence. That repository-level
notice is not proof of a separate grant from every original author. Keep these
as account-local test inputs, never package them as plugin defaults.

Each link below pins the inspected archive bytes. All four include a native
`exefs/1.0.0.pchtxt`; dynamic-resolution and FXAA archives also contain other
versions. Load only the version that matches the actual game's NSO build ID.
The 1.0.0 files declare build-ID prefix
`<eden-profile-3>`. Eden pads native IDs to 64 hex digits
(`ips_layer.cpp:225–228`, `patch_manager.cpp:348–379`). A filename/version claim
alone is not proof of application.

| Candidate/source URL | Archive bytes | Archive SHA256 | Limitation |
|---|---:|---|---|
| [Disable Dynamic Resolution](https://raw.githubusercontent.com/yuzu-mirror/yuzu-mod-archive/26fe6b257e61ac96edfc3ad5839f41727a7d70b5/files/Super%20Mario%20Odyssey/Disable_Dynamic_Resolution.zip) | 1,560 | `85ce7e4975055733892e49f6c57b38ddc3930a5cdd322b89516a96119d01d05b` | A fixed high resolution can be slower than native dynamic resolution; bench before keeping. |
| [Disable FXAA](https://raw.githubusercontent.com/yuzu-mirror/yuzu-mod-archive/26fe6b257e61ac96edfc3ad5839f41727a7d70b5/files/Super%20Mario%20Odyssey/Disable_FXAA.zip) | 1,028 | `65f8bbbdc16a8a104de0fe408becd561ad43d75f2d137d1945ea03b039c80b8e` | Removes game AA, not merely Eden's separate AA option. |
| [Disable Camera Motion Blur](https://raw.githubusercontent.com/yuzu-mirror/yuzu-mod-archive/26fe6b257e61ac96edfc3ad5839f41727a7d70b5/files/Super%20Mario%20Odyssey/Disable_Camera_Motion_Blur.zip) | 770 | `9a8b6ed3f0bcd859df2db351dacaf1923d2af76ef8c8d185ca9d88435df23a3b` | Static reference may not show a gain; does not prove open-area performance. |
| [Disable Deferred Shading](https://raw.githubusercontent.com/yuzu-mirror/yuzu-mod-archive/26fe6b257e61ac96edfc3ad5839f41727a7d70b5/files/Super%20Mario%20Odyssey/Disable_Deferred_Shading.zip) | 787 | `129fb0ff4e7631545a356b19051932ecedbc02347a95f7283ddd929ea89abaff` | README describes an AMD Navi shadow fix, not an A650 optimization. Original patch also credits kenshi. Test only if warranted; image correctness can worsen. |

Actual Eden v0.2.1 `BISFactory::GetModificationLoadRoot`
(`src/core/file_sys/bis_factory.cpp:54–58`) derives a title directory below its
native load root. `patch_manager.cpp:348–451` reads `<mod>/exefs`, respects
native disabled-add-on choices, matches the full NSO build ID, and logs
“Applying IPSwitch patch” or “Applying IPS patch”. Archive availability, placing
a folder, or booting without an error is not enough. Require this fresh native
application evidence for each rung. Back up pre-existing account mods first;
never remove or overwrite a person's mod while restoring only our additions.

## Resolution/cap candidates not yet usable

| Source checked | Verified fact | Missing evidence / cost |
|---|---|---|
| [GameBanana Upscaling Settings](https://gamebanana.com/mods/49047) | Public search API identifies RagdollClash's SMO entry with that title, version 1.0, marked obsolete. The existing April Ryujinx operational note describes its 960×540 **docked** pchtxt section. | Detail/download API returned HTTP 403. Archive bytes, current licence and exact native patch sections were not obtained. Do not claim a verified 540p/360p handheld patch. Docked mode is a separate factor from the patch. |
| [theboy181/switch-ptchtxt-mods](https://github.com/theboy181/switch-ptchtxt-mods) | Actual GitHub repository metadata has no licence, and its SMO 1.0.0 tree currently lists ultrawide and friends archives. | No verified 30 FPS, 540p or 360p patch was found there. Do not rely on the research brief's generic repository claim. |
| Research brief and audit | Host reference only: `~/.cache/research/switch-aarch64-update-20261022T231212/audit.md` corrects unsupported community FPS claims. | No measured Mini/Linux/Turnip speedup. Do not present estimated FPS or an unverified patch offset as evidence. |

No 30 FPS game patch, shadow-reduction patch or 360p patch is prepared. Native
Eden resolution scaling is independently available for rung 3. Native frame
pacing/host presentation caps are not automatically equivalent to a correct
30 FPS game-speed patch. Do not invent opcode offsets or claim a new patch is
public domain solely because it is short.

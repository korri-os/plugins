# Odin Vulkan device selection — 2026-10-23

**Verified cause: Eden reorders the Vulkan devices and defaults to the CPU renderer.** This is not missing render-node access or a hidden Turnip ICD.

## Real game-unit probe

Launch `0fa1444896386d6cdb7b6725ffb4aa3b` used the admitted personal Eden runner and Gamescope through korrid. A prebuilt, signature-checked Vulkan Tools 1.4.363.0 closure came from cache.nixos.org, was signed on <build-host>, and arrived through `nix copy`. Nothing compiled on Odin.

The administrator's diagnostic child joined only that owned game cgroup and the renderer's namespaces, then dropped to the observed runtime UID/GID/groups before executing `vulkaninfo --summary`. [Identity proof](probe-identity.json) and [join assertions](ARCHIVE.sha256) confirm all six namespaces and the exact cgroup matched Eden. The child's host supervisor PID was **51684**, 04:06:56.446977–04:06:56.646685 UTC, exit **0**. The inner process was namespace PID 63; vulkaninfo was namespace PID 68. Both exited before the exact session stop; the cgroup was empty afterward.

[Device list](ARCHIVE.sha256):

| Order | Vulkan loader | Eden 0.2.1 |
|---|---|---|
| 0 | Turnip Adreno (TM) 740, integrated GPU, Mesa 26.2.3 | llvmpipe, CPU |
| 1 | llvmpipe (LLVM 21.1.8, 128 bits), CPU | Turnip Adreno (TM) 740 |

The game user could open `/dev/dri/renderD128` read/write. It was mode 0666, UID 0, GID 303. No `/dev/kgsl*` node existed. The unit had `DevicePolicy=auto` and `PrivateDevices=no`. Its Freedreno ICD was readable and resolved to the system's unchanged Mesa 26.2.3 output. No device permission or mount was changed.

[Allowlisted selectors and mounts](ARCHIVE.sha256) show no `VK_DRIVER_FILES`, `VK_ICD_FILENAMES`, explicit layer selectors, `MESA_VK_DEVICE_SELECT` or `DRI_PRIME`. Eden's Qt/GApps wrapper populated `XDG_DATA_DIRS`; its exact value is retained, not the rest of the environment. The loaded Vulkan loader was the pinned 1.4.363.0 output. `/run/opengl-driver` supplied the Mesa ICDs. The native probe listed `VK_LAYER_MESA_device_select` as available; availability alone is not proof it was active. The early renderer-mapping snapshot did not yet contain that layer's library. The later real Turnip run mapped `libVkLayer_MESA_device_select.so`; see [runtime maps](ARCHIVE.sha256). This resolves the earlier active-layer observation without any environment override.

[Native loader diagnostics](ARCHIVE.sha256) include skipped incompatible DZN/RADV drivers; vulkaninfo still exited 0 and enumerated the real Adreno. No driver or Mesa environment variable was set, and no ICD was removed.

The first diagnostic attempt had an operator rendezvous bug: its executable substring included an extra slash and did not match the real Eden path. It timed out and stopped its own session. No probe child joined that attempt. The predicate was corrected against the preserved executable identity before the successful probe.

## Eden's native index

All citations are the actual pinned v0.2.1 source `/nix/store/inmrhbhn9k0lnrcw8v4hi9rc2nwp9k95-source`:

- `src/common/settings.h:339`: integer `vulkan_device`, default **0**, category Renderer.
- `src/frontend_common/config.cpp:366–375,912–935`: reads `[Renderer]`, native `\\default` and per-title `\\use_global` flags. There is no name selector in this path.
- `src/video_core/vulkan_common/vulkan_wrapper.cpp:23–69,470–475`: stable name sort **descending**, then discrete-device and Nvidia/AMD/Intel preferences, then Microsoft Dozen demotion. Neither Qualcomm nor llvmpipe receives a preferred-vendor rank. Neither is discrete. Lowercase `llvmpipe` sorts ahead of uppercase `Turnip`; CPU devices are not demoted.
- `src/video_core/renderer_vulkan/renderer_vulkan.cpp:93–103`: indexes that sorted list with the configured integer, not the loader's raw ordinal.

Therefore setting raw Vulkan GPU0 would keep selecting llvmpipe in Eden. The native Adreno index is **1** for the observed list. The fix computes/checks Eden's order instead of hardcoding the loader ordinal. Its version/source gate pins 0.2.1 and the complete `vulkan_wrapper.cpp` hash. x86 and no-game GUI probes are unchanged. Native non-default Adreno choices are preserved; invalid/non-Adreno choices fail without rewriting. There is no sidecar or new Korri setting. The native index-0 authorship limitation and an unfiled upstream-issue draft are in the plugin README.

## Why the successful Cemu route chose Turnip

The exact successful Cemu launcher at `/nix/store/ygfpc2z5in3p7ljfz8xdsxbfknbyxpxm-cemu-0-unstable-2026-10-22-29f2f1f/bin/cemu` had no ICD override. It used Vulkan loader 1.4.328.0. Later Cemu worktree builds changed their driver policy; those were not substituted for this comparison.

The actual pinned Cemu 29f2f1f source is `/nix/store/hq0ns3vmrsgq9xb0kxnz69v0m26lmz9k-source`. `src/Cafe/HW/Latte/Renderer/Vulkan/VulkanRenderer.cpp:563–615` retains Vulkan enumeration order, tests suitability, and picks the matching UUID or the first suitable device. It does not apply Eden's descending-name sort. `src/config/CemuConfig.cpp:124–131` reads the native Graphic selection. The inspected account configuration had `Graphic/api=1` and no `Graphic/device` or `Graphic/vkDevice` selection. Thus its default selects the first suitable loader device, consistent with the recorded Turnip result and this probe's raw order.

## Control socket and DiscoveryConflict — read-only findings

`korrid-control.socket` remained active after stopping only `korrid.service`. The running socket's `Triggers` names that service. `services/korrid/nixos-module.nix:509–525` defines the listening stream with `Service=korrid.service`; it does not stop the socket when the service stops. A new connection therefore activates the daemon.

A current private-socket connection belonged to inputd. `services/inputd/src/main.rs:109–130` discards a lost producer and reconnects; `runtime.rs:25` sets the reconciliation interval to one second; `korrid_client.rs:58–60` and `producer.rs:28–30` connect to that Unix socket. This explains the expected reactivation. The historical initiating connection was not journaled, so **inputd as that exact caller is inferred**, not proven. The old journal proves the daemon restarted at 03:18:19 during the offline scan interval, 03:18:15–03:18:42.

`discovery/reconcile/documents.rs:81–85` rejects a commit if the readable documents changed since its snapshot. The parallel daemon/offline scans can hit this optimistic conflict gate. `discovery/coordinator.rs:613–619,673–677,864` records the failed scan as `last_problem`/`DiscoveryConflict`, producing the Problem display phase. It is not by itself a global launch lock. Existing valid catalogue records can reload independently. The real SMO route, settings writes and later diagnostic launch all worked while that prior problem was displayed.

The durable repair record was `{"pending_write":null}`. `discovery/reconcile.rs:657–665` blocks settings writers for a pending publication, not for a historical in-memory display diagnostic. A conflict does mean the failed scan did not publish its own changes or run enrichment; it must not be called a successful scan.

Another workflow rebooted Odin at 04:34. The system and korrid store paths stayed unchanged. At 04:48, discovery reported Idle with the Switch source and no conflict. We did not restart the daemon or clear any state in this graphics stage. A successful startup scan after that external restart naturally replaced the old in-memory diagnostic; `coordinator.rs:587–610` clears `last_problem` after a successful scan. No new offline operation was attempted.

## Restoration and remaining boundary

The probe's Gamescope opt-in and native-config/log changes were restored. [Hashes](restored.sha256) match [before](before.sha256): catalogue `8aa9f6be…f92806`, native config `df69b761…efa31`, native log `279dba95…7e78`. A revision guard first refused restoration because another write canonicalized quotes in the modifier record. A parsed comparison proved its values still exactly matched our candidate; restoration then used that fresh hash atomically. No unrelated value was overwritten.

The code fix passed the ARM/x86 package/admission gates and 12 native-selection tests. Bench 0.2.2 separately fixes native-default backend evidence using the run's fresh effective log, with unchanged refusal/runtime checks. The later [save and hardware proof](SAVE-PROOF.md) verifies the real Turnip picture and manual-save persistence. FPS, audio and soak must still be reported from subsequent runs, not inferred from this diagnosis.

**bubblewrap: absent — core gap #184.** No wrapper or permission bypass was added to the plugin.

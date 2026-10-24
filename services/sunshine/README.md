# sunshine-korri

`sunshine-korri` is Korri's downstream Sunshine package for carried patches that are useful to Korri before they are upstreamed, redesigned, or retired.

The package is intentionally an umbrella, not a single-feature fork. Patches may be unrelated. Each patch should explain:

- what behavior it changes,
- whether it is experimental or intended for upstreaming,
- what evidence exists,
- when it can be removed.

Producer packages, native gates, diagnostics and the retirement app are now
owned by this publisher. Run the commands below from this repository. Core
retains packaged consumer checks and host authority.

The input-presence proof runs the actual patched C++ binary as root in a Linux
VM. ARM runs QEMU software emulation without KVM. The x86 runner is unchanged.
Source hashes, ordered patches, root credentials, and test assertions stay the
same. Software emulation is slower and does not prove encoder performance or
physical-device behavior.

## Base

The base is upstream Sunshine `v2026.914.233613` from the shared `nixpkgs`
input (`02c087f3`). It carries the upstream fixes for GHSA-ph75 (exact enrolled
client-certificate identity; unknown issuers rejected), GHSA-26q2 and GHSA-6w33
(input packet bounds), GHSA-c428 (short control packets) and GHSA-36ff
(`pairing_id`-bound PINs). Upstream still accepts an expired or not-yet-valid
certificate from an enrolled identity on purpose (`openssl_verify_cb`, Moonlight
clock tolerance); Korri keeps that behaviour and does not modify `crypto.*`.

The experimental runtime-settings series (`0001`-`0005`, `0010`, `0012`-`0014`,
`0016`) was removed: its edge cases were never resolved, upstream now uses packet
`0x5504` for player LEDs, and its private VAAPI/NVENC struct copies cannot
follow FFmpeg 9. Git history keeps it. A revival needs new packet IDs and no
private struct copies. `0024` was removed because upstream `72faa710` carries the
same stdin pairing return.

## Current patches

### V4L2 M2M encoder profile

Patch `0021-add-v4l2m2m-encoder.patch` exposes Sunshine encoder name `v4l2m2m`. Open upstream Sunshine PR `#5717` (zero-copy V4L2) uses the same name; if it merges, this patch must be dropped or renamed. It maps H.264 to FFmpeg `h264_v4l2m2m` and HEVC to `hevc_v4l2m2m`. The backend accepts host-memory NV12 frames and relies on the Linux V4L2 M2M codec API. The removable plugin carries it in the approved aarch64 package and lets Sunshine select an available encoder at startup.

The `sunshine-korri-v4l2m2m` package uses the same reviewed Sunshine source and Korri patch set as `sunshine-korri`. It replaces only Sunshine's prepared FFmpeg libraries. Those libraries come from `build-deps` commit `a1fe2841cbc0d8c4501a1006d2d1cb88f219cc8c`, the one Sunshine `v2026.914.233613` pins, with FFmpeg commit `bf1b838f2ab88b4f8fd83443325c782ea0e0f7fa` (libavcodec `63.1.101`). The bundle also ships `nv-codec-headers` 13.1 (`include/ffnvcodec`): Sunshine configures against them even without CUDA, and would otherwise fetch them from Git during the build. Korri applies the buffer-layout fix from FFmpeg PR `#24328`. The fix copies visible rows into the driver-aligned storage width and height. This prevents the `ff_v4l2_buffer_avframe_to_buf()` crash seen with the `qcom-iris` encoder at standard `1280x720` and `1920x1080` frame sizes.

The Odin 2 Portal kernel carries upstream Linux commit `6f62dcefd2494aa9ac01538372353bf07755491e`, `media: qcom: iris: Add request key frame support for encoder`. It maps `V4L2_CID_MPEG_VIDEO_FORCE_KEY_FRAME` to the Iris encoder's request-sync-frame property. Sunshine needs this control for Moonlight recovery requests and stream refreshes after loss.

The approved plugin has one aarch64 release with both V4L2 M2M and Rockchip RKMPP support. RG353M can select `h264_rkmpp`; devices with a V4L2 codec can select `h264_v4l2m2m` or `hevc_v4l2m2m`. Korrid does not select an encoder or read encoder facts.

A second, Korri-local FFmpeg patch adds `repeat_headers=1`. Sunshine sets this option to join the sequence header to the first frame and repeat parameter sets at every IDR. Encoder creation fails if the requested header controls do not read back correctly. The default FFmpeg behavior is unchanged when the option is absent. Remove this patch when the reviewed FFmpeg version supplies equivalent in-band header controls.

A second, Korri-local Iris patch subscribes to `HFI_PROP_PICTURE_TYPE` on encoder bitstream output. Linux 7.2 otherwise skips encoder property subscriptions, so even actual IDRs have no V4L2 keyframe flag. The existing response handler maps this property to the flags FFmpeg and Sunshine use. Remove the patch when upstream reports encoder picture types correctly.

The cost is one separately built static FFmpeg/CBS package, two FFmpeg patches, and two Portal kernel patches. Frames use host memory rather than a zero-copy capture path. HDR, 4:4:4, AV1, and live bitrate changes are not supported by this profile. No software fallback is added. Remove each upstream backport when the reviewed dependency includes its fix; review the two local changes separately.

Physical probe and Moonlight results, including unresolved Wi-Fi packet loss, are recorded in [the Portal acceptance report](https://github.com/korri-os/korri/blob/f6597dd6fd8cd1452f5f75803672b33a8cfd6225/docs/acceptance/sunshine-korri-v4l2m2m-portal-2026-09-05.md). These results do not establish a production-ready host session or a sustained moving-content frame rate.

### Input-seat event mirror patch

`0015-add-korri-input-seat-event-mirror.patch` adds a native Sunshine event-source seam for Korri input seats. Sunshine remains an event source. It mirrors sanitized controller packets to a local Korri socket. A protected receiver must own emulator-visible virtual seats.

This patch is hardened from the legacy patch. It keeps the legacy wire schema. It does not keep the legacy blocking socket or loose sidecar parser.

The mirror needs these stable service values:

- `KORRI_INPUT_SEAT_MIRROR_SOCKET`: an absolute Unix socket path that the protected receiver owns.
- `KORRI_INPUT_SEAT_RUNTIME_DIR`: an absolute runtime directory that contains `sunshine-active-launch.json`.
- `sunshine-active-launch.json`: a root-owned sidecar with exactly `launchId`, `generation`, and `mirrorToken`. Its group must equal Sunshine's dedicated effective group. Group read is required. Group write, group execute, and every permission for other users are rejected. Mode `0640` is the intended producer mode.

The host service must keep the runtime directory and receiver socket root-owned. Sunshine receives only dedicated-group access. Sunshine opens the fixed sidecar with `openat`, `O_CLOEXEC`, and `O_NOFOLLOW`. It accepts only a root-owned regular file whose group equals Sunshine's effective GID and whose size is 4096 bytes or less. `launchId` and `mirrorToken` must be bounded strings. `generation` must be a nonnegative integer. Extra JSON fields are rejected.

Frames use bounded token-envelope NDJSON. A frame is 2048 bytes or less. The envelope contains `mirrorToken` and one `SunshineInputSeatFrame`. The frame can report `source-connected`, `source-state`, or `source-disconnected`. It does not contain keyboard, mouse, text, touch, pen, motion, battery, or raw device-path data.

Controller submission uses nonblocking AF_UNIX `SOCK_SEQPACKET` with `SOCK_CLOEXEC`. Before disclosing authority, Sunshine requires kernel `SO_PEERCRED` to identify a root receiver. Each connection submits one bounded token-envelope NDJSON message. An incomplete send is a failure. The receiver must discard any message that does not contain exact JSON followed by exactly one terminal newline. Receiver backpressure cannot wait in the controller packet path.

Each stream captures `launchId`, `generation`, and `mirrorToken` once at `input::alloc`. Later packets and timers check that the protected sidecar still matches all three values. Missing or changed authority permanently fences that stream; it cannot adopt a replacement launch. Configure and publish authority before starting the stream. A stream allocated without authority must reconnect after authority becomes available.

Sunshine refreshes actual current controller state every 200 ms on its existing single-thread input task pool. This is a scheduled interval, not a real-time execution guarantee. It does not require client packet repeats. Arrival reports connection but does not invent a neutral baseline: only an actual controller state packet establishes the first state. The active mask removes every absent controller from the stream's live set. Stream stop closes an atomic gate before slow thread joins, then serializes disconnect and timer cancellation on the input executor. The broadcast shutdown path does the same. Pending timers hold weak references, so they cannot keep a destroyed stream alive. An already executing nonblocking write can finish during stop; no later refresh may revive the stopped stream.

The private source identity is still `launchId` plus `controllerNumber` (0–15). Upstream controller numbers are per-stream, not global. If two live streams claim the same number under the same authority, both streams are fenced and their sources are disconnected. There is no remapping, winner selection, or new multi-stream policy. Clients need fresh streams after this conflict.

The core-owned input-seat receiver owns the persistent virtual seat pool. The Sunshine plugin supplies controller events, not a second seat backend. When the protected receiver paths are configured, Sunshine never creates its native gamepad as an authority/transport fallback. Keyboard, mouse, and touch remain outside this mirror. Receiver loss may drop messages; only a still-live, still-authorized stream may resume current-state refresh. The receiver's 1250 ms stale-source expiry remains the final bound when disconnect delivery fails.

The automated Python backpressure fixture remains a Sunshine-source transport check, not producer proof. `input-seat-presence-check.nix` compiles `test-input-seat-presence.cpp` against the fully patched upstream `src/input.cpp`, actual Moonlight packet definitions, input queue and task pool. It stubs platform injection only. Its off-device root VM exercises real sidecar metadata and socket credentials, quiet presence for more than 1250 ms then one press, held first state, cancellation/destruction, authority replacement, mask removal, stream collisions, unavailable/full receivers, and a non-root socket impostor. The main input-seat patch check also depends on the real release package and its exact provenance. The separate `korri-input-seat-receiver` checks exercise the Rust receiver; the C++ test is not Sunshine-to-inputd-to-portal E2E proof.

The mirror remains inert without configured protected paths. Missing authority at allocation permanently disables that stream's mirror. The mirror token must not appear in public status, network RPC, logs, or committed evidence. Physical device acceptance remains separate from the repository implementation.

Current automated gate:

- `nix build --no-link .#checks.$(nix eval --raw --impure --expr builtins.currentSystem).sunshine-korri-input-seat-patch` checks the input-seat source boundary, the approved patch hash, the patched Sunshine build, and a nonblocking transport model/source-invariant check under receiver backpressure. The model does not execute compiled Sunshine behavior.

## Korrid certificate control

The separate [offline all-client retirement executable](OFFLINE-RETIREMENT.md)
reuses this producer's state reader, serializer, file-persistence machinery and
trust verifier. Its separate offline entry never restores old trust after the
actual rename, including on sync, close, verification or output failure. Online
transaction rollback is unchanged. It needs exclusive external quiescence and
the existing state UID/GID, not admin credentials. It adds no runtime endpoint.
All clients must pair again.

Patch `0020` adds an opt-in private adapter for Korrid-managed Moonlight trust. Sunshine consumes exactly one root-created systemd `SOCK_SEQPACKET` socket named `korri-certificate-control`. Sunshine verifies the configured absolute pathname, root ownership, and exact narrow mode before it serves requests. It does not create a TCP, HTTP, or web user interface. The adapter remains inactive when any socket-activation value or the exact expected Korrid UID and GID are absent.

Each accepted connection carries one JSON frame of at most 16384 bytes. The non-mutating `attest` operation compares an expected Sunshine UUID and returns only whether it matches. Provision and revoke also check `SO_PEERCRED`, the exact Sunshine host UUID, and one valid public X.509 PEM certificate. Provision is idempotent by the certificate's SHA-256 fingerprint. Revoke removes only entries with that fingerprint. Sunshine preserves its existing `root.named_devices` schema, replaces its state file atomically, and proves that the replacement live TLS verifier accepts every current client certificate before it reports success. If a failed mutation cannot restore the prior durable state, Sunshine terminates instead of serving HTTPS or certificate-control requests with uncertain authorization. Mutation replies contain only status, whether state changed, and Sunshine's public server certificate. Certificate bodies and state contents do not enter logs.

The adapter does not replace TLS. It replaces only the manual GameStream pairing ceremony. The Moonlight private key remains on the Android device, and Sunshine's private key remains in Sunshine's existing state directory. The removable Sunshine plugin supplies the native socket and service units. Korrid supplies only the bounded trust operation. Physical device acceptance remains separate.

## Rockchip RKMPP hardware encoding

The `aarch64-linux-rkmpp` profile adds patches `0022` and `0023` after every base patch. Patch `0022` defines an `rkmpp` encoder that uses FFmpeg's `h264_rkmpp` (Rockchip MPP, RKVENC hardware) in CBR mode with a single slice and no intra refresh. The encoder advertises only H.264 because RKVENC-v1 on RK3566 has no HEVC or AV1 encoder. The patch also paces the encode loop to the negotiated frame rate. Without pacing, the asynchronous MPP encoder returns immediately and the loop spins at the KMS capture rate.

The RKMPP pacer uses the negotiated `config.framerate`, not mutable session settings. Patch `0032` keeps the encode deadline absolute: advance by one interval, then resynchronise to the current time plus one interval only when the advanced deadline is more than one interval late. IDR requests bypass that sleep. Patch `0029` lets Wayland capture follow the compositor and skips conversion/encoding for early captures; it advances the session deadline until it is strictly after the capture time. Other encoders do not use either pacer.

`sunshine-korri-capture` executes both pacing blocks extracted from the patched release source with a deterministic clock. It checks 1, 30, 60, 90 and 120 FPS, sleep overshoot, the strict stall threshold, early and stalled captures, and bypass conditions. This proves deadline arithmetic, not hardware throughput.

Patch `0023` adds a KMS DRM_PRIME path for native-size streams. On the RG353M, Sway scans out a single-plane linear XRGB8888 framebuffer. Sunshine duplicates that dma-buf file descriptor into a ref-counted `AVDRMFrameDescriptor` and gives it directly to `h264_rkmpp`; RKVENC performs RGB-to-YUV conversion in hardware. This avoids the previous `GetTextureSubImage` readback, `sws_scale`, and CPU upload. Streams whose requested size does not exactly match the KMS framebuffer retain the RAM scaling and RKMPP upload fallback. The zero-copy path reduced total Sunshine CPU from about 135% to about 10% at 640x480@30.

The profile links Sunshine against `ffmpeg-rkmpp-static.nix`. That derivation builds Sunshine's own `build-deps` recipe against the reviewed FFmpeg commit from `approved-patches.nix`, so the libavcodec ABI matches the other profiles, and adds the RKMPP encoder and hardware context from `patches/ffmpeg/`. `rockchip-mpp.nix` builds the official Rockchip MPP 1.1.0 source at commit `c08762ebfadeb4e986d2fed993bc7a54862d3ebe`; the pinned Nixpkgs has no MPP package. `0001` is the encoder and hardware context lifted from the `ffmpeg-rockchip` fork; it replaces the NV12-only `h264_rkmpp` that FFmpeg 8.1 and later ship (`61b034a47c`), because Korri needs XRGB8888 DRM_PRIME input and requested-IDR behaviour. There is one `h264_rkmpp`. `0002` adapts the fork to the reviewed FFmpeg's APIs. The aarch64 build also enables the reviewed H.264 and HEVC V4L2 M2M encoders in the same static FFmpeg archive. Sunshine selects the available encoder at startup.

The combined profile is approved only for `aarch64-linux`, is mutually exclusive with CUDA, and keeps the same reviewed upstream base derivation as the software profile.

Measured on RG353M at 640x480@30 with KMS capture: RKVENC serviced one interrupt per delivered frame, the encoder thread used about 1% CPU, and Sunshine's total CPU fell from about 170% (libx264) to about 135%. The remaining load is Sunshine's GPU-to-RAM readback and BGRA-to-NV12 software conversion. A zero-copy DRM_PRIME capture path is tracked separately.

## Package provenance

The installed package contains `share/korri/sunshine-korri/provenance`. This mode-`0444` file records:

- the provenance format,
- the package name,
- the approved platform build profile,
- whether the build contains CUDA support,
- the base Sunshine version,
- the independently approved base Sunshine source hash,
- the exact observed base Sunshine source store path,
- the exact observed base Sunshine derivation path,
- the reviewed libavcodec version,
- the exact reviewed FFmpeg commit and source hash,
- whether the V4L2 M2M FFmpeg profile is enabled,
- the reviewed `build-deps` commit and source hash,
- the V4L2 M2M FFmpeg patch name, hash, and patch-set hash,
- the reviewed NVENC API major and minor version,
- the Sunshine executable path,
- each ordered Korri patch name and SHA-256 value,
- one SHA-256 value for the complete ordered patch set.

Nix also exposes the provenance path, build profile, CUDA state, V4L2 M2M state, RKMPP state, approved base source hash, observed base source and derivation paths, ordered patch names, and patch-set digests through package passthru values. `approved-patches.nix` is the independent approval record. The approved profiles currently cover x86_64 Linux with CUDA and one combined aarch64 Linux V4L2 M2M and RKMPP profile. V4L2 M2M patches only FFmpeg, so it keeps the base ordered patch-set digest; RKMPP appends Sunshine patches after the base set and therefore carries its own digest. Package evaluation fails when the profile, base version, base source hash, one patch hash, or the ordered patch-set digest changes. The host module also requires the exact approved final derivation and output, so an `overrideAttrs` derivative cannot preserve trusted metadata while replacing the executable or patches. Deployment checks must use these values to attest the exact package. The manifest contains no secret or device-specific value.

## Removal/upstream policy

Remove or replace a carried patch when one of these becomes true:

1. Sunshine upstream accepts an equivalent feature.
2. Korri no longer needs the behavior.
3. A cleaner patch supersedes the current one.
4. The evidence shows the approach is unsafe or too narrow for continued carrying.

## RG35XX Pro linear KMS 60 fps candidate

This is a candidate, not a published release. The common patch set has 8
patches. The combined ARM profile has 22. The four new patches replace the
layered `exp/kms-direct-readback` experiment without its observers or timing
output. Only guarded RAM-KMS requests FIFO, after its first valid vblank lock.
It logs the granted backend and priority once per thread lifetime. The generic
async Linux loop never promotes other backends. It writes no observer file. The existing rotation operation remains; its timing probes are removed.
Package and capture checks require `--fuzz=0` and disable backup
creation. Ordered hashes are SHA-256 of `name + " " + sha256 + "\n"` for each
record, in application order. Individual hashes cover the complete patch bytes.

| Patch | Scope and status | Evidence and removal condition |
| --- | --- | --- |
| `0035-read-linear-kms-dmabuf.patch` | Experimental ARM KMS RAM path. Explicit linear, single-plane little-endian XRGB/ARGB8888 uses read-only PRIME mmap with checked READ START/END sync. Other layouts, transforms, map/sync failures keep EGL. | Experiment `4cc7af7`: about 13 ms direct copy versus 72 ms GL p50 on Pro. Remove for an upstream equivalent, accepted faster path, or unsafe coherency/lifetime evidence. |
| `0036-convert-kms-row-pairs-to-nv12.patch` | Experimental ARM capture optimization. Copy each WC row once to reusable cached row-pair scratch, then libyuv NEON dispatch to owned NV12. All active consumers must agree on even, native-size, unpadded 8-bit BT.601 limited V4L2 H.264. Cursor-visible frames keep RGB and swscale. Other matrices, ranges, sizes, formats and mixed streams keep swscale. Encoder frames never alias the capture pool. | Experiments `cec8d8a`, `6b81298`, `e1180ed`; exact whole-frame libyuv comparison in `row-pair-test.cpp`. libyuv is not bit-identical to swscale. Remove for accepted upstream/hardware conversion or unsafe colour/lifetime evidence. |
| `0037-preserve-kms-capture-phase.patch` | ARM RAM KMS capture follows the captured plane's CRTC vblank sequence and samples at `capture_vblank_offset_ms` (default 0). Missed phases resynchronise to a real refresh; no synthetic catch-up acquisitions or affinity rule. Unsupported timing falls back once to absolute nominal pacing with overdue deadlines skipped. | Device-local source IDs linked high-miss sessions to the early-refresh region, not concurrent CMA migration. The independent timer drifted about 2.27 ms/min. Phase is an association, not an exclusive cause: isolated raw acquisition omissions occurred outside that band. Remove for equivalent upstream pacing or failed latency/source-starvation acceptance. |
| `0038-configure-linux-capture-fifo.patch` | Experimental opt-in Linux asynchronous capture-only FIFO, with reset-on-fork. `capture_rt_priority` is a strict decimal integer, 0 (default off) or 1..20. Invalid values disable the request. Scheduling failure, including EPERM, logs a warning and capture continues. No service-wide RT scheduling. | The older FIFO 15 experiment measured acquisition rate, not this source-ID gate. Current guarded trials compare OTHER, nice −10 and FIFO 5/15; CPU isolation is not carried. Remove for equivalent upstream policy, lost need, or latency/starvation evidence. |

The publisher still ships one aarch64 release with both RKMPP and V4L2 M2M.
Only that ARM profile links libyuv. The x86_64 CUDA recipe adds no libyuv input.
`capture_rt_priority` is consumed on Linux only. The synchronous
capture/encode loop and other encoder/packet/input threads are not promoted.

### RAM KMS vblank offset

The ARM KMS profile accepts `capture_vblank_offset_ms`, a scalar decimal
integer from 0 to 1000 milliseconds. Its default is **0 ms**, the vblank edge.
Zero selects edge capture; it does not disable the lock. Unset/empty keeps
the default; malformed values warn and select the default. The initial
12–13 ms trials read queued plane state ahead of physical presentation and
still omitted rare presented IDs. Edge capture usually matches currently
presented content, with rare ahead-of-presentation samples; the acceptance
record reports exact counts. The value
must be shorter than the active CRTC mode refresh period. The mode refresh
must also match negotiated capture FPS within 0.1%; otherwise this path
uses nominal absolute pacing with overdue deadlines skipped.

The RAM capture thread queues `DRM_VBLANK_EVENT` requests on a separately opened,
nonblocking fd for the captured plane's DRM card/CRTC. It never blocks waiting
inside `drmWaitVBlank` or consumes another fd's flip events. Poll/read shares an
absolute **100 ms deadline** across all requests in a pacing iteration; EINTR
never extends it. An expired wait closes/cancels outstanding events, checks the
session-stop callback and permanently falls back to nominal pacing. Timestamp
and sequence checks precede sleeping to the selected refresh's offset. It never reuses a sequence or carries an overdue nominal
deadline across refreshes. A used/expired refresh or entry after the requested
phase waits for a future refresh. Ioctl and wakeup overshoot is allowed only
when waiting began before the selected phase. The following deadline still
comes from its own vblank. Actual phase/lateness is measured in acceptance.
Clock/driver/timing failures log once per capture instance and permanently
fall back to nominal absolute pacing for that instance. Fallback skips overdue
deadlines rather than running catch-up acquisitions continuously. No modesetting
or additional capability is requested. VAAPI/CUDA/Wayland capture is unchanged.

The RAM RT safety guard counts actual vblank-wait ioctl invocations and
fallback/offset pacing sleep calls; their duration does not matter. These
calls can return immediately when the next vblank already passed. Before
capture, three consecutive acquisitions without a pacing call, three with
the same vblank sequence, or a backwards sequence demote to SCHED_OTHER for
the capture-thread lifetime. Forward skips and unsigned sequence wrap are
valid. CPU share is not a trigger. FIFO is requested only after the first
successful lock in this backend. Initial timing fallback never acquires FIFO.
Backend exit restores SCHED_OTHER, retaining RESET_ON_FORK. If that restoration
is denied, Sunshine terminates rather than leaking FIFO to an unguarded backend.
The guard's degradation is sticky for the thread lifetime. Logs include the condition, acquisition
end times, decision time, calls, sequences and diagnostic pacing timings.
Demotion keeps SCHED_RESET_ON_FORK and priority zero. If it fails, the guard
sleeps a full capture period on every iteration, takes no more snapshots
and lets the encoder repeat. Final performance measurements reject policy
degradation; explicit forced safety controls test session continuation.

The offset controls scheduling after the chosen vblank, not an equal change
to content-to-client latency: KMS plane state can already name a queued
frame before that frame is presented. Acceptance reports both actual sample
phase and matched source-presentation-to-client latency. FIFO can still
preempt the compositor; source misses and the longest such preemption must
be reported for every policy and acceptance run.

Evidence before this candidate: Core's
[frame profile](https://github.com/korri-os/korri/blob/d001d08c2ef8ca17e12acc687004800a22068a2b/docs/acceptance/sunshine-korri-rg35xxpro-frame-profile-2026-10-22.md)
and [encoder acceptance](https://github.com/korri-os/korri/blob/d001d08c2ef8ca17e12acc687004800a22068a2b/docs/acceptance/sunshine-korri-rg35xxpro-v4l2m2m-2026-10-22.md).
The experiment's local `/tmp/h700-sun/readback.md`, `convert.md` (including
scheduling), and `profile.md` retain raw measurement references. These are
experiment evidence, not a pass for the new package. Fresh package/device
results and remaining publication steps are recorded in `/tmp/h700-sun/ship.md`.
The [refresh-phase acceptance record](kms-phase-lock-acceptance.md) distinguishes
prototype failures from final guarded results.
Acquisitions and changed decoded content are different measurements. Fresh
acceptance uses a self-describing source frame ID and actual presentation
feedback. A presented ID missing from the entire received stream is a
capture-path miss; an external per-acquisition NV12 ID trace distinguishes
acquisition omissions from encoder/delivery omissions. Source presentation
sequence gaps are reported separately. Decode every frame, discard exactly
10 seconds from first receive, then record every whole 10-second window in
three fresh 90-second runs and six back-to-back 60-second runs. The owner
selected the approximately 59.99 fps ship bar: no guard trip/spin, active lock,
zero decode errors, about at most one capture/downstream miss per 90-second
run and no window below 597 new frames. This is not a perfect-60 claim.
Report raw warm-up, source misses, phase, matched latency and compositor
preemption. Never move the windows to obtain a pass. Diagnostic observers are
not shipped in these patches.

The owner approved the pre-review package **as is** and stopped testing. The three
90-second runs measured 59.98 fps with misses 2/1/2 and every window at least598.
The interrupted short-session batch still had bad sessions (including596 and
522/538 windows); it did not pass the597 floor. See the acceptance record for
all completed windows, the actual stop chronology and downstream classification.

### Explicit native permission change — approval required

`plugins/sunshine/korri-sunshine.service` now requests **`LimitRTPRIO=5`**.
Its native `runtime.sh` sets Sunshine's `capture_rt_priority=5` override.
The limit allows this service's threads to request FIFO/RR up to 5; Sunshine
chooses only guarded RAM-KMS after lock establishment. It does not prove other code in
the service cannot use the allowance. It adds no `CAP_SYS_NICE`, affinity or
service-wide `CPUSchedulingPolicy`. Existing KMS capabilities are unchanged.
FIFO can delay lower-priority input, compositor, audio and network work. The
Pro's unchanged RT runtime budget does not guarantee per-frame latency or
starvation safety. The owner explicitly waived further device acceptance for
the review fixes; host checks do not establish physical-device performance.

The publisher now pins reviewed Core main
`eab74c96134abed6453ff74c6c80bf4ebca5c52f` in both `flake.nix` and `flake.lock`.
It admits canonical decimal 1..20 only, refuses leading-zero values, exposes
the native authority in the warning and approval digest, and derives
`RestrictRealtime=no` only for the requesting unit. Units without the request
keep their previous filter and approval. Deploy a compatible consuming host
before exact-build inspection/approval. `plugin.ts` remains unchanged.

### Independent-review fixes: host-only verification

The review fixes scope FIFO to guarded RAM-KMS, replace blocking vblank waits
with bounded DRM events, and adopt the reviewed Core permission. Capture tests
on both build architectures exercise the real scheduling gate (all positive
priorities on other/unlocked backends do not request FIFO), real poll timeout
under repeated signals, stale-event cookies, and successful event decoding.
The capture check also refuses a FIFO request in generic `src/video.cpp`.
Producer checks compile the actual backend; admission checks use the pinned
Core, not a developer-path override. The ARM V4L2 check is retried explicitly.

No device access or acceptance run is authorized for this revision. The
[measurement record](kms-phase-lock-acceptance.md) and per-miss CSV describe the
older exact package, not this new event-wait implementation. New output paths
and host check results are recorded in `/tmp/h700-review/review.md` on zao.
The NARs require a new pinned-source publication dry run per `PUBLICATION.md`.
After actual publication, Core must update both architecture Sunshine entries
in `published-plugins.nix` and append the actual batch/archive hashes at matching
indices in `published-plugin-metadata.nix`; no unpublished image pin is invented.

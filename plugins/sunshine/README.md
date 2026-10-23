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

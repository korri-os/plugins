# Sunshine streaming host plugin

`@korri:sunshine` is the removable Linux streaming-host integration. The package ships three native systemd units:

- `korri-sunshine.service` runs the reviewed Sunshine build as `korri`.
- `korri-sunshine-certificate-control.socket` gives korrid the private certificate-trust channel.
- `korri-sunshine-input-setup.service` owns the temporary group and runtime UHID permission rule. The core `korri-input-seat-receiver.service` owns persistent shared seats independently of this plugin.

The plugin requests KMS capture, broad device visibility, `CAP_SETPCAP`, and `CAP_SYS_ADMIN`. Approval binds those requests, both root helper commands, the named udev rule artifact, every native unit, and the exact package closure. The plugin host starts all three units before it opens the declared Sunshine ports. It never opens the administrative TCP port `47990`.

Removal stops all three plugin units, checks native cleanup, removes the runtime UHID rule and temporary group, closes the firewall rules, and releases the package selection. It does not stop the core receiver or change persistent seat permissions. It preserves `/home/korri/.config/sunshine`, including Sunshine identity, settings, and paired-client state. Korrid remains the only owner of the bounded stream-client trust effect.

The plugin uses globally unique systemd names. It does not replace a host `sunshine.service`, add a NixOS module, or keep a disabled host unit in the image.

## New real-time scheduling permission (candidate)

The native service now requests **`LimitRTPRIO=15`**. `runtime.sh` sets the
Sunshine config key `capture_rt_priority=15`. Only the asynchronous Linux
capture thread requests FIFO 15, with reset-on-fork. EPERM logs and continues.
No `CAP_SYS_NICE` or service-wide scheduling policy is requested. This limit
still permits any thread in the service to request RT priority up to 15.
Lower-priority input/compositor work can be delayed; measured responsiveness
and exact-build re-approval are required, not implied by the limit.

The current locked Core refuses this directive. Release is blocked until the
separate Core `ceca5b06630bc9a8798b39a3bdef56b6952a4c75`
(`feat/plugin-host-limit-rtprio`) is reviewed, reachable,
pinned and available on the consuming host. That change makes the native
request visible in the warning and approval digest, and withdraws the host's
`RestrictRealtime` filter for only that unit. See the
[producer record](../../services/sunshine/README.md#rg35xx-pro-linear-kms-60-fps-candidate)
for scope, evidence and removal conditions. This branch does not install or
automatically approve the changed plugin.

# Mini host-preparation checks — 2026-10-23 UTC

**Host checks passed; Mini hardware acceptance has not run.**
No full repository suite was run.

| Focused check | Result |
|---|---|
| `nix build --no-link --print-out-paths .#checks.x86_64-linux.korri-eden-package .#checks.x86_64-linux.korri-eden-admission .#checks.aarch64-linux.korri-eden-package .#checks.aarch64-linux.korri-eden-admission -L` | All four outputs passed. x86 outputs reused; ARM package check ran on <builder-2>. Includes native CLI/GUI, two-account/save-root retargeting, TypeScript/callback checks, ShellCheck, 12 Vulkan tests, 9 P1 tests, Ruff and strict mypy. |
| Documented ARM bench build, default daemon builders | Passed on <builder-1>; exact 0.2.2 output matches Odin's tested output. The first attempt with the retired explicit builder name failed; no source was changed to conceal it. |
| x86 bench build through `plugins/eden/bench/build.nix` | Passed fresh: 26 tests, real two-window Xvfb Present integration, C `-Wall -Wextra -Werror`, Ruff, format and mypy. |
| Existing personal plugin source and native helpers | Direct byte comparisons passed; [host-only proof](host-source-proof.json). |
| Signature readiness | All 489 paths in the personal-plugin/bench closure union carry `korri-cache-<build-host>-1`; candidate plugin also carries its existing personal-publisher signature. No device trust changed. |
| README shell snippets | All three parse with `bash -n`. |
| Input sources | Read-only <content-host> stat/count passed; host key modes/sizes and selected two-file save checked. No proprietary payload committed. |

Exact gate outputs, in command order:

```text
/nix/store/casid596p7xhwi20lzyhmq0j4v7n9yq7-korri-eden-package-check
/nix/store/injh0w47mn7qqrzc0xhkp5nbaqmcfg72-korri-eden-admission
/nix/store/c2fgxamxzw6wy0hp6zh78c4sxg8yvam6-korri-eden-package-check
/nix/store/4qhbrg4pa46j6qarhark07020sv9s6w3-korri-eden-admission
```

Exact ARM bench output:
`/nix/store/zd7jxck7icv2hizxr6zlx65ci4n89qnz-korri-eden-bench-0.2.2`.
Exact fresh x86 bench output:
`/nix/store/v28qcbs42l7xqcwld8lnsk598ikvdpwr-korri-eden-bench-0.2.2`.

These are package/executor and synthetic native-display checks, not SMO or
Mini FPS measurements. The SSH timeout is the only real Mini path exercised.
Audio and restoration cannot be verified on an unreachable device; no device
mutation or session from this worker needs restoring.

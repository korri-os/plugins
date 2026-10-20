# Proton

`@korri:proton` ships Proton compatibility tools for runners that require it.
It declares no runner and no handler. `cachyos` names the one build it
carries. That name is the artifact key, a file-key prefix and a cache-path
segment only.

## Files

A runner that lists this plugin's exact output in its `plugin.nix` `requires`
reads this file from its launch input under `@korri:proton/<key>`:

| Key | File |
|---|---|
| `cachyos-unpack` | Native program that unpacks the verified release; korrid runs it, runners do not |

`cachyos/compatibilitytool.vdf` is not a file key. `cachyos-unpack` installs
it from its own closure.

## Artifact `@korri:proton/cachyos`

`plugin.ts` declares the pinned Proton-CachyOS arm64 release as the artifact
`cachyos`, version `11.0-20260601-slr-arm64`, with its URL, `sha256:<hex>`
and `bytes` (0.34 GB, the server's Content-Length). `plugin.ts` is the single
source of the pin. The tool is not in the plugin closure.

A runner that lists `@korri:proton/cachyos` in its `artifacts` receives the
ready directory, `<storage-root>/cache/proton/cachyos/11.0-20260601-slr-arm64/`,
in its launch input as `artifacts["@korri:proton/cachyos"]`. korrid downloads,
resumes and verifies the release, runs `cachyos-unpack` in a work directory,
makes the tree read-only, flushes it and renames it to the ready directory.
See ADR 0012.

## Tool name

`plugin.ts` is the only version source. `cachyos/tool-name.nix` uses Core's
`korri-publish declaration` command at build time to evaluate it in the empty
sandbox. It derives `proton-cachyos-11.0-20260601-slr-arm64` from
`artifacts.cachyos.version`. Builders read the result and substitute it into
`compatibilitytool.vdf`, the Steam session and the VDF settings helper. Nix
evaluation does not read build outputs. No compiled declaration is shipped.
The current tool name and existing per-game selections are unchanged.

`korri-proton-tool-name` changes the real declaration's version and checks all
three generated consumers. The metadata step needs the matching Core evaluator
on the build machine; it does not run on a device.

`compatibilitytool.vdf` is the legacy file with one change: `install_path` is
`.`. The file sits inside the tool directory, and Valve's own template in the
release says a subdirectory of `compatibilitytools.d` uses `.`.

## `cachyos-unpack <work-dir> <release.tar.xz>`

korrid invokes it with the verified release.

1. It unpacks the release's single top-level directory into `<work-dir>`.
2. It removes `require_tool_appid` from `toolmanifest.vdf`, so the tool
   serves as Steam's global default instead of chaining to an unregistered
   runtime tool.
3. It installs `compatibilitytool.vdf` in place of the release's own file.

It writes only under `<work-dir>`. Exit status: 0 ready, 1 failed (including
usage). Diagnostics go to stderr; stdout carries nothing korrid reads. tar and
xz come from Nix. Nothing is compiled on the device.

## Checks

Build these on a build machine, never on a device. `packages/check.nix` runs
`cachyos/test_unpack.py` against a small synthetic release, `bash -n` and
shellcheck. `packages/plugin-check.nix` checks the built package for the
target system.

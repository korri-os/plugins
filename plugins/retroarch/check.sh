#!/usr/bin/env bash
# Build-machine gate for the source and pinned settings evidence.
set -euo pipefail
root="${KORRI_ROOT:-$(git rev-parse --show-toplevel)}"
cd "$root/plugins/retroarch"
bun install --frozen-lockfile --ignore-scripts
bun run typecheck
bun test
system="$(nix eval --impure --raw --expr builtins.currentSystem)"
nix build --no-link "$root#checks.$system.korri-retroarch-settings"

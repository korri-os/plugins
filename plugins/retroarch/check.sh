#!/usr/bin/env bash
# Build-machine gate for the source and pinned settings evidence.
set -euo pipefail
root="${KORRI_ROOT:-$(git rev-parse --show-toplevel)}"
cd "$root/plugins/retroarch"
bun install --frozen-lockfile --ignore-scripts
bun run typecheck
bun test
system="$(nix eval --impure --raw --expr builtins.currentSystem)"
# Native netplay/window checks must not compete with other check builds.
nix build --no-link --print-build-logs --max-jobs 1 \
  "$root#${KORRI_CHECKS_ATTRIBUTE:-checks}.$system.korri-retroarch-settings" \
  "$root#${KORRI_CHECKS_ATTRIBUTE:-checks}.$system.korri-retroarch-netplay-password" \
  "$root#${KORRI_CHECKS_ATTRIBUTE:-checks}.$system.korri-retroarch-netplay-host-during-play"

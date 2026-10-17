#!/usr/bin/env bash
# Incremental private authoring-editor build (x86_64 build host only).
# Usage: dev-build.sh   (re-run after editing ../src-overlay/*)
# Copies pinned upstream source once, overlays our recipe files, configures
# once inside the derivation's build environment, then runs ninja.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
state="$here/.."
src="$state/zc-work"
build="$state/zc-build"
if [ ! -d "$src" ]; then
  cp -r "$state/zc-src/." "$src"
  chmod -R u+w "$src"
fi
# Overlay: our files win (lh_recipe.inc and the patched commands.cpp hook).
if [ -d "$state/src-overlay" ]; then
  cp -r "$state/src-overlay/." "$src/"
fi
exec nix develop --impure -f "$here/default.nix" editor --command bash -c '
  set -euo pipefail
  src="'"$src"'"; build="'"$build"'"
  cd "$src"
  if [ ! -f cmake/FindLibuuid.cmake.done ]; then
    source "$stdenv/setup"
    eval "$postPatch"
    touch cmake/FindLibuuid.cmake.done
  fi
  mkdir -p "$build"; cd "$build"
  if [ ! -f build.ninja ]; then
    cmake -G "Ninja Multi-Config" $cmakeFlags "$src"
  fi
  cmake --build . --config Release --target zeditor zscript --parallel "$(nproc)"
'

#!/usr/bin/env bash
# Build out/${OUTNAME:-lantern-hollow}.qst: stock template (private) -> scrub -> recipe -> engine save.
set -euo pipefail
state="$(cd "$(dirname "$0")/.." && pwd)"
out="$state/out"
mkdir -p "$out"
"$state/tools/make-recipe.py" 2>/dev/null
cd "$state/zc-build/Release"
BASE="${BASE:-modules/classic/default.qst}"
rm -f "$out/${OUTNAME:-lantern-hollow}.qst"
nix shell nixpkgs#xvfb-run -c xvfb-run -a ./zeditor -headless -lh-build \
  "$BASE" "$out/recipe.json" "$out/${OUTNAME:-lantern-hollow}.qst" > "$out/build.log" 2>&1 || {
  tail -20 "$out/build.log"; exit 1; }
grep "lh-build" "$out/build.log"
nix shell nixpkgs#xvfb-run -c xvfb-run -a ./zeditor -headless -uncompress-qst \
  "$out/${OUTNAME:-lantern-hollow}.qst" "$out/${OUTNAME:-lantern-hollow}.raw.qst" >/dev/null 2>&1
ls -la "$out/${OUTNAME:-lantern-hollow}.qst" "$out/${OUTNAME:-lantern-hollow}.raw.qst"

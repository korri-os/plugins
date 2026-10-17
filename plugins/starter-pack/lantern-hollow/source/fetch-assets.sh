#!/usr/bin/env bash
# Download the CC0 source assets for Lantern Hollow with SHA-256 receipts.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p raw
fetch() { # name url licence-page
  local name="$1" url="$2" page="$3"
  if [ ! -f "raw/$name" ]; then curl -fsSL -o "raw/$name.part" "$url" && mv "raw/$name.part" "raw/$name"; fi
  printf '%s  %s  %s  %s\n' "$(sha256sum "raw/$name" | cut -d' ' -f1)" "$name" "$url" "$page"
}
{
  echo "# sha256  file  url  licence-page   (fetched $(date -u +%FT%TZ))"
  fetch kenney_tiny-town.zip "https://kenney.nl/media/pages/assets/tiny-town/a415fbeb49-1735736916/kenney_tiny-town.zip" "https://kenney.nl/assets/tiny-town"
  fetch kenney_tiny-dungeon.zip "https://kenney.nl/media/pages/assets/tiny-dungeon/f8422efb44-1674742415/kenney_tiny-dungeon.zip" "https://kenney.nl/assets/tiny-dungeon"
  fetch 15_melodic_rpg_chiptunes_mid.zip "https://opengameart.org/sites/default/files/15_melodic_rpg_chiptunes_mid.zip" "https://opengameart.org/content/15-melodic-rpg-chiptunes"
  fetch subspace_512_sfx.zip "https://opengameart.org/sites/default/files/The%20Essential%20Retro%20Video%20Game%20Sound%20Effects%20Collection%20%5B512%20sounds%5D.zip" "https://opengameart.org/content/512-sound-effects-8-bit-style"
} > RECEIPTS.txt
cat RECEIPTS.txt
for z in raw/*.zip; do d="unpacked/$(basename "$z" .zip)"; [ -d "$d" ] || { mkdir -p "$d"; nix run nixpkgs#unzip -- -q "$z" -d "$d"; }; done

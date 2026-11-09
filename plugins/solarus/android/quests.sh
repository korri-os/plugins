#!/usr/bin/env bash
# Builds the Starter Pack cartridges package (incl. the two .solarus quests)
# from korri-os/plugins at a pinned commit, on aka.
set -euo pipefail
REV=97c28031b06cb854aaf67d6f7cc842763d3858b9
W=/var/lib/solarus-android-build/plugins
if [[ ! -d "$W/.git" ]]; then
  git clone https://github.com/korri-os/plugins.git "$W"
fi
cd "$W"
git fetch origin "$REV"
git checkout --detach "$REV"
test "$(git rev-parse HEAD)" = "$REV"
out=$(nix-build -E "let pkgs = import <nixpkgs> {}; in import ./plugins/starter-pack/cartridges-package.nix { inherit pkgs; }" --no-out-link)
find "$out" -name '*.solarus' -exec sha256sum {} \;

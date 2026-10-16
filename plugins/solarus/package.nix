{ pkgs }:
# Use the existing nixpkgs build recipe with the current upstream release.
# The source hash is also used by nixpkgs' Solarus 2.1.4 package.
pkgs.solarus.overrideAttrs (old: {
  version = "2.1.4";
  src = pkgs.fetchFromGitLab {
    owner = "solarus-games";
    repo = "solarus";
    tag = "v2.1.4";
    hash = "sha256-gXqKDhjK6vZWFTBNDNCu5XTks7zr+ZUAIJregGEvtOc=";
  };
  postInstall = (old.postInstall or "") + ''
    install -Dm644 "$src/license" "$out/share/licenses/solarus/COPYING"
    install -Dm644 "$src/license-details.md" "$out/share/licenses/solarus/license-details.md"
  '';
})

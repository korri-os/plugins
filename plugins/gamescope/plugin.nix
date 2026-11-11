{ gamescopePackage, pkgs }:
let
  displayChange = import ./display-change.nix { inherit pkgs; };
in
{
  packages.gamescope = gamescopePackage;
  packages.display-change = displayChange;
  files.gamescope = "${gamescopePackage}/bin/gamescope";
  files.display-change = "${displayChange}/bin/gamescope-display-change";
}

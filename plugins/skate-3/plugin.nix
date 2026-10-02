# Native launch behavior stays in skate-3-flake's existing launcher.nix.
{ skate3Package }:
{
  packages.skate3 = skate3Package;
  files.skate3 = "${skate3Package}/bin/skate3";
}

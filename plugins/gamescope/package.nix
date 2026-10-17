{ pkgs }:
assert pkgs.lib.assertMsg (
  pkgs.gamescope.version == "3.16.18"
) "Gamescope launch modifier requires the reviewed Gamescope 3.16.18 flags";
pkgs.gamescope.overrideAttrs (old: {
  # Retain nixpkgs' packaging/system-library patches. The only added patch is
  # ROCKNIX 0001: nested Wayland wl_touch, ValveSoftware/gamescope#1606.
  # Copied from korri b22b82d6a24e6164846ad97adb347e783579b531:
  # nix/devices/odin2portal/rocknix/gamescope/patches/0001-*.patch.
  patches = (old.patches or [ ]) ++ [
    ./patches/0001-WaylandBackend-wire-up-wl_touch-implementation.patch
  ];
})

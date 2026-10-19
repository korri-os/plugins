{ pkgs }:
assert pkgs.lib.assertMsg (
  pkgs.gamescope.version == "3.16.18"
) "Gamescope launch modifier requires the reviewed Gamescope 3.16.18 flags";
pkgs.gamescope.overrideAttrs (old: {
  # Keep nixpkgs' patches and ROCKNIX nested wl_touch (#1606). Backport
  # upstream c2d8f0c3 to reject empty/offscreen viewports before Sway disconnects
  # us. ROCKNIX 0024 moves framebuffer acquisition after that clipping gate so
  # skipped planes do not leak references. Provenance and repro: README.md.
  patches = (old.patches or [ ]) ++ [
    ./patches/0001-WaylandBackend-wire-up-wl_touch-implementation.patch
    ./patches/0002-WaylandBackend-skip-fully-clipped-planes.patch
    ./patches/0003-WaylandBackend-acquire-only-attached-buffers.patch
  ];
})

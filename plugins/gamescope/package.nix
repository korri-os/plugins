{ pkgs }:
assert pkgs.lib.assertMsg (
  pkgs.gamescope.version == "3.16.18"
) "Gamescope launch modifier requires the reviewed Gamescope 3.16.18 flags";
pkgs.gamescope.overrideAttrs (old: {
  # Keep nixpkgs' patches and ROCKNIX nested wl_touch (#1606). Backport
  # upstream c2d8f0c3 to reject empty/offscreen viewports before Sway disconnects
  # us. ROCKNIX 0024 moves framebuffer acquisition after that clipping gate so
  # skipped planes do not leak references. Upstream c50ddfa9 + 6867f509 wait
  # for configure after a real toplevel unmap. Korri-local 0005-0009 run the
  # Vulkan renderer on Mesa panvk for Mali Bifrost (RG353M) with no device
  # configuration. Provenance and repro: README.md.
  patches = (old.patches or [ ]) ++ [
    ./patches/0001-WaylandBackend-wire-up-wl_touch-implementation.patch
    ./patches/0002-WaylandBackend-skip-fully-clipped-planes.patch
    ./patches/0003-WaylandBackend-acquire-only-attached-buffers.patch
    ./patches/0004-WaylandBackend-await-configure-after-unmap.patch
    ./patches/0005-rendervulkan-run-without-nullDescriptor.patch
    ./patches/0006-rendervulkan-bind-only-uploaded-constants.patch
    ./patches/0007-rendervulkan-uncached-mappable-memory-fallback.patch
    ./patches/0008-rendervulkan-compile-pipelines-on-demand.patch
    ./patches/0009-rendervulkan-opt-in-to-panvk-on-bifrost.patch
  ];
})

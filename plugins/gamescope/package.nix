{ pkgs }:
assert pkgs.lib.assertMsg (
  pkgs.gamescope.version == "3.16.31"
) "Gamescope launch modifier requires the reviewed Gamescope 3.16.31 flags";
pkgs.gamescope.overrideAttrs (old: {
  # Keep nixpkgs' patches and ROCKNIX nested wl_touch (#1606). 3.16.31
  # already rejects fully clipped viewports (upstream c2d8f0c3) and waits for
  # configure after a real toplevel unmap (c50ddfa9 + 6867f509). ROCKNIX 0024
  # acquires framebuffers only when attached, after that gate and clipping, so
  # skipped planes do not leak references. Upstream master 56861b7c reverts
  # d12ec394 (lost mouse lock in nested mode). Korri-local 0004-0008 run the
  # Vulkan renderer on Mesa panvk for Mali Bifrost (RG353M) with no device
  # configuration. Provenance and repro: README.md.
  patches = (old.patches or [ ]) ++ [
    ./patches/0001-WaylandBackend-wire-up-wl_touch-implementation.patch
    ./patches/0002-WaylandBackend-acquire-only-attached-buffers.patch
    ./patches/0003-steamcompmgr-revert-nested-pointer-constraint-fix.patch
    ./patches/0004-rendervulkan-run-without-nullDescriptor.patch
    ./patches/0005-rendervulkan-bind-only-uploaded-constants.patch
    ./patches/0006-rendervulkan-uncached-mappable-memory-fallback.patch
    ./patches/0007-rendervulkan-compile-pipelines-on-demand.patch
    ./patches/0008-rendervulkan-opt-in-to-panvk-on-bifrost.patch
  ];
})

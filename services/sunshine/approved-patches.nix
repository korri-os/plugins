rec {
  baseSunshineVersion = "2025.924.154138";
  approvedBaseSourceHash = "sha256-QrPfZqd9pgufohUjxlTpO6V0v7B41UrXHZaESsFjZ48=";
  approvedDeviceBaseDerivation = "/nix/store/5hmg1ff3wjkzcmspssckdlydk0d5bbjz-sunshine-2025.924.154138.drv";
  approvedDeviceBaseDerivations = {
    "x86_64-linux-cuda" = "/nix/store/5hmg1ff3wjkzcmspssckdlydk0d5bbjz-sunshine-2025.924.154138.drv";
    "aarch64-linux-software" =
      "/nix/store/8dhfxx3xi04qvlv8ihrg4p6ycqwx6fhc-sunshine-2025.924.154138.drv";
    "aarch64-linux-rkmpp" = "/nix/store/8dhfxx3xi04qvlv8ihrg4p6ycqwx6fhc-sunshine-2025.924.154138.drv";
  };
  approvedBaseDerivationsByProfile = {
    "x86_64-linux-cuda" = [
      # Korri nixpkgs revision a6531044f6d0bef691ea18d4d4ce44d0daa6e816.
      "/nix/store/63c39c0mjs72ixh20hs18r8l8zh3wix7-sunshine-2025.924.154138.drv"
      # Mountainous nixpkgs revision c06b4ae3d6599a672a6210b7021d699c351eebda.
      "/nix/store/5hmg1ff3wjkzcmspssckdlydk0d5bbjz-sunshine-2025.924.154138.drv"
    ];
    "aarch64-linux-software" = [
      # Korri nixpkgs revision a6531044f6d0bef691ea18d4d4ce44d0daa6e816.
      "/nix/store/8dhfxx3xi04qvlv8ihrg4p6ycqwx6fhc-sunshine-2025.924.154138.drv"
    ];
    "aarch64-linux-rkmpp" = [
      # Same reviewed CUDA-free upstream recipe; RKMPP is added only downstream.
      "/nix/store/8dhfxx3xi04qvlv8ihrg4p6ycqwx6fhc-sunshine-2025.924.154138.drv"
    ];
    "aarch64-linux-rkmpp-v4l2m2m" = [
      # Both encoder patches change the downstream static FFmpeg, not this
      # reviewed upstream Sunshine derivation.
      "/nix/store/8dhfxx3xi04qvlv8ihrg4p6ycqwx6fhc-sunshine-2025.924.154138.drv"
    ];
  };
  approvedBaseDerivations = builtins.concatLists (
    builtins.attrValues approvedBaseDerivationsByProfile
  );
  reviewedLibavcodecVersion = "63.1.101";
  reviewedFfmpegCommit = "bf1b838f2ab88b4f8fd83443325c782ea0e0f7fa";
  reviewedFfmpegSourceHash = "sha256-9Vnryl9jSSXRfvt2jPsNp7vHWL0KYdWA29D2zDRAZ+0=";
  reviewedBuildDepsCommit = "a1fe2841cbc0d8c4501a1006d2d1cb88f219cc8c";
  reviewedBuildDepsSourceHash = "sha256-y24dqgVODlpRnlwlLwK/8n38m2FE1sZpD6V+mgLITTU=";
  v4l2m2mPatches = [
    {
      name = "0001-fix-v4l2m2m-buffer-alignment.patch";
      path = ./patches/ffmpeg/0001-fix-v4l2m2m-buffer-alignment.patch;
      sha256 = "d066bb790cc3ee3bdaf1fd44060fd03fbc875be72d3f225c3b59f734d990d540";
      upstreamPullRequest = "https://code.ffmpeg.org/FFmpeg/FFmpeg/pulls/24328";
      upstreamCommit = "3fda94e1309bead4d39ea4b2cc42d13f8cdf48b4";
      sourceArchive = "https://www.mail-archive.com/ffmpeg-devel@ffmpeg.org/msg190438.html";
    }
    {
      name = "0002-add-v4l2m2m-repeat-headers.patch";
      path = ./patches/ffmpeg/0002-add-v4l2m2m-repeat-headers.patch;
      sha256 = "2d6cd48d31a3b0eae109e2487851a6b0c6b8101de11e70c0817f3d03908686d5";
    }
  ];
  v4l2m2mPatchSetSha256 = "e918232613be4264d0c7c55900ff030674cc66e3f8f37f4daa0c59f1051960a6";
  reviewedNvencApiMajor = 12;
  reviewedNvencApiMinor = 0;
  patchSetSha256 = "64d07a531579a764b001497890eaaf4d635caf6589c6642e6a500c05dc1d2438";
  patches = [
    {
      name = "0015-add-korri-input-seat-event-mirror.patch";
      path = ./patches/0015-add-korri-input-seat-event-mirror.patch;
      sha256 = "f7fe0901a3735e09d08c8dc58c17ff51b687755649579512879467a5fb2a4793";
    }
    {
      name = "0017-use-wayland-ram-capture-for-cuda.patch";
      path = ./patches/0017-use-wayland-ram-capture-for-cuda.patch;
      sha256 = "a87aefc6eb5f71a4d413d751eefb87743745a2fab126dded5b66b23b949f66b2";
    }
    {
      name = "0018-vectorize-wayland-bgr888-with-swscale.patch";
      path = ./patches/0018-vectorize-wayland-bgr888-with-swscale.patch;
      sha256 = "753971f16e33598215caa455074f3bbca23e43b0cf2a2b8a97779f356486203f";
    }
    {
      name = "0019-use-pinned-memory-for-cuda-capture.patch";
      path = ./patches/0019-use-pinned-memory-for-cuda-capture.patch;
      sha256 = "83fd586d210668b06753fdd8bb6312967ba8805ce7a2fdc992c5cbdc49c79c88";
    }
    {
      name = "0020-add-korrid-certificate-control.patch";
      path = ./patches/0020-add-korrid-certificate-control.patch;
      sha256 = "8e97eb5c8cf30a5b80b6a13aa88102de4ff443103875873ae4eb8f483ccfe059";
    }
    {
      name = "0021-add-v4l2m2m-encoder.patch";
      path = ./patches/0021-add-v4l2m2m-encoder.patch;
      sha256 = "64e51b7085e2678d2abb04aafb5d9a4c8d961a2f2b6ced7c7636f85ec67a66b3";
    }
    {
      name = "0038-configure-linux-capture-fifo.patch";
      path = ./patches/0038-configure-linux-capture-fifo.patch;
      sha256 = "314fd4d8bda3ecbe46e30aa394236d6527e558a280676e351e2bcf6508dc8eba";
    }
    {
      name = "0039-bind-paired-client-input-identity.patch";
      path = ./patches/0039-bind-paired-client-input-identity.patch;
      sha256 = "3d8cb7be912b0bd7afa66aa49cd7f0a78be3702e4242fe7bb1bcb52fa161f943";
    }
  ];

  # Applied after every base patch, only for the aarch64-linux-rkmpp profile.
  # It adds the Rockchip MPP H.264 encoder definition and paces its encode
  # loop to the negotiated frame rate.
  rkmppPatch = {
    name = "0022-add-rkmpp-h264-encoder.patch";
    path = ./patches/0022-add-rkmpp-h264-encoder.patch;
    sha256 = "ccaee940f2bfd8b28c2f9487931cfa8ceb1b707770a093df62096d17e6980003";
  };

  # Applied after the RKMPP encoder patch, only for the
  # aarch64-linux-rkmpp profile. It hands compatible KMS scanout dma-bufs
  # directly to h264_rkmpp as DRM_PRIME frames.
  rkmppZeroCopyPatch = {
    name = "0023-add-rkmpp-drm-prime-zero-copy.patch";
    path = ./patches/0023-add-rkmpp-drm-prime-zero-copy.patch;
    sha256 = "601a6ce16580902dae652920f4af819fa19afb7aa430b1c65860b3c8f99b9086";
  };

  # Scope the stdin pairing fix to the device profile while validating it;
  # leave the approved x86 build unchanged.
  stdinPinPatch = {
    name = "0024-fix-stdin-pin-pairing-return.patch";
    path = ./patches/0024-fix-stdin-pin-pairing-return.patch;
    sha256 = "eeab5c78eea1c2c1f72277fb370681b5352b28da75a58668bfda043836b28020";
  };

  # Applied after the stdin pairing fix, only for the aarch64-linux-rkmpp
  # profile. wlroots compositors expose no KMS scanout framebuffer, so the
  # KMS zero-copy route never runs on a Wayland host. This hands the
  # compositor's exported dma-buf to h264_rkmpp as a DRM_PRIME frame, which
  # keeps both the readback and the RGB-to-YUV conversion off the CPU.
  rkmppWaylandPatch = {
    name = "0027-capture-wayland-frames-for-rkmpp.patch";
    path = ./patches/0027-capture-wayland-frames-for-rkmpp.patch;
    sha256 = "d501ea2c8db6ed4905794b036094796a82aa04d147e92f54b6f73feb35f443b5";
  };

  # The compositor has already advertised the capture format before Sunshine
  # creates this buffer. Use linux-dmabuf's immediate creation request to avoid
  # waiting for an extra server callback on every frame.
  rkmppWaylandImmediatePatch = {
    name = "0028-create-wayland-dmabuf-immediately.patch";
    path = ./patches/0028-create-wayland-dmabuf-immediately.patch;
    sha256 = "0433b060174c0ea3bea40612558ec8a9da6d7e9ff6b72bd398fb752b0ecb1d82";
  };

  # Let Wayland capture follow the compositor, then enforce the negotiated
  # frame rate at the async RKMPP encoder boundary with an absolute deadline.
  # This permits capture headroom without sending more than the requested FPS.
  rkmppWaylandPacingPatch = {
    name = "0029-pace-rkmpp-after-wayland-capture.patch";
    path = ./patches/0029-pace-rkmpp-after-wayland-capture.patch;
    sha256 = "902e5f87c1050a0db82aa9760485ef6ea2f0202d8c78fd681cae318f1ac3b0b7";
  };

  # Keep a bounded pool of linear GBM buffers instead of allocating and
  # importing one on every screencopy. A busy token follows each captured image
  # until the encoder releases it, preventing capture/encode reuse races.
  rkmppWaylandBufferPoolPatch = {
    name = "0030-reuse-wayland-capture-buffers.patch";
    path = ./patches/0030-reuse-wayland-capture-buffers.patch;
    sha256 = "194d34f3ba95aba3dd5a0011bca4f9bef1bd6436b8b3d7d43f9d3db15c3cc963";
  };

  # Issue the next screencopy request before handing the current frame to the
  # encoder. Requesting only after the handoff means a request is outstanding
  # for some vblanks but not others, which costs captured frames.
  rkmppWaylandPipelinePatch = {
    name = "0031-pipeline-wayland-capture-requests.patch";
    path = ./patches/0031-pipeline-wayland-capture-requests.patch;
    sha256 = "6d05d0d8f22ee61e7dc51d43080ba0ef7e2acf6786397fe13104146c5c3584cd";
  };

  # The async encode loop reset its deadline from the clock after sleeping,
  # folding each sleep's overshoot into the next period. That drift held the
  # encoder permanently below the negotiated rate. Advance from the previous
  # deadline and resynchronise only after a real stall.
  rkmppEncodeSchedulePatch = {
    name = "0032-keep-an-absolute-rkmpp-encode-schedule.patch";
    path = ./patches/0032-keep-an-absolute-rkmpp-encode-schedule.patch;
    sha256 = "e46d0639328923b43fa165ef9ad66bebc720532acf19140d68802a8f7aa43b18";
  };

  # Accepted from the Mini V2 rotation trial as tested on the device (signed
  # clockwise and SPS-crop candidates, 2026-09-29): rotate KMS capture to the
  # output transform and crop the encoded SPS to the visible size. Patch 0036
  # removes the timing-only probes, not rotation. Devices whose output has no
  # transform take the unrotated path. See rotation-probe.md.
  rotationPatch = {
    name = "0033-rotate-kms-capture-to-output-transform.patch";
    path = ./patches/0033-rotate-kms-capture-to-output-transform.patch;
    sha256 = "0ef6edf82c50f8d700b5ab288f069b5801f404e33b0f2af3e229eee975b0fb1f";
  };
  rotationCropPatch = {
    name = "0034-crop-encoded-sps-to-visible-size.patch";
    path = ./patches/0034-crop-encoded-sps-to-visible-size.patch;
    sha256 = "dd2ef90eba90c1628e418e540502b42aea4c85339c70114ca7a806aa257cbe7f";
  };

  kmsLinearPatch = {
    name = "0035-read-linear-kms-dmabuf.patch";
    path = ./patches/0035-read-linear-kms-dmabuf.patch;
    sha256 = "049202bf0baa783b5936a1d9be4fa17adf63cfb1cbc75d984c904fa1bce5de7a";
  };

  kmsNv12Patch = {
    name = "0036-convert-kms-row-pairs-to-nv12.patch";
    path = ./patches/0036-convert-kms-row-pairs-to-nv12.patch;
    sha256 = "d925d87bb009dbac48b013236ebf9efa98c494c8f128c923fd835247dbdd08a1";
  };

  kmsPacingPatch = {
    name = "0037-preserve-kms-capture-phase.patch";
    path = ./patches/0037-preserve-kms-capture-phase.patch;
    sha256 = "a568a1c9c9a1460dd4bc1893c3028bbaa63eb1b0c86e91055c8aa6a843d11d1c";
  };

  rkmppPatches = [
    rkmppPatch
    rkmppZeroCopyPatch
    stdinPinPatch
    rkmppWaylandPatch
    rkmppWaylandImmediatePatch
    rkmppWaylandPacingPatch
    rkmppWaylandBufferPoolPatch
    rkmppWaylandPipelinePatch
    rkmppEncodeSchedulePatch
    rotationPatch
    rotationCropPatch
    kmsLinearPatch
    kmsNv12Patch
    kmsPacingPatch
  ];

  # Ordered digest of 8 base patches ++ 14 rkmppPatches. Bump after reviewing the
  # complete base-plus-RKMPP patch order.
  rkmppPatchSetSha256 = "749776f23caf2536cf4fe3baa2f920cab05518c0f158f50ccd0e6e46f4891a5c";
}

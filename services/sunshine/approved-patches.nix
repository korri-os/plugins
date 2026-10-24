rec {
  baseSunshineVersion = "2026.914.233613";
  approvedBaseSourceHash = "sha256-HqbswLvX/UiY3nOwxSesBMqnFAF0zKP1ueE6PwDtTNs=";
  approvedDeviceBaseDerivation = "/nix/store/832s1aqgsrkcawmf5pcff634mla3a03r-sunshine-2026.914.233613.drv";
  approvedDeviceBaseDerivations = {
    "x86_64-linux-cuda" = "/nix/store/832s1aqgsrkcawmf5pcff634mla3a03r-sunshine-2026.914.233613.drv";
    "aarch64-linux-software" = "/nix/store/302q240fw26629y5d9099cp86yl0b670-sunshine-2026.914.233613.drv";
    "aarch64-linux-rkmpp" = "/nix/store/302q240fw26629y5d9099cp86yl0b670-sunshine-2026.914.233613.drv";
  };
  approvedBaseDerivationsByProfile = {
    # Korri plugins nixpkgs revision 02c087f3fe673c9e317f206a627cb6b910336dbe.
    "x86_64-linux-cuda" = [ "/nix/store/832s1aqgsrkcawmf5pcff634mla3a03r-sunshine-2026.914.233613.drv" ];
    "aarch64-linux-software" = [ "/nix/store/302q240fw26629y5d9099cp86yl0b670-sunshine-2026.914.233613.drv" ];
    # Same reviewed CUDA-free upstream recipe; RKMPP is added only downstream.
    "aarch64-linux-rkmpp" = [ "/nix/store/302q240fw26629y5d9099cp86yl0b670-sunshine-2026.914.233613.drv" ];
    # Both encoder patches change the downstream static FFmpeg, not this
    # reviewed upstream Sunshine derivation.
    "aarch64-linux-rkmpp-v4l2m2m" = [ "/nix/store/302q240fw26629y5d9099cp86yl0b670-sunshine-2026.914.233613.drv" ];
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
  v4l2m2mPatchSetSha256 = "4aeb0e1fcd2602fca166659fcff9ad74c37abb6d27797ba4eda0c2ef0b7cdf2e";
  reviewedNvencApiMajor = 13;
  reviewedNvencApiMinor = 1;
  patchSetSha256 = "480077e8a76fa390a4e122053882d1605e9e2b23226f09bbb92cb0aa3c3bd484";
  patches = [
    {
      name = "0015-add-korri-input-seat-event-mirror.patch";
      path = ./patches/0015-add-korri-input-seat-event-mirror.patch;
      sha256 = "ef17f7585ae23e869a0b8de932bd094d9f705a4c0629219e4b11b53be00ed2b6";
    }
    {
      name = "0017-use-wayland-ram-capture-for-cuda.patch";
      path = ./patches/0017-use-wayland-ram-capture-for-cuda.patch;
      sha256 = "3ea2bffbcddc618b515bc98a4c0790260b00962fac0306739e39821a52e8587b";
    }
    {
      name = "0018-vectorize-wayland-bgr888-with-swscale.patch";
      path = ./patches/0018-vectorize-wayland-bgr888-with-swscale.patch;
      sha256 = "9c16386d03e8d7508a491b394265406dd69ec362b46f42dc9a73ae296fb25e5b";
    }
    {
      name = "0019-use-pinned-memory-for-cuda-capture.patch";
      path = ./patches/0019-use-pinned-memory-for-cuda-capture.patch;
      sha256 = "52542104b98574f0360b15cee8466b9a104e75ec59d28e1df26fd937a6f92d0c";
    }
    {
      name = "0020-add-korrid-certificate-control.patch";
      path = ./patches/0020-add-korrid-certificate-control.patch;
      sha256 = "40dd5e8c914bac588ec5f167df82355fbb6e2387cffdb04af42d576efa60a2c8";
    }
    {
      name = "0021-add-v4l2m2m-encoder.patch";
      path = ./patches/0021-add-v4l2m2m-encoder.patch;
      sha256 = "9dfa95777c45e230c08a5c150ab9e9b7264bcde41ba5dd74112b6db0dc180e12";
    }
    {
      name = "0038-configure-linux-capture-fifo.patch";
      path = ./patches/0038-configure-linux-capture-fifo.patch;
      sha256 = "388d8ab90e4d06c95cdcb1d1f0c148b4e9a090a18efe8e0d969b93fad3f052d6";
    }
    {
      name = "0039-bind-paired-client-input-identity.patch";
      path = ./patches/0039-bind-paired-client-input-identity.patch;
      sha256 = "f08fb2ba63c534349cf5ab63e7bcfa39f7a063db01a224242812ddc8bda0fa8f";
    }
  ];

  # Applied after every base patch, only for the aarch64-linux-rkmpp profile.
  # It adds the Rockchip MPP H.264 encoder definition and paces its encode
  # loop to the negotiated frame rate.
  rkmppPatch = {
    name = "0022-add-rkmpp-h264-encoder.patch";
    path = ./patches/0022-add-rkmpp-h264-encoder.patch;
    sha256 = "818b5fc1d16a69746e21933d8ce69f8f75c6334149bea5cac2addbc363739fc7";
  };

  # Applied after the RKMPP encoder patch, only for the
  # aarch64-linux-rkmpp profile. It hands compatible KMS scanout dma-bufs
  # directly to h264_rkmpp as DRM_PRIME frames.
  rkmppZeroCopyPatch = {
    name = "0023-add-rkmpp-drm-prime-zero-copy.patch";
    path = ./patches/0023-add-rkmpp-drm-prime-zero-copy.patch;
    sha256 = "11639b5df70d46bee1358b765cb9d202f36734eaefc2b1120d53f4a350c67557";
  };


  # Applied after the zero-copy patch, only for the aarch64-linux-rkmpp
  # profile. wlroots compositors expose no KMS scanout framebuffer, so the
  # KMS zero-copy route never runs on a Wayland host. This hands the
  # compositor's exported dma-buf to h264_rkmpp as a DRM_PRIME frame, which
  # keeps both the readback and the RGB-to-YUV conversion off the CPU.
  rkmppWaylandPatch = {
    name = "0027-capture-wayland-frames-for-rkmpp.patch";
    path = ./patches/0027-capture-wayland-frames-for-rkmpp.patch;
    sha256 = "74a9d3b3551d9e0f7133c417817c9cef6113882c13e35c3cd25de026cc4d47b6";
  };

  # The compositor has already advertised the capture format before Sunshine
  # creates this buffer. Use linux-dmabuf's immediate creation request to avoid
  # waiting for an extra server callback on every frame.
  rkmppWaylandImmediatePatch = {
    name = "0028-create-wayland-dmabuf-immediately.patch";
    path = ./patches/0028-create-wayland-dmabuf-immediately.patch;
    sha256 = "9cd531b77a21ed11ba5f99c4049cde5e8081e79c4b56ee73a48ce6c4a9503cbe";
  };

  # Let Wayland capture follow the compositor, then enforce the negotiated
  # frame rate at the async RKMPP encoder boundary with an absolute deadline.
  # This permits capture headroom without sending more than the requested FPS.
  rkmppWaylandPacingPatch = {
    name = "0029-pace-rkmpp-after-wayland-capture.patch";
    path = ./patches/0029-pace-rkmpp-after-wayland-capture.patch;
    sha256 = "28f0b532a162172e7eee53191265b51caf6d087b5f74ab3bcc912bbb3e455ec6";
  };

  # Keep a bounded pool of linear GBM buffers instead of allocating and
  # importing one on every screencopy. A busy token follows each captured image
  # until the encoder releases it, preventing capture/encode reuse races.
  rkmppWaylandBufferPoolPatch = {
    name = "0030-reuse-wayland-capture-buffers.patch";
    path = ./patches/0030-reuse-wayland-capture-buffers.patch;
    sha256 = "a0ae2553c5278e4245e2911a552f13578644da5c86b42a09386153e3e1881bb8";
  };

  # Issue the next screencopy request before handing the current frame to the
  # encoder. Requesting only after the handoff means a request is outstanding
  # for some vblanks but not others, which costs captured frames.
  rkmppWaylandPipelinePatch = {
    name = "0031-pipeline-wayland-capture-requests.patch";
    path = ./patches/0031-pipeline-wayland-capture-requests.patch;
    sha256 = "fc849deec75baab1e8eba7befdd5f57d82a3ed0c5fe3429b8f8537ef00165163";
  };

  # The async encode loop reset its deadline from the clock after sleeping,
  # folding each sleep's overshoot into the next period. That drift held the
  # encoder permanently below the negotiated rate. Advance from the previous
  # deadline and resynchronise only after a real stall.
  rkmppEncodeSchedulePatch = {
    name = "0032-keep-an-absolute-rkmpp-encode-schedule.patch";
    path = ./patches/0032-keep-an-absolute-rkmpp-encode-schedule.patch;
    sha256 = "28dedb7a2987178f1859c0fed739d4dc841174c833285bf6d7b0dd41d79588e2";
  };

  # Accepted from the Mini V2 rotation trial as tested on the device (signed
  # clockwise and SPS-crop candidates, 2026-09-29): rotate KMS capture to the
  # output transform and crop the encoded SPS to the visible size. Patch 0036
  # removes the timing-only probes, not rotation. Devices whose output has no
  # transform take the unrotated path. See rotation-probe.md.
  rotationPatch = {
    name = "0033-rotate-kms-capture-to-output-transform.patch";
    path = ./patches/0033-rotate-kms-capture-to-output-transform.patch;
    sha256 = "bcdaa3f1a0401f9a88f2c47d6b08e6b0201695a4a255c51af1fe5cf646648b03";
  };
  rotationCropPatch = {
    name = "0034-crop-encoded-sps-to-visible-size.patch";
    path = ./patches/0034-crop-encoded-sps-to-visible-size.patch;
    sha256 = "0e0688cc462f94813df9d6192aeba9c8f15e115058279563e45daf6986fab461";
  };

  kmsLinearPatch = {
    name = "0035-read-linear-kms-dmabuf.patch";
    path = ./patches/0035-read-linear-kms-dmabuf.patch;
    sha256 = "965f8ef9f7d66c656c6ce4385cbd43fb01969731da35f88ffdf05710ec327afd";
  };

  kmsNv12Patch = {
    name = "0036-convert-kms-row-pairs-to-nv12.patch";
    path = ./patches/0036-convert-kms-row-pairs-to-nv12.patch;
    sha256 = "dc76392269aa18672ce9836b904724b6486d16c57abf57b30e76ba93570bbb65";
  };

  kmsPacingPatch = {
    name = "0037-preserve-kms-capture-phase.patch";
    path = ./patches/0037-preserve-kms-capture-phase.patch;
    sha256 = "cc3fb70f3886f98c7cbe230d92620e3a6feae7604c3a3ebd192a4939f9a2faf1";
  };

  rkmppPatches = [
    rkmppPatch
    rkmppZeroCopyPatch
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

  # Ordered digest of 8 base patches ++ 13 rkmppPatches. Bump after reviewing the
  # complete base-plus-RKMPP patch order.
  rkmppPatchSetSha256 = "0ddf3a31bc2c7a76988784646b1aeb95e1f5825240f524806da123a16c6e4975";
}

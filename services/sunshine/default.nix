{ pkgs, system }:
let
  sunshinePackage = pkgs.callPackage ./package.nix {
    sunshine = pkgs.sunshine;
    cudaSupport = system == "x86_64-linux";
  };
  sunshineV4l2m2mPackage =
    if system == "aarch64-linux" then
      let
        rockchipMpp = pkgs.callPackage ./rockchip-mpp.nix { };
        ffmpegArm = pkgs.callPackage ./ffmpeg-rkmpp-static.nix { inherit rockchipMpp; };
      in
      pkgs.callPackage ./package.nix {
        sunshine = pkgs.sunshine;
        cudaSupport = false;
        rkmppSupport = true;
        ffmpegRkmpp = ffmpegArm;
        ffmpegV4l2m2m = ffmpegArm;
        inherit rockchipMpp;
        libdrm = pkgs.libdrm;
      }
    else
      null;
  sunshineApprovedPatches = import ./approved-patches.nix;
  sunshinePatchDefinitions =
    sunshineApprovedPatches.patches
    ++ (if sunshinePackage.korriRkmppEnabled then sunshineApprovedPatches.rkmppPatches else [ ]);
  sunshinePatchPaths = map (record: record.path) sunshinePatchDefinitions;
  sunshineExpectedPatchSetSha256 =
    if sunshinePackage.korriRkmppEnabled then
      sunshineApprovedPatches.rkmppPatchSetSha256
    else
      sunshineApprovedPatches.patchSetSha256;
  sunshineApprovedBaseDerivations =
    sunshineApprovedPatches.approvedBaseDerivationsByProfile.${sunshinePackage.korriBuildProfile}
      or [ ];
  sunshineBasePackage = pkgs.sunshine.override {
    cudaSupport = sunshinePackage.korriCudaEnabled;
  };
  sunshineApprovedDeviceBaseDerivation =
    sunshineApprovedPatches.approvedDeviceBaseDerivations.${sunshinePackage.korriBuildProfile} or null;
  sunshineOfflineRetirement = import ./offline-retirement.nix { inherit pkgs; };
in
{
  pluginPackage = if sunshineV4l2m2mPackage != null then sunshineV4l2m2mPackage else sunshinePackage;
  packages = {
    sunshine-korri = sunshinePackage;
    sunshine-retire-all-clients = sunshineOfflineRetirement;
  }
  // pkgs.lib.optionalAttrs (sunshineV4l2m2mPackage != null) {
    sunshine-korri-v4l2m2m = sunshineV4l2m2mPackage;
    sunshine-v4l2m2m-probe = import ./v4l2m2m-probe.nix {
      inherit pkgs;
      ffmpeg = pkgs.callPackage ./ffmpeg-v4l2m2m-static.nix { };
    };
  };
  apps.sunshine-retire-all-clients = {
    type = "app";
    program = "${sunshineOfflineRetirement}/bin/sunshine-retire-all-clients";
  };
  checks = {
    sunshine-offline-retirement = sunshineOfflineRetirement;
    sunshine-korri-package = pkgs.runCommand "sunshine-korri-package-check" { } ''
      test -f ${sunshinePackage}/bin/sunshine
      test -x ${sunshinePackage}/bin/sunshine
      ${
        if sunshinePackage.korriCudaEnabled then
          ''
            test ! -L ${sunshinePackage}/bin/sunshine
            test -L ${sunshinePackage}/bin/.sunshine-wrapped
            grep -F '"${sunshinePackage}/bin/.sunshine-wrapped"' ${sunshinePackage}/bin/sunshine >/dev/null
          ''
        else
          ''
            test -L ${sunshinePackage}/bin/sunshine
            case "$(readlink -f ${sunshinePackage}/bin/sunshine)" in
              ${sunshinePackage}/bin/sunshine-*) ;;
              *) exit 1 ;;
            esac
          ''
      }
      test "${sunshinePackage.pname}" = sunshine-korri
      test "${sunshinePackage.version}" = "${pkgs.sunshine.version}-korri"
      test "${toString (builtins.length sunshinePackage.korriPatchNames)}" = 16
      test "${sunshinePackage.korriBaseSunshineVersion}" = "${sunshineApprovedPatches.baseSunshineVersion}"
      test "${sunshinePackage.korriApprovedBaseSunshineSourceHash}" = "${sunshineApprovedPatches.approvedBaseSourceHash}"
      test "${pkgs.sunshine.src.outputHash}" = "${sunshineApprovedPatches.approvedBaseSourceHash}"
      test "${sunshinePackage.korriBaseSunshineSource}" = "${builtins.unsafeDiscardStringContext (toString pkgs.sunshine.src)}"
      test "${sunshinePackage.korriBuildProfile}" = "${system}-${
        if sunshinePackage.korriRkmppEnabled then
          "rkmpp"
        else if sunshinePackage.korriCudaEnabled then
          "cuda"
        else
          "software"
      }"
      test "${sunshinePackage.korriBaseSunshineDerivation}" = "${builtins.unsafeDiscardStringContext sunshineBasePackage.drvPath}"
      test "${toString (builtins.elem sunshinePackage.korriBaseSunshineDerivation sunshineApprovedBaseDerivations)}" = 1
      test "${sunshinePackage.korriApprovedBaseSunshineDerivation}" = "${sunshinePackage.korriBaseSunshineDerivation}"
      test "${toString (sunshineApprovedDeviceBaseDerivation != null)}" = 1
      test "${sunshinePackage.korriReviewedLibavcodecVersion}" = "${sunshineApprovedPatches.reviewedLibavcodecVersion}"
      test "${sunshinePackage.korriReviewedFfmpegCommit}" = "${sunshineApprovedPatches.reviewedFfmpegCommit}"
      test "${sunshinePackage.korriReviewedFfmpegSourceHash}" = "${sunshineApprovedPatches.reviewedFfmpegSourceHash}"
      test "${toString sunshinePackage.korriReviewedNvencApiMajor}" = "${toString sunshineApprovedPatches.reviewedNvencApiMajor}"
      test "${toString sunshinePackage.korriReviewedNvencApiMinor}" = "${toString sunshineApprovedPatches.reviewedNvencApiMinor}"
      test "${toString sunshinePackage.korriCudaEnabled}" = "${toString (system == "x86_64-linux")}"
      # This proof checks the base CUDA/software package. The combined ARM
      # encoder package has its own RKMPP and V4L2 proof below.
      test "${toString sunshinePackage.korriRkmppEnabled}" = ""
      test "${sunshinePackage.korriPatchSetSha256}" = "${sunshineExpectedPatchSetSha256}"
      provenance=${sunshinePackage}/${sunshinePackage.korriProvenanceRelativePath}
      test -f "$provenance"
      grep -Fx 'package=sunshine-korri' "$provenance" >/dev/null
      grep -Fx 'build_profile=${sunshinePackage.korriBuildProfile}' "$provenance" >/dev/null
      grep -Fx 'cuda_enabled=${
        if sunshinePackage.korriCudaEnabled then "1" else "0"
      }' "$provenance" >/dev/null
      grep -Fx 'approved_base_sunshine_source_hash=${sunshineApprovedPatches.approvedBaseSourceHash}' "$provenance" >/dev/null
      grep -Fx 'approved_base_sunshine_derivation=${sunshinePackage.korriBaseSunshineDerivation}' "$provenance" >/dev/null
      grep -Fx 'reviewed_ffmpeg_commit=${sunshineApprovedPatches.reviewedFfmpegCommit}' "$provenance" >/dev/null
      grep -Fx 'reviewed_ffmpeg_source_hash=${sunshineApprovedPatches.reviewedFfmpegSourceHash}' "$provenance" >/dev/null
      grep -Fx 'reviewed_nvenc_api=${toString sunshineApprovedPatches.reviewedNvencApiMajor}.${toString sunshineApprovedPatches.reviewedNvencApiMinor}' "$provenance" >/dev/null
      grep -Fx 'executable=bin/sunshine' "$provenance" >/dev/null
      grep -Fx 'patch_set_sha256=${sunshinePackage.korriPatchSetSha256}' "$provenance" >/dev/null
      touch "$out"
    '';
    sunshine-korri-runtime-settings = import ./runtime-settings-check.nix {
      inherit pkgs sunshinePackage;
      approvedPatchesPath = ./approved-patches.nix;
      patchPaths = sunshinePatchPaths;
      packagePath = ./package.nix;
      readmePath = ./README.md;
    };
    sunshine-korri-input-presence =
      (import ./input-seat-presence-check.nix {
        inherit pkgs;
      }).vm;
    sunshine-korri-input-seat-patch = import ./input-seat-patch-check.nix {
      inherit pkgs sunshinePackage;
      approvedPatchesPath = ./approved-patches.nix;
      nonblockingTestPath = ./test-nonblocking-mirror.py;
      patchPath = ./patches/0015-add-korri-input-seat-event-mirror.patch;
      packagePath = ./package.nix;
      readmePath = ./README.md;
    };
    sunshine-korri-certificate-control = import ./certificate-control-check.nix {
      inherit pkgs sunshinePackage;
      approvedPatchesPath = ./approved-patches.nix;
      patchPath = ./patches/0020-add-korrid-certificate-control.patch;
      packagePath = ./package.nix;
      testPath = ./test-certificate-control.cpp;
    };
    sunshine-korri-v4l2m2m = import ./v4l2m2m-check.nix {
      inherit pkgs sunshinePackage sunshineV4l2m2mPackage;
      approvedPatchesPath = ./approved-patches.nix;
      patchPath = ./patches/0021-add-v4l2m2m-encoder.patch;
      ffmpegPatchPath = ./patches/ffmpeg/0001-fix-v4l2m2m-buffer-alignment.patch;
      ffmpegPackagePath = ./ffmpeg-rkmpp-static.nix;
      packagePath = ./package.nix;
      readmePath = ./README.md;
    };
  };
}

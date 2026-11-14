# Host binaries are integration-test dependencies, never plugin package inputs.
{
  pkgs,
  system,
  korri,
  tailscalePackage,
  sshPackage,
  sunshinePlugin,
  moonlightPlugin,
  hasViewer,
  viewerPlugin,
  viewerOtherContract,
  gameRuntime,
}:
let
  hostPackage = korri.packages.${system}.korri-plugin-host;
  vmHostPackage = korri.checks.${system}.korri-plugin-host-vm;
in
{
  packages.korri-plugin-host = hostPackage;
  checks = {
    korri-plugin-host = hostPackage;
    inherit (korri.checks.${system})
      korri-device-cache
      korri-input-module
      korri-bundle-module
      korri-ssh-host-support
      ;
    korri-sunshine-plugin-admission =
      pkgs.runCommand "korri-sunshine-plugin-admission" { nativeBuildInputs = [ pkgs.jq ]; }
        ''
          ${hostPackage}/bin/korri-plugin seed ${sunshinePlugin} https://cache.example.invalid > receipt.json
          jq -e '.id == "@korri:sunshine" and .desired.state == "Enabled" and .previous == null' receipt.json
          touch "$out"
        '';
    korri-runtime-plugin-host = import "${korri}/services/korrid/plugin-host/vm-test.nix" {
      inherit
        pkgs
        hostPackage
        vmHostPackage
        tailscalePackage
        sshPackage
        gameRuntime
        ;
      korridPackage = korri.packages.${system}.korrid;
      hostModule = korri.nixosModules.korri-plugin-host;
    };
  }
  // pkgs.lib.optionalAttrs hasViewer {
    # #435: korrid starts, observes and stops @korri:viewer through its
    # socket, falls back to Moonlight, and refuses another viewer contract.
    korri-viewer-lifecycle = import "${korri}/services/korrid/viewer-vm-test.nix" {
      inherit
        pkgs
        hostPackage
        moonlightPlugin
        viewerPlugin
        ;
      otherContractPlugin = viewerOtherContract;
      korridPackage = korri.packages.${system}.korrid;
      korridModule = korri.nixosModules.korrid-linux-device;
      hostModule = korri.nixosModules.korri-plugin-host;
    };
  };
}

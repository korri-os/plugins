# Host binaries are integration-test dependencies, never plugin package inputs.
{
  pkgs,
  system,
  korri,
  tailscalePackage,
  sshPackage,
  sunshinePlugin,
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
  };
}

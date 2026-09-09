{ korri }:
korri.inputs.flake-utils.lib.eachSystem [ "x86_64-linux" "aarch64-linux" ] (
  system:
  let
    pkgs = import korri.inputs.nixpkgs {
      inherit system;
      overlays = [ korri.inputs.rust-overlay.overlays.default ];
    };
    tailscalePackage = import ../plugins/tailscale/package.nix { inherit pkgs; };
    hostPackage = korri.packages.${system}.korri-plugin-host;
  in
  {
    packages = {
      korri-tailscale = tailscalePackage;
      korri-plugin-host = hostPackage;
    };
    apps = {
      korri-publish = korri.apps.${system}.korri-publish;
      korri-publisher-check = {
        type = "app";
        program = "${
          pkgs.writeShellApplication {
            name = "korri-publisher-check";
            # Always test this repository's package, never core's fallback fixture.
            text = ''
              exec ${korri.apps.${system}.korri-publisher-check.program} ${tailscalePackage} "$@"
            '';
          }
        }/bin/korri-publisher-check";
      };
    };
    checks = {
      korri-tailscale-package = import ../plugins/tailscale/package-check.nix {
        inherit pkgs;
        tailscale = tailscalePackage;
      };
      korri-plugin-host = hostPackage;
      inherit (korri.checks.${system}) korri-device-cache korri-input-module korri-bundle-module;
      korri-publication-workflow = import ./publication-check.nix { inherit pkgs; };
      korri-runtime-plugin-host = import "${korri}/services/korrid/plugin-host/vm-test.nix" {
        inherit pkgs hostPackage tailscalePackage;
        hostModule = korri.nixosModules.korri-plugin-host;
      };
    };
  }
)

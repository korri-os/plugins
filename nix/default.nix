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
    cacheTool = pkgs.writeShellApplication {
      name = "korri-cache";
      runtimeInputs = [
        pkgs.python3
        pkgs.nix
        pkgs.gh
      ];
      text = ''
        exec python3 ${./github-cache.py} "$@"
      '';
    };
  in
  {
    packages = {
      korri-tailscale = tailscalePackage;
      korri-plugin-host = hostPackage;
      korri-cache = cacheTool;
    };
    apps = {
      korri-cache = {
        type = "app";
        program = "${cacheTool}/bin/korri-cache";
      };
    };
    checks = {
      korri-github-cache = import ./github-cache-check.nix { inherit pkgs; };
      korri-tailscale-package = import ../plugins/tailscale/package-check.nix {
        inherit pkgs;
        tailscale = tailscalePackage;
      };
      korri-plugin-host = hostPackage;
      inherit (korri.checks.${system}) korri-device-cache korri-input-module korri-bundle-module;
      korri-runtime-plugin-host = import "${korri}/services/korrid/plugin-host/vm-test.nix" {
        inherit pkgs hostPackage tailscalePackage;
        hostModule = korri.nixosModules.korri-plugin-host;
      };
    };
  }
)

{ korri }:
korri.inputs.flake-utils.lib.eachSystem [ "x86_64-linux" "aarch64-linux" ] (
  system:
  let
    pkgs = korri.lib.${system}.pkgs;
    mkPlugin = korri.lib.${system}.mkPlugin;
    # Publisher identity enters the immutable manifest before signing. Never
    # rewrite a built package: mGBA already pins RetroArch's exact store path.
    tailscalePackage = mkPlugin {
      publisher.namespace = "@korri";
      source = ../plugins/tailscale;
      plugin = ../plugins/tailscale/plugin.nix;
    };
    retroarchDefinition = import ../plugins/retroarch/plugin.nix { inherit pkgs; };
    retroarchSource = pkgs.runCommand "korri-retroarch-source" { } ''
      mkdir -p "$out"
      cp ${../plugins/retroarch/plugin.ts} "$out/plugin.ts"
    '';
    retroarchPackage = mkPlugin {
      publisher.namespace = "@korri";
      source = retroarchSource;
      plugin = _: retroarchDefinition;
    };
    libretro = import ../plugins/libretro { inherit pkgs mkPlugin; };
    hostPackage = korri.packages.${system}.korri-plugin-host;
    retroarchCheck = pkgs.writeShellApplication {
      name = "korri-retroarch-check";
      runtimeInputs = [
        pkgs.bun
        pkgs.git
        pkgs.nix
      ];
      text = ''
        exec ${pkgs.bash}/bin/bash ${../plugins/retroarch/check.sh}
      '';
    };
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
      korri-plugin-retroarch = retroarchPackage;
      inherit (korri.packages.${system}) korri-plugin-ssh korri-plugin-sunshine;
      korri-plugin-host = hostPackage;
      korri-cache = cacheTool;
    }
    // libretro.packages;
    apps = {
      korri-cache = {
        type = "app";
        program = "${cacheTool}/bin/korri-cache";
      };
      korri-retroarch-check = {
        type = "app";
        program = "${retroarchCheck}/bin/korri-retroarch-check";
      };
    };
    checks = {
      korri-github-cache = import ./github-cache-check.nix { inherit pkgs; };
      korri-tailscale-package = import ./tailscale-check.nix {
        inherit pkgs;
        tailscale = tailscalePackage;
      };
      korri-retroarch-package = import ./retroarch-check.nix {
        inherit pkgs;
        package = retroarchPackage;
        definition = retroarchDefinition;
      };
      korri-retroarch-settings = retroarchDefinition.packages.retroarch-settings;
      korri-libretro-example = import ../plugins/libretro/example-check.nix {
        inherit pkgs mkPlugin;
      };
      korri-libretro-frontend-override = import ../plugins/libretro/frontend-override-check.nix {
        inherit pkgs mkPlugin;
      };
      korri-libretro-typecheck = import ./libretro-typecheck.nix {
        inherit pkgs;
        helper = ../plugins/libretro/retroarch.ts;
        settings = retroarchDefinition.packages.retroarch-settings;
        contract = "${korri}/contracts/generated/korrid.ts";
      };
      korri-plugin-host = hostPackage;
      inherit (korri.checks.${system})
        korri-device-cache
        korri-input-module
        korri-bundle-module
        korri-ssh-upstream
        korri-ssh-host-support
        korri-sunshine-plugin-admission
        ;
      korri-runtime-plugin-host = import "${korri}/services/korrid/plugin-host/vm-test.nix" {
        inherit pkgs hostPackage tailscalePackage;
        korridPackage = korri.packages.${system}.korrid;
        sshPackage = korri.packages.${system}.korri-plugin-ssh;
        gameRuntime = libretro.packages.korri-plugin-mgba;
        hostModule = korri.nixosModules.korri-plugin-host;
      };
    };
  }
)

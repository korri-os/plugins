{
  korri,
  nixpkgs,
  flake-utils,
}:
flake-utils.lib.eachSystem [ "x86_64-linux" "aarch64-linux" ] (
  system:
  let
    pkgs = import nixpkgs {
      inherit system;
      config.allowUnfree = true;
    };
    mkPlugin = korri.lib.${system}.mkPlugin { inherit pkgs; };
    sunshine = import ../services/sunshine { inherit pkgs system; };
    sshPackage = mkPlugin {
      publisher.namespace = "@korri";
      source = ../plugins/ssh;
      plugin = ../plugins/ssh/plugin.nix;
    };
    sunshineDefinition = import ../plugins/sunshine/plugin.nix {
      inherit pkgs;
      sunshinePackage = sunshine.pluginPackage;
    };
    sunshinePlugin = mkPlugin {
      publisher.namespace = "@korri";
      source = ../plugins/sunshine;
      plugin = _: sunshineDefinition;
    };
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
    starterPackDefinition = import ../plugins/starter-pack/plugin.nix {
      inherit pkgs;
      fake08Plugin = libretro.packages.korri-plugin-fake08;
    };
    starterPack = mkPlugin {
      publisher.namespace = "@korri";
      source = ../plugins/starter-pack;
      plugin = _: starterPackDefinition;
    };
    integration = import ./integration.nix {
      inherit
        pkgs
        system
        korri
        tailscalePackage
        sshPackage
        sunshinePlugin
        ;
      gameRuntime = libretro.packages.korri-plugin-mgba;
    };
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
    # Local path overrides can include Git/worktree metadata. The mutation gate
    # compares pristine NAR content, so give it the same clean source as CI.
    churnCore = builtins.path {
      path = korri;
      name = "korri-churn-source";
      filter =
        path: _:
        !(builtins.elem (builtins.baseNameOf path) [
          ".git"
          ".worktree"
          ".worktrees"
          "__pycache__"
        ]);
    };
    churnCheck = pkgs.writeShellApplication {
      name = "korri-plugin-churn-check";
      runtimeInputs = [
        pkgs.python3
        pkgs.nix
      ];
      text = ''
        exec python3 ${./plugin-churn-check.py} --publisher ${../.} --korri ${churnCore} "$@"
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
      korri-plugin-ssh = sshPackage;
      korri-plugin-sunshine = sunshinePlugin;
      korri-plugin-starter-pack = starterPack;
      starter-pack-cartridges = starterPackDefinition.packages.cartridges;
      korri-cache = cacheTool;
      korri-plugin-churn-check = churnCheck;
    }
    // libretro.packages
    // sunshine.packages
    // integration.packages;
    apps = sunshine.apps // {
      korri-cache = {
        type = "app";
        program = "${cacheTool}/bin/korri-cache";
      };
      korri-plugin-churn-check = {
        type = "app";
        program = "${churnCheck}/bin/korri-plugin-churn-check";
      };
      korri-retroarch-check = {
        type = "app";
        program = "${retroarchCheck}/bin/korri-retroarch-check";
      };
    };
    checks =
      sunshine.checks
      // integration.checks
      // {
        korri-plugin-builder = korri.lib.${system}.pluginBuilderCheck { inherit pkgs; };
        korri-ssh-upstream = (import ../plugins/ssh/upstream.nix { inherit pkgs; }).report;
        korri-sunshine-plugin-native = import ../plugins/sunshine/native-check.nix {
          inherit pkgs;
          plugin = sunshineDefinition;
        };
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
        korri-fake08-package = import ../plugins/libretro/fake08/check.nix {
          inherit pkgs;
          package = libretro.packages.korri-plugin-fake08;
          core = libretro.catalogue.fake08.core;
          contract = korri.lib.${system}.pluginContract;
        };
        korri-fake08-admission =
          pkgs.runCommand "korri-fake08-admission" { nativeBuildInputs = [ pkgs.jq ]; }
            ''
              ${korri.packages.${system}.korri-plugin-host}/bin/korri-plugin seed \
                ${libretro.packages.korri-plugin-fake08} https://cache.example.invalid > receipt.json
              jq -e '.id == "@korri:fake08" and .desired.state == "Enabled" and .previous == null' receipt.json
              touch "$out"
            '';
        korri-starter-pack-package = import ./starter-pack-check.nix {
          inherit pkgs;
          package = starterPack;
          cartridges = starterPackDefinition.packages.cartridges;
          fake08Plugin = libretro.packages.korri-plugin-fake08;
        };
        korri-starter-pack-admission = import ./starter-pack-admission.nix {
          inherit pkgs;
          package = starterPack;
          fake08Plugin = libretro.packages.korri-plugin-fake08;
          hostPackage = korri.packages.${system}.korri-plugin-host;
        };
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
          contract = korri.lib.${system}.pluginContract;
        };
      };
  }
)

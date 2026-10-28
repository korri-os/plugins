{
  korri,
  nixpkgs,
  nixpkgs-held,
  nixpkgs-eden,
  flake-utils,
  gitConfigFile ? null,
}:
flake-utils.lib.eachSystem [ "x86_64-linux" "aarch64-linux" ] (
  system:
  let
    packageSet =
      source:
      let
        canonicalPkgs = import source {
          inherit system;
          config.allowUnfree = true;
        };
      in
      if gitConfigFile == null then
        canonicalPkgs
      else
        import source {
          inherit system;
          config = {
            allowUnfree = true;
            inherit gitConfigFile;
          };
          # Sunshine approves and records the exact upstream drv, not only its
          # output. Keep that guarded base intact; custom fetches still use CI.
          overlays = [ (_: _: { sunshine = canonicalPkgs.sunshine; }) ];
        };
    pkgs = packageSet nixpkgs;
    mkPlugin = korri.lib.${system}.mkPlugin { inherit pkgs; };
    # Temporary split (see flake.nix): every Cemu output builds from the held
    # nixpkgs revision.
    heldPkgs = packageSet nixpkgs-held;
    heldMkPlugin = korri.lib.${system}.mkPlugin { pkgs = heldPkgs; };
    sunshine = import ../services/sunshine { inherit pkgs system; };
    moonlightPackage = pkgs.callPackage ../services/moonlight/package.nix { };
    moonlightDefinition = import ../plugins/moonlight/plugin.nix { inherit pkgs moonlightPackage; };
    moonlightPlugin = mkPlugin {
      publisher.namespace = "@korri";
      source = ../plugins/moonlight;
      plugin = _: moonlightDefinition;
    };
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
    fantasyCorePackages = pkgs.lib.genAttrs [ "tic80" "wasm4" "lowresnx" "pzretro" ] (
      name: libretro.packages."korri-plugin-${name}"
    );
    pyxel = import ../plugins/pyxel { inherit pkgs mkPlugin; };
    libretroNativeProbe = import ../plugins/libretro/native-check/probe.nix { inherit pkgs; };
    pyxelNativeProbe = import ../plugins/pyxel/probe.nix { inherit pkgs; };
    gamescopePackage = import ../plugins/gamescope/package.nix { inherit pkgs; };
    gamescopeSource = pkgs.runCommand "korri-gamescope-source" { } ''
      mkdir -p "$out"
      cp ${../plugins/gamescope/plugin.ts} "$out/plugin.ts"
      cp ${../plugins/gamescope/compose.ts} "$out/compose.ts"
    '';
    gamescopePlugin = mkPlugin {
      publisher.namespace = "@korri";
      source = gamescopeSource;
      plugin = _: import ../plugins/gamescope/plugin.nix { inherit gamescopePackage; };
    };
    # Core ADR 0012: korrid acquires declared artifacts before launch. Steam's
    # manifest still names the exact runtime plugin builds published beside it.
    # A plain string read during evaluation; korri-proton-tool-name checks it
    # against Core's evaluator. Plugin builds take no host recipe.
    protonToolName = import ../plugins/proton/cachyos/tool-name.nix { inherit (pkgs) lib; };
    pluginSourceOnly =
      dir:
      pkgs.lib.fileset.toSource {
        root = dir;
        fileset = dir + "/plugin.ts";
      };
    fexPlugin = mkPlugin {
      publisher.namespace = "@korri";
      source = pluginSourceOnly ../plugins/fex;
      plugin = ../plugins/fex/plugin.nix;
    };
    protonPlugin = mkPlugin {
      publisher.namespace = "@korri";
      source = pluginSourceOnly ../plugins/proton;
      plugin = _: import ../plugins/proton/plugin.nix { inherit pkgs protonToolName; };
    };
    steamPlugin = mkPlugin {
      publisher.namespace = "@korri";
      source = pluginSourceOnly ../plugins/steam;
      plugin =
        _:
        import ../plugins/steam/plugin.nix {
          inherit
            pkgs
            fexPlugin
            protonPlugin
            protonToolName
            ;
        };
    };
    # Acquisition plugins (Core ADR 0013/0014): source only. pico8 is a search
    # provider that names the hosts korrid may reach for it; homebrewhub and
    # retrobrews declare games with pinned artifacts. Tests, fixtures and live
    # probes stay in this repository.
    acquisitionPlugin =
      name:
      mkPlugin {
        publisher.namespace = "@korri";
        source = pluginSourceOnly (../plugins + "/${name}");
        plugin = ../plugins + "/${name}/plugin.nix";
      };
    pico8Plugin = acquisitionPlugin "pico8";
    itchioPlugin = acquisitionPlugin "itchio";
    tic80GalleryPlugin = acquisitionPlugin "tic80gallery";
    wasm4GalleryPlugin = acquisitionPlugin "wasm4gallery";
    lowresnxGalleryPlugin = acquisitionPlugin "lowresnxgallery";
    puzzlescriptPlugin = acquisitionPlugin "puzzlescript";
    pyxelGalleryPlugin = acquisitionPlugin "pyxelgallery";
    homebrewhubPlugin = acquisitionPlugin "homebrewhub";
    retrobrewsPlugin = acquisitionPlugin "retrobrews";
    acquisitionCheck =
      name: package: hosts:
      import ./acquisition-plugin-check.nix {
        inherit
          pkgs
          package
          name
          hosts
          ;
        contract = korri.lib.${system}.pluginContract;
        hostPackage = korri.packages.${system}.korri-plugin-host;
      };
    cemuTurnip = import ../plugins/cemu/turnip.nix { pkgs = heldPkgs; };
    cemuPackage = import ../plugins/cemu/package.nix {
      pkgs = heldPkgs;
      turnip = cemuTurnip;
    };
    cemuPlugin = heldMkPlugin {
      publisher.namespace = "@korri";
      source = pluginSourceOnly ../plugins/cemu;
      plugin = _: import ../plugins/cemu/plugin.nix { inherit cemuPackage; };
    };
    # Isolate Eden's newer dependencies from Sunshine's approved base derivation.
    edenPkgs = import nixpkgs-eden { inherit system; };
    edenPackage = import ../plugins/eden/package.nix { pkgs = edenPkgs; };
    edenBench = import ../plugins/eden/bench { inherit pkgs; };
    edenPlugin = mkPlugin {
      publisher.namespace = "@korri";
      source = pluginSourceOnly ../plugins/eden;
      plugin = _: import ../plugins/eden/plugin.nix { inherit edenPackage; };
    };
    bitsyboxPackage = import ../plugins/bitsybox/package.nix { inherit pkgs; };
    bitsyboxPlugin = mkPlugin {
      publisher.namespace = "@korri";
      source = pluginSourceOnly ../plugins/bitsybox;
      plugin = _: import ../plugins/bitsybox/plugin.nix { inherit bitsyboxPackage; };
    };
    solarusPackage = import ../plugins/solarus/package.nix { inherit pkgs; };
    solarusPlugin = mkPlugin {
      publisher.namespace = "@korri";
      source = ../plugins/solarus;
      plugin = _: import ../plugins/solarus/plugin.nix { inherit solarusPackage; };
    };
    zquestEngine = import ../plugins/zquest-classic/package.nix { inherit pkgs; };
    zquestLauncher = import ../plugins/zquest-classic/launcher.nix {
      inherit pkgs;
      engine = zquestEngine;
    };
    zquestPlugin = mkPlugin {
      publisher.namespace = "@korri";
      source = pkgs.lib.fileset.toSource {
        root = ../plugins/zquest-classic;
        fileset = ../plugins/zquest-classic/plugin.ts;
      };
      plugin = _: import ../plugins/zquest-classic/plugin.nix { launcher = zquestLauncher; };
    };
    starterPackDefinition = import ../plugins/starter-pack/plugin.nix {
      inherit pkgs solarusPlugin zquestPlugin;
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
        export KORRI_CHECKS_ATTRIBUTE=${if gitConfigFile == null then "checks" else "ci.checks"}
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
    cemuBench = import ../plugins/cemu/bench { pkgs = heldPkgs; };
    cacheTool = pkgs.writeShellApplication {
      name = "korri-cache";
      runtimeInputs = [
        pkgs.python3
        pkgs.nix
        pkgs.gh
        pkgs.git
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
      korri-plugin-moonlight = moonlightPlugin;
      moonlight-embedded-korri = moonlightPackage;
      korri-plugin-bitsybox = bitsyboxPlugin;
      bitsybox = bitsyboxPackage;
      korri-plugin-pyxel = pyxel.plugin;
      pyxel = pyxel.package;
      # Off-device acceptance tools, not plugins or game-runtime dependencies.
      korri-libretro-native-probe = libretroNativeProbe;
      korri-pyxel-native-probe = pyxelNativeProbe;
      korri-plugin-solarus = solarusPlugin;
      solarus = solarusPackage;
      cemu = cemuPackage;
      korri-plugin-cemu = cemuPlugin;
      eden = edenPackage;
      eden-bench = edenBench;
      korri-plugin-eden = edenPlugin;
      korri-plugin-zquest-classic = zquestPlugin;
      zquest-classic = zquestLauncher;
      zquest-classic-source = import ./zquest-source-release.nix {
        inherit pkgs;
        engine = zquestEngine;
      };
      korri-plugin-gamescope = gamescopePlugin;
      gamescope = gamescopePackage;
      korri-plugin-fex = fexPlugin;
      korri-plugin-proton = protonPlugin;
      korri-plugin-steam = steamPlugin;
      korri-plugin-pico8 = pico8Plugin;
      korri-plugin-itchio = itchioPlugin;
      korri-plugin-tic80gallery = tic80GalleryPlugin;
      korri-plugin-wasm4gallery = wasm4GalleryPlugin;
      korri-plugin-lowresnxgallery = lowresnxGalleryPlugin;
      korri-plugin-puzzlescript = puzzlescriptPlugin;
      korri-plugin-pyxelgallery = pyxelGalleryPlugin;
      korri-plugin-homebrewhub = homebrewhubPlugin;
      korri-plugin-retrobrews = retrobrewsPlugin;
      korri-plugin-starter-pack = starterPack;
      starter-pack-cartridges = starterPackDefinition.packages.cartridges;
      korri-cemu-bench = cemuBench;
      korri-cache = cacheTool;
      korri-plugin-churn-check = churnCheck;
    }
    // libretro.packages
    // sunshine.packages
    // integration.packages;
    # `nix run` treats only top-level `apps.<system>` as apps, so the CI-only
    # outputs expose the check runner as a plain derivation instead.
    ${if gitConfigFile == null then null else "tools"} = {
      korri-retroarch-check = retroarchCheck;
    };
    apps = sunshine.apps // {
      korri-cemu-bench = {
        type = "app";
        program = "${cemuBench}/bin/korri-cemu-bench";
      };
      korri-libretro-native-probe = {
        type = "app";
        program = "${libretroNativeProbe}/bin/korri-libretro-native-probe";
      };
      korri-pyxel-native-probe = {
        type = "app";
        program = "${pyxelNativeProbe}/bin/korri-pyxel-native-probe";
      };
      eden-bench = {
        type = "app";
        program = "${edenBench}/bin/korri-eden-bench";
      };
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
    publicationChecks = import ./publication-checks.nix {
      inherit (pkgs) lib;
      libretroPackages = libretro.packages;
      sunshineChecks = sunshine.checks;
      sunshinePackages = sunshine.packages;
    };
    checks =
      sunshine.checks
      // integration.checks
      // {
        korri-eden-bench = edenBench;
        korri-eden-package = import ./eden-check.nix {
          inherit pkgs edenPackage;
          package = edenPlugin;
          contract = korri.lib.${system}.pluginContract;
        };
        korri-eden-admission = import ./eden-admission.nix {
          inherit pkgs;
          package = edenPlugin;
          hostPackage = korri.packages.${system}.korri-plugin-host;
          korridPackage = korri.packages.${system}.korrid;
        };
        korri-plugin-builder = korri.lib.${system}.pluginBuilderCheck { inherit pkgs; };
        korri-native-fantasy-runners = import ../plugins/libretro/native-check/check.nix {
          inherit pkgs;
          packages = fantasyCorePackages;
          contract = korri.lib.${system}.pluginContract;
        };
        korri-pyxel-native = import ../plugins/pyxel/check.nix {
          inherit pkgs;
          package = pyxel.plugin;
          contract = korri.lib.${system}.pluginContract;
        };
        korri-fantasy-runner-admission = import ./fantasy-runner-admission.nix {
          inherit pkgs;
          hostPackage = korri.packages.${system}.korri-plugin-host;
          packages = fantasyCorePackages // {
            pyxel = pyxel.plugin;
          };
        };
        korri-ssh-upstream = (import ../plugins/ssh/upstream.nix { inherit pkgs; }).report;
        korri-moonlight-server-pin = import ../services/moonlight/server-pin-check.nix {
          inherit pkgs moonlightPackage;
        };
        korri-moonlight-plugin-native = import ../plugins/moonlight/native-check.nix {
          inherit pkgs;
          plugin = moonlightDefinition;
          package = moonlightPlugin;
          hostPackage = korri.packages.${system}.korri-plugin-host;
        };
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
        korri-retroarch-netplay-password =
          import ../plugins/retroarch/patches/retroarch-netplay-config-password-check.nix
            {
              inherit pkgs;
              program = retroarchDefinition.packages.retroarch;
            };
        korri-retroarch-netplay-host-during-play =
          import ../plugins/retroarch/patches/retroarch-netplay-host-during-play-check.nix
            {
              inherit pkgs;
              program = retroarchDefinition.packages.retroarch;
            };
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
        korri-fex-package = import ../plugins/fex/packages/plugin-check.nix {
          inherit pkgs;
          plugin = fexPlugin;
        };
        korri-proton-package = import ../plugins/proton/packages/plugin-check.nix {
          inherit pkgs;
          plugin = protonPlugin;
          inherit protonToolName;
        };
        korri-steam-package = import ../plugins/steam/packages/plugin-check.nix {
          inherit pkgs fexPlugin protonPlugin;
          plugin = steamPlugin;
        };
        korri-fex-source = import ../plugins/fex/packages/check.nix { inherit pkgs; };
        korri-proton-source = import ../plugins/proton/packages/check.nix { inherit pkgs; };
        korri-proton-tool-name = import ../plugins/proton/packages/tool-name-check.nix {
          inherit pkgs protonToolName;
          evaluator = korri.packages.${system}.korri-plugin-host;
        };
        korri-steam-declaration = import ../plugins/steam/packages/declaration-check.nix {
          inherit pkgs;
          contract = korri.lib.${system}.pluginContract;
        };
        korri-steam-source = import ../plugins/steam/packages/check.nix { inherit pkgs; };
        korri-pico8-plugin = acquisitionCheck "pico8" pico8Plugin [ "www.lexaloffle.com" ];
        korri-itchio-plugin = acquisitionCheck "itchio" itchioPlugin [
          "itch.io"
          "0neforgetfulbug.itch.io"
          "itchio-mirror.cb031a832f44726753d6267436f3b414.r2.cloudflarestorage.com"
        ];
        korri-tic80gallery-plugin = acquisitionCheck "tic80gallery" tic80GalleryPlugin [ "tic80.com" ];
        korri-wasm4gallery-plugin = acquisitionCheck "wasm4gallery" wasm4GalleryPlugin [ "wasm4.org" ];
        korri-lowresnxgallery-plugin = acquisitionCheck "lowresnxgallery" lowresnxGalleryPlugin [
          "lowresnx.inutilis.com"
        ];
        korri-puzzlescript-plugin = acquisitionCheck "puzzlescript" puzzlescriptPlugin [
          "www.puzzlescript.net"
          "gist.githubusercontent.com"
        ];
        korri-pyxelgallery-plugin = acquisitionCheck "pyxelgallery" pyxelGalleryPlugin [
          "api.github.com"
          "raw.githubusercontent.com"
        ];
        korri-homebrewhub-plugin = acquisitionCheck "homebrewhub" homebrewhubPlugin [ ];
        korri-retrobrews-plugin = acquisitionCheck "retrobrews" retrobrewsPlugin [ ];
        korri-gamescope-plugin = import ./gamescope-check.nix {
          inherit pkgs gamescopePackage;
          package = gamescopePlugin;
          contract = korri.lib.${system}.pluginContract;
        };
        korri-cemu-package = import ./cemu-check.nix {
          inherit cemuPackage;
          pkgs = heldPkgs;
          package = cemuPlugin;
          contract = korri.lib.${system}.pluginContract;
        };
        korri-cemu-admission = import ./cemu-admission.nix {
          pkgs = heldPkgs;
          package = cemuPlugin;
          hostPackage = korri.packages.${system}.korri-plugin-host;
          korridPackage = korri.packages.${system}.korrid;
        };
        korri-bitsybox-plugin = import ../plugins/bitsybox/check.nix {
          inherit pkgs;
          package = bitsyboxPlugin;
          contract = korri.lib.${system}.pluginContract;
          hostPackage = korri.packages.${system}.korri-plugin-host;
          korridPackage = korri.packages.${system}.korrid;
        };
        korri-solarus-plugin = import ./solarus-check.nix {
          inherit pkgs solarusPackage;
          package = solarusPlugin;
          contract = korri.lib.${system}.pluginContract;
          hostPackage = korri.packages.${system}.korri-plugin-host;
          korridPackage = korri.packages.${system}.korrid;
        };
        korri-starter-pack-solarus-runtime = import ./solarus-starter-runtime-check.nix {
          inherit pkgs solarusPackage;
          cartridges = starterPackDefinition.packages.cartridges;
        };
        korri-zquest-classic-plugin = import ./zquest-check.nix {
          inherit pkgs;
          package = zquestPlugin;
          engine = zquestEngine;
          contract = korri.lib.${system}.pluginContract;
          hostPackage = korri.packages.${system}.korri-plugin-host;
          korridPackage = korri.packages.${system}.korrid;
        };
        korri-starter-pack-lantern-hollow = import ./lantern-hollow-check.nix {
          inherit pkgs;
          engine = zquestEngine;
          cartridges = starterPackDefinition.packages.cartridges;
        };
        korri-starter-pack-package = import ./starter-pack-check.nix {
          inherit pkgs solarusPlugin zquestPlugin;
          package = starterPack;
          cartridges = starterPackDefinition.packages.cartridges;
          fake08Plugin = libretro.packages.korri-plugin-fake08;
        };
        korri-starter-pack-admission = import ./starter-pack-admission.nix {
          inherit pkgs solarusPlugin zquestPlugin;
          package = starterPack;
          fake08Plugin = libretro.packages.korri-plugin-fake08;
          hostPackage = korri.packages.${system}.korri-plugin-host;
        };
        korri-libretro-netplay = import ../plugins/libretro/netplay-check.nix {
          inherit pkgs;
          plugins = libretro.packages;
          contract = korri.lib.${system}.pluginContract;
        };
        korri-libretro-example = import ../plugins/libretro/example-check.nix {
          inherit pkgs mkPlugin;
        };
        korri-libretro-frontend-override = import ../plugins/libretro/frontend-override-check.nix {
          inherit pkgs mkPlugin;
        };
        korri-libretro-typecheck = import ./libretro-typecheck.nix {
          inherit pkgs;
          inherit (libretro) catalogue;
          plugins = libretro.packages;
          helper = ../plugins/libretro/retroarch.ts;
          settings = retroarchDefinition.packages.retroarch-settings;
          contract = korri.lib.${system}.pluginContract;
        };
      };
  }
)

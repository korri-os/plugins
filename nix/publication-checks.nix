# Publication gates, grounded in the package consumers in nix/default.nix.
# General regression coverage runs independently in plugin-checks.yml. Keep
# native runtime/admission gates when that runtime is actually in the batch.
{
  lib,
  libretroPackages,
  sunshineChecks,
  sunshinePackages,
}:
let
  retroarch = [
    "korri-retroarch-package"
    "korri-retroarch-settings"
    "korri-libretro-example"
    "korri-libretro-frontend-override"
    "korri-libretro-typecheck"
    "korri-libretro-netplay"
  ];
  fantasy = [
    "korri-native-fantasy-runners"
    "korri-fantasy-runner-admission"
  ];
  fake08 = retroarch ++ [
    "korri-fake08-package"
    "korri-fake08-admission"
  ];
  solarus = [ "korri-solarus-plugin" ];
  zquest = [ "korri-zquest-classic-plugin" ];
  fex = [
    "korri-fex-package"
    "korri-fex-source"
  ];
  proton = [
    "korri-proton-package"
    "korri-proton-source"
    "korri-proton-tool-name"
  ];
  cemu = [
    "korri-cemu-package"
    "korri-cemu-admission"
  ];
  eden = [
    "korri-eden-package"
    "korri-eden-admission"
    "korri-eden-bench"
  ];
  pyxel = [
    "korri-pyxel-native"
    "korri-fantasy-runner-admission"
  ];
  gamescope = [ "korri-gamescope-plugin" ];
  bitsybox = [ "korri-bitsybox-plugin" ];
  moonlight = [
    "korri-moonlight-server-pin"
    "korri-moonlight-plugin-native"
  ];
  sunshine = builtins.attrNames sunshineChecks ++ [
    "korri-sunshine-plugin-native"
    "korri-sunshine-plugin-admission"
  ];
in
lib.genAttrs (builtins.attrNames libretroPackages) (_: retroarch)
// lib.genAttrs (map (name: "korri-plugin-${name}") [
  "tic80"
  "wasm4"
  "lowresnx"
  "pzretro"
]) (_: retroarch ++ fantasy)
// {
  korri-plugin-fake08 = fake08;
  korri-plugin-retroarch = retroarch;
  korri-tailscale = [ "korri-tailscale-package" ];
  korri-plugin-ssh = [
    "korri-ssh-upstream"
    "korri-ssh-host-support"
  ];
  korri-plugin-sunshine = sunshine;
  sunshine-korri = sunshine;
  sunshine-retire-all-clients = [ "sunshine-offline-retirement" ];
  korri-plugin-moonlight = moonlight;
  moonlight-embedded-korri = moonlight;
  korri-plugin-bitsybox = bitsybox;
  inherit
    bitsybox
    cemu
    eden
    gamescope
    pyxel
    ;
  korri-plugin-cemu = cemu;
  korri-cemu-bench = cemu;
  korri-plugin-eden = eden;
  eden-bench = eden;
  korri-plugin-gamescope = gamescope;
  korri-plugin-pyxel = pyxel;
  korri-pyxel-native-probe = pyxel;
  korri-libretro-native-probe = fantasy;
  korri-plugin-solarus = solarus;
  inherit solarus;
  korri-plugin-zquest-classic = zquest;
  zquest-classic = zquest;
  zquest-classic-source = zquest;
  korri-plugin-fex = fex;
  korri-plugin-proton = proton;
  korri-plugin-steam =
    fex
    ++ proton
    ++ [
      "korri-steam-package"
      "korri-steam-source"
      "korri-steam-declaration"
    ];
  korri-plugin-starter-pack =
    fake08
    ++ solarus
    ++ zquest
    ++ [
      "korri-starter-pack-package"
      "korri-starter-pack-admission"
      "korri-starter-pack-solarus-runtime"
      "korri-starter-pack-lantern-hollow"
    ];
  starter-pack-cartridges = [
    "korri-starter-pack-package"
    "korri-starter-pack-solarus-runtime"
    "korri-starter-pack-lantern-hollow"
  ];
  # These are publisher/host tools, not native game frontends.
  korri-cache = [ "korri-github-cache" ];
  korri-plugin-churn-check = [ ];
  korri-plugin-host = [ "korri-runtime-plugin-host" ];
}
// lib.genAttrs (map (name: "korri-plugin-${name}") [
  "pico8"
  "itchio"
  "tic80gallery"
  "wasm4gallery"
  "lowresnxgallery"
  "puzzlescript"
  "pyxelgallery"
  "homebrewhub"
  "retrobrews"
]) (package: [ "korri-${lib.removePrefix "korri-plugin-" package}-plugin" ])
// lib.optionalAttrs (sunshinePackages ? sunshine-korri-v4l2m2m) {
  sunshine-korri-v4l2m2m = sunshine;
  sunshine-v4l2m2m-probe = sunshine;
}

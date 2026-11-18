# One session program owns Steam's native paths. plugin.ts names this file and
# hands the session the FEX and Proton files of the exact required builds.
# The publisher composition builds those plugins and passes their outputs.
#
# The engine runner (ADR 0083) adds korri-steam-host, built from `engineMap`
# (the flake input `steam-engine-map`), and its session program.
{
  pkgs,
  fexPlugin,
  protonPlugin,
  protonToolName,
  engineMap,
}:
let
  steam = import ./packages { inherit pkgs protonToolName; };
  engine = import ./packages/engine.nix {
    inherit pkgs engineMap protonToolName;
    inherit (steam) settings helpers;
  };
in
{
  requires = [
    fexPlugin
    protonPlugin
  ];
  packages = {
    steam-session = steam.session;
    korri-steam-host = engine.hostRun;
    steam-engine-session = engine.session;
  };
  files = {
    "steam-session" = "${steam.session}/bin/steam-session";
    # korrid starts this as the engine runner's host (contract of korri#518).
    "korri-steam-host" = "${engine.hostRun}/bin/korri-steam-host";
    "steam-engine-session" = "${engine.session}/bin/steam-engine-session";
  };
}

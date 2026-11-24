# One session program owns Steam's native paths. plugin.ts names this file and
# hands the session the ready FEX and Proton directories that korrid resolves
# from the artifacts the runners name. This plugin requires no exact FEX or
# Proton package (Core ADR 0083): each of the three moves to a new release by
# itself, and Proton's tool name is read from the artifact at launch.
#
# The engine runner (ADR 0083) adds korri-steam-host, built from `engineMap`
# (the flake input `steam-engine-map`), and its session program.
{
  pkgs,
  engineMap,
}:
let
  steam = import ./packages { inherit pkgs; };
  engine = import ./packages/engine.nix {
    inherit pkgs engineMap;
    inherit (steam) settings helpers;
  };
in
{
  packages = {
    steam-session = steam.session;
    korri-steam-host = engine.hostRun;
    steam-engine-session = engine.session;
    steam-legacycompat-unpack = engine.legacycompatUnpack;
  };
  files = {
    "steam-session" = "${steam.session}/bin/steam-session";
    # korrid starts this as the engine runner's host (contract of korri#518).
    "korri-steam-host" = "${engine.hostRun}/bin/korri-steam-host";
    "steam-engine-session" = "${engine.session}/bin/steam-engine-session";
    # korrid runs this on the legacycompat artifact (plugin.ts `unpack`).
    "steam-legacycompat-unpack" = "${engine.legacycompatUnpack}/bin/steam-legacycompat-unpack";
  };
}

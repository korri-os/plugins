# The Steam plugin's engine runner (P/engine) native files (ADR 0083): korri-steam-host
# built from an engine map, its start wrapper, the session program, and the
# Steam FHS they run games and the engine in.
#
# `engineMap` is the flake input `steam-engine-map`: a folder with engine.map.
# The public default (plugins/steam/engine-host/map) is empty; a host built
# from it reports engine_map_missing. A real build overrides the input on aka
# with `--override-input steam-engine-map path:/var/lib/korri-private/steam-engine/<version>`.
{
  pkgs,
  engineMap,
  settings,
  helpers,
  protonToolName,
}:
let
  lib = pkgs.lib;
  host = import ./engine-host.nix { inherit pkgs engineMap; };
  steps = import ./session-steps.nix {
    inherit pkgs;
    runner = "engine";
  };
  # The client runner's FHS rootfs with its own run script: run the command
  # given. SDL3 is the library Proton's winebus loads for controllers; Valve's
  # copy lives in the client, which this runner does not have (spike section 11).
  fhs = import ./steam-korri/fhs.nix {
    inherit pkgs helpers;
    name = "korri-steam-engine-fhs";
    executableName = "korri-steam-engine-fhs";
    runScript = pkgs.writeShellScript "korri-steam-engine-run" ''exec "$@"'';
    extraMultiPkgs = p: [ p.sdl3 ];
  };
  replace =
    file: values:
    lib.replaceStrings (map (name: "@${name}@") (builtins.attrNames values)) (builtins.attrValues values) (
      builtins.readFile file
    );
  hostRun = pkgs.writeShellApplication {
    name = "korri-steam-host";
    runtimeInputs = with pkgs; [
      acl
      coreutils
      findutils
      util-linux
    ];
    text = replace ../engine/host-run.sh {
      fhs = "${fhs}";
      host = "${host}";
      settings = "${settings}";
      inherit protonToolName;
    };
  };
  session = pkgs.writeShellApplication {
    name = "steam-engine-session";
    # The session decides on each failed step itself; it reports a refusal
    # through systemd-notify before it exits.
    bashOptions = [
      "nounset"
      "pipefail"
    ];
    runtimeInputs = with pkgs; [
      coreutils
      gnugrep
      gnused
      jq
      python3
      systemd
      util-linux
    ];
    text = ''
      if [[ "$#" != 1 || ! "$1" =~ ^[1-9][0-9]*$ ]]; then
        echo 'usage: steam-engine-session <appid>' >&2
        exit 2
      fi
      for name in STEAM_ENGINE_HOME KORRI_STEAM_ENGINE_CHANNEL KORRI_PROTON_CACHYOS; do
        if [[ "''${!name:-}" != /* || ! -d "''${!name}" ]]; then
          echo "steam-engine-session: $name must be an existing absolute directory" >&2
          exit 2
        fi
      done
    ''
    + replace ../engine/session.sh {
      fhs = "${fhs}";
      steps = "${steps}";
      launchEntry = "${../engine/launch-entry.py}";
      placeholder = "${../engine/x-placeholder.py}";
    };
  };
in
{
  inherit
    host
    hostRun
    session
    fhs
    steps
    ;
}

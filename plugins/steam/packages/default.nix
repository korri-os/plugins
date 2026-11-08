{ pkgs, protonToolName }:
let
  native = import ./steam-korri { inherit pkgs settings; };
  # ARM64 runs Valve's ARM64 client from the package's own FHS, with FEX for
  # the x86 Steam Runtime helpers. nixpkgs has no ARM64 Steam. x86_64 runs
  # nixpkgs' Steam FHS with the same input guard, and needs no FEX.
  arm = pkgs.stdenv.hostPlatform.isAarch64;
  x86Steam = pkgs.steam.override {
    extraEnv = {
      KORRI_STEAM_INPUT_GUARD = "1";
      SDL_JOYSTICK_DISABLE_UDEV = "1";
    };
    # Steam splices LD_PRELOAD onto overlay paths without adding a separator
    # (see steam-guest-run). The 32-bit helpers ignore this 64-bit library.
    extraProfile = ''
      export LD_PRELOAD=:${native.guard}/lib/libkorri-steam-input-guard.so
    '';
  };
  platform =
    if arm then
      {
        steamClient = "${native.fhs}/bin/steam-arm64-fhs";
        usesFex = "1";
        steamBeta = "steamdeck_stable";
        desktopScaling = "1.5";
      }
    else
      {
        steamClient = "${x86Steam}/bin/steam";
        usesFex = "0";
        steamBeta = "";
        desktopScaling = "";
      };
  requiredPaths = if arm then "KORRI_FEX_CONFIG KORRI_FEX_ROOTFS KORRI_PROTON_CACHYOS" else "KORRI_PROTON_CACHYOS";
  settingsSource = pkgs.runCommand "vdf-settings.py" { } ''
    substitute ${../session/vdf-settings.py} "$out" \
      --replace-fail @protonToolName@ ${pkgs.lib.escapeShellArg protonToolName}
  '';
  settings = pkgs.writeShellApplication {
    name = "steam-vdf-settings";
    runtimeInputs = [ pkgs.python3 ];
    text = ''exec python3 ${settingsSource} "$@"'';
  };
  sessionRun = pkgs.writeShellApplication {
    name = "steam-session-run";
    runtimeInputs = with pkgs; [
      acl
      coreutils
      diffutils
      findutils
      gnugrep
      procps
      util-linux
    ];
    text =
      pkgs.lib.replaceStrings
        [
          "@steamClient@"
          "@usesFex@"
          "@steamBeta@"
          "@desktopScaling@"
          "@helpers@"
          "@settings@"
          "@protonToolName@"
        ]
        [
          platform.steamClient
          platform.usesFex
          platform.steamBeta
          platform.desktopScaling
          "${native.helpers}"
          "${settings}"
          protonToolName
        ]
        (builtins.readFile ../session/steam-session.sh);
  };
  session = pkgs.writeShellApplication {
    name = "steam-session";
    runtimeInputs = [
      pkgs.dbus
      pkgs.coreutils
    ];
    text = ''
      if [[ "$#" != 1 || ! "$1" =~ ^[1-9][0-9]*$ ]]; then
        echo 'usage: steam-session <appid>' >&2
        exit 2
      fi
      if [[ "''${STEAM_HOME:-}" != /* || "''${HOME:-}" != /* ]]; then
        echo 'steam-session: STEAM_HOME and HOME must be absolute paths' >&2
        exit 2
      fi
      if ! mkdir -p "$STEAM_HOME" || [[ ! -w "$STEAM_HOME" ]]; then
        echo 'steam-session: STEAM_HOME is not a writable directory' >&2
        exit 2
      fi
      # plugin.ts passes these from the exact required @korri:fex and
      # @korri:proton builds: the FEX config file and the artifact
      # directories korrid readied before the launch. x86_64 has no FEX.
      required=(${requiredPaths})
      for name in "''${required[@]}"; do
        if [[ "''${!name:-}" != /* ]]; then
          echo "steam-session: $name must be an absolute path" >&2
          exit 2
        fi
        if [[ ! -d "''${!name}" ]]; then
          echo "steam-session: $name is not a directory" >&2
          exit 2
        fi
      done
      status=0
      dbus-run-session -- ${sessionRun}/bin/steam-session-run "$1" || status=$?
      case "$status" in
        0|2|124|126|130|143) exit "$status" ;;
        *) echo "steam-session: Steam failed: session bus or client exited with status $status" >&2; exit 126 ;;
      esac
    '';
  };
in
native
// {
  inherit
    settings
    settingsSource
    session
    sessionRun
    protonToolName
    x86Steam
    ;
  fex = pkgs.fex;
}

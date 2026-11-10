# Focused native/source checks. Invoke with build-host pkgs; no device effects.
{ pkgs }:
let
  steps = import ./session-steps.nix { inherit pkgs; };
  guard =
    (import ./steam-korri {
      inherit pkgs;
      settings = null;
    }).guard;
in
pkgs.runCommand "steam-session-check"
  {
    nativeBuildInputs = with pkgs; [
      acl
      bash
      bun
      shellcheck
      python3
      procps
      util-linux
      stdenv.cc
    ];
  }
  ''
    cp -r ${../session} session
    mkdir -p packages/steam-korri
    cp -r ${./steam-korri/resources} packages/steam-korri/resources
    cp -r ${./steam-korri/scripts} packages/steam-korri/scripts
    cp ${../plugin.ts} plugin.ts
    cp ${./session-steps.ts} packages/session-steps.ts
    export STEAM_SESSION_STEPS=${steps}
    chmod -R u+w session
    python3 -m unittest discover -s session -p 'test_*.py'
    for script in ${../session}/*.sh ${./steam-korri/scripts}/*; do
      bash -n "$script"
      shellcheck -s bash -x "$script"
    done
    $CC -Wall -Wextra -Werror ${./steam-korri/tests/guard-ioctl.c} -o ioctl-probe
    LD_PRELOAD=:${guard}/lib/libkorri-steam-input-guard.so \
      KORRI_STEAM_INPUT_GUARD=1 ./ioctl-probe
    touch "$out"
  ''

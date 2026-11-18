# korri-steam-host's own checks (ADR 0083), offline: rustfmt, the unit tests and
# clippy with the public empty map, then the built host must refuse to start
# with {"event":"engine_map_missing"} and status 1. The same checks with the
# private map run on aka (the private map never enters this repository).
{ pkgs, engineMap }:
let
  host = (import ./engine-host.nix { inherit pkgs engineMap; }).overrideAttrs (_: {
    doCheck = true;
    nativeCheckInputs = [
      pkgs.rustfmt
      pkgs.clippy
    ];
    preCheck = ''
      cargo fmt --check
    '';
    postCheck = ''
      cargo clippy --offline --all-targets -- -D warnings
    '';
  });
in
pkgs.runCommand "korri-steam-host-check" { } ''
  touch steamclient.so
  status=0
  ${host}/bin/korri-steam-host --commands "$PWD/commands" --host-lock "$PWD/host.lock" \
    "$PWD/steamclient.so" >events.jsonl 2>stderr.txt || status=$?
  [ "$status" = 1 ]
  [ "$(cat events.jsonl)" = '{"event":"engine_map_missing"}' ]
  grep -q 'without an engine map' stderr.txt
  touch "$out"
''

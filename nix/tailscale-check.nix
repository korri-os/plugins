{ pkgs, tailscale }:
pkgs.runCommand "korri-tailscale-package-check" { nativeBuildInputs = [ pkgs.jq ]; } ''
  manifest=${tailscale}/manifest.json
  jq -e '
    .publisher == {"namespace": "@korri"} and
    .ports == {"allowedUDPPorts": [41641]} and
    (has("requires") | not) and
    (.services | keys) == ["tailscaled"] and
    (.files | keys) == ["tailscale", "tailscaled"]
  ' "$manifest"
  cli=$(jq -r .files.tailscale "$manifest")
  daemon=$(jq -r .files.tailscaled "$manifest")
  test "$cli" = ${pkgs.tailscale}/bin/tailscale
  test "$daemon" = ${pkgs.tailscale}/bin/tailscaled
  test -x "$cli"
  test -x "$daemon"

  unit=$(jq -r .services.tailscaled "$manifest")
  grep -Fx 'Type=notify' "$unit"
  grep -Fx 'DeviceAllow=/dev/net/tun rw' "$unit"
  grep -Fx 'CapabilityBoundingSet=CAP_NET_ADMIN' "$unit"
  grep -Fx 'CapabilityBoundingSet=CAP_NET_RAW' "$unit"
  test "$(grep -c '^CapabilityBoundingSet=' "$unit")" = 2
  grep -Fx 'ExecStart=${pkgs.tailscale}/bin/tailscaled --state=''${STATE_DIRECTORY}/tailscaled.state --socket=''${RUNTIME_DIRECTORY}/tailscaled.sock --port=41641' "$unit"
  grep -Fx 'ExecStopPost=${pkgs.tailscale}/bin/tailscaled --cleanup' "$unit"
  ! grep -q '^LoadCredential=' "$unit"

  "$cli" version > cli-version
  "$daemon" --version > daemon-version
  test "$(head -n 1 cli-version)" = ${pkgs.lib.escapeShellArg pkgs.tailscale.version}
  test "$(head -n 1 daemon-version)" = ${pkgs.lib.escapeShellArg pkgs.tailscale.version}

  # Never consult the build machine's daemon or join a tailnet.
  if "$cli" --socket="$TMPDIR/not-running.sock" status --json > status 2> error; then
    echo "tailscale status succeeded without a daemon" >&2
    exit 1
  fi
  test -s error

  mkdir -p "$out"
  cp cli-version daemon-version "$out/"
''

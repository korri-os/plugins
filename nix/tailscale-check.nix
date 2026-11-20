{ pkgs, tailscale }:
pkgs.runCommand "korri-tailscale-package-check" { nativeBuildInputs = [ pkgs.jq ]; } ''
  manifest=${tailscale}/manifest.json
  jq -e '
    .publisher == {"namespace": "@korri"} and
    .ports == {"allowedUDPPorts": [41641]} and
    (has("requires") | not) and
    (.services | keys) == ["tailscaled"] and
    (.files | keys) == ["korri-tailscale-account", "logo", "tailscale", "tailscaled"]
  ' "$manifest"
  cli=$(jq -r .files.tailscale "$manifest")
  daemon=$(jq -r .files.tailscaled "$manifest")
  test "$cli" = ${pkgs.tailscale}/bin/tailscale
  test "$daemon" = ${pkgs.tailscale}/bin/tailscaled
  test -x "$cli"
  test -x "$daemon"
  account=$(jq -r '.files["korri-tailscale-account"]' "$manifest")
  logo=$(jq -r .files.logo "$manifest")
  test -x "$account"
  # Tailscale's icon, unchanged from the media kit (README.md, "Logo").
  test "$(sha256sum < "$logo")" = "$(sha256sum < ${../plugins/tailscale/tailscale-icon.svg})"
  grep -q '<svg' "$logo"
  # plugin.ts declares the one account by its file keys (Core ADR 0089).
  grep -F 'program: "korri-tailscale-account"' ${tailscale}/plugin.ts
  grep -F 'logo: "logo"' ${tailscale}/plugin.ts

  unit=$(jq -r .services.tailscaled "$manifest")
  grep -Fx 'Type=notify' "$unit"
  grep -Fx 'DeviceAllow=/dev/net/tun rw' "$unit"
  grep -Fx 'CapabilityBoundingSet=CAP_NET_ADMIN' "$unit"
  grep -Fx 'CapabilityBoundingSet=CAP_NET_RAW' "$unit"
  test "$(grep -c '^CapabilityBoundingSet=' "$unit")" = 2
  grep -Fx 'ExecStart=${pkgs.tailscale}/bin/tailscaled --state=''${STATE_DIRECTORY}/tailscaled.state --socket=''${RUNTIME_DIRECTORY}/tailscaled.sock --port=41641' "$unit"
  grep -Fx 'ExecStopPost=${pkgs.tailscale}/bin/tailscaled --cleanup' "$unit"
  # The one admitted credential; the account host reads it (Core ADR 0034).
  grep -Fx 'LoadCredential=authkey:tailscale-authkey' "$unit"
  test "$(grep -c '^LoadCredential=' "$unit")" = 1

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

  # The account host against the plugin's own CLI with no daemon: it says the
  # daemon does not answer, and ends at the end of its input.
  mkdir run
  printf 'status\n' | RUNTIME_DIRECTORY="$TMPDIR/run" timeout 60 "$account" > account-events
  jq -e -s '. == [{"event": "signin_failed", "reason": "daemon_unreachable"}]' account-events
  RUNTIME_DIRECTORY="$TMPDIR/run" timeout 10 "$account" < /dev/null > account-empty
  test ! -s account-empty

  mkdir -p "$out"
  cp cli-version daemon-version "$out/"
''

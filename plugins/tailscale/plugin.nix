{ pkgs }:
let
  account = import ./account-host.nix { inherit pkgs; };
in
{
  packages = {
    tailscale = pkgs.tailscale;
    korri-tailscale-account = account;
  };
  files = {
    tailscaled = "${pkgs.tailscale}/bin/tailscaled";
    tailscale = "${pkgs.tailscale}/bin/tailscale";
    # Core ADR 0089: the account host plugin.ts names.
    korri-tailscale-account = "${account}/bin/korri-tailscale-account";
  };
  # Native service options match core's Tailscale fixture. The host supplies
  # private state/runtime directories and the final hardening drop-in.
  services.tailscaled = {
    description = "Tailscale";
    serviceConfig = {
      Type = "notify";
      ExecStart = "${pkgs.tailscale}/bin/tailscaled --state=\${STATE_DIRECTORY}/tailscaled.state --socket=\${RUNTIME_DIRECTORY}/tailscaled.sock --port=41641";
      ExecStopPost = "${pkgs.tailscale}/bin/tailscaled --cleanup";
      CapabilityBoundingSet = [
        "CAP_NET_ADMIN"
        "CAP_NET_RAW"
      ];
      DeviceAllow = "/dev/net/tun rw";
      # The one admitted credential (Core ADR 0034). The plugin host gives the
      # account host this service's credentials; with an auth key it signs in
      # without a login link. Korri supplies no value, and a missing
      # credential is not an error.
      LoadCredential = "authkey:tailscale-authkey";
    };
  };
  ports.allowedUDPPorts = [ 41641 ];
}

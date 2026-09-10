{ pkgs }:
{
  packages.tailscale = pkgs.tailscale;
  files = {
    tailscaled = "${pkgs.tailscale}/bin/tailscaled";
    tailscale = "${pkgs.tailscale}/bin/tailscale";
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
    };
  };
  ports.allowedUDPPorts = [ 41641 ];
}

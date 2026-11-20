# The Tailscale plugin's account host (Core ADR 0089), built from its Rust
# source. The plugin host runs it beside tailscaled for each korrid
# connection.
{ pkgs }:
let
  source = pkgs.lib.fileset.toSource {
    root = ./account-host;
    fileset = pkgs.lib.fileset.unions [
      ./account-host/Cargo.toml
      ./account-host/Cargo.lock
      ./account-host/src
      ./account-host/tests
    ];
  };
in
pkgs.rustPlatform.buildRustPackage {
  pname = "korri-tailscale-account";
  version = "0.1.0";
  src = source;
  cargoLock.lockFile = ./account-host/Cargo.lock;
  # The plugin's own CLI; the program drives no other.
  env.KORRI_TAILSCALE_CLI = "${pkgs.tailscale}/bin/tailscale";
  strictDeps = true;
  meta.mainProgram = "korri-tailscale-account";
}

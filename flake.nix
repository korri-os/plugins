{
  description = "Korri plugin packages and release preparation";

  inputs = {
    korri.url = "github:korri-os/korri/80e15526dc7e5d6a004d2fa5ed1218e75b57d942";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  # Index only. Publisher owns its package set; Core supplies the build interface.
  outputs =
    {
      korri,
      nixpkgs,
      flake-utils,
      ...
    }:
    import ./nix { inherit korri nixpkgs flake-utils; };
}

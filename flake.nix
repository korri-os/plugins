{
  description = "Korri plugin packages and release preparation";

  inputs = {
    korri.url = "github:korri-os/korri/d65b285dae77a742dcfb16b030b9fa0c60713d40";
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

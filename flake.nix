{
  description = "Korri plugin packages and release preparation";

  inputs = {
    korri.url = "github:korri-os/korri/7caee2e91f9ed3144dd7df81c8b55985ad92adfa";
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

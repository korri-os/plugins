{
  description = "Korri plugin packages and release preparation";

  inputs = {
    korri.url = "github:korri-os/korri/7f37bd48fe707e523a85ed1cd8ad27e8cfa1b7c3";
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

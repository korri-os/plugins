{
  description = "Korri plugin packages and release preparation";

  inputs = {
    korri.url = "github:korri-os/korri/eab74c96134abed6453ff74c6c80bf4ebca5c52f";
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
    (import ./nix { inherit korri nixpkgs flake-utils; })
    // {
      ci = import ./nix {
        inherit korri nixpkgs flake-utils;
        gitConfigFile = "/run/korri-github-source-auth/gitconfig";
      };
    };
}

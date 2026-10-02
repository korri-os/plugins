{
  description = "Korri plugin packages and release preparation";

  inputs = {
    korri.url = "github:korri-os/korri/80e15526dc7e5d6a004d2fa5ed1218e75b57d942";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    skate3.url = "github:simonwjackson/skate-3-flake/e309e451f644eab95490c8e7c4bab9de398cda40";
  };

  # Index only. Publisher owns its package set; Core supplies the build interface.
  outputs =
    {
      korri,
      nixpkgs,
      flake-utils,
      skate3,
      ...
    }:
    import ./nix {
      inherit
        korri
        nixpkgs
        flake-utils
        skate3
        ;
    };
}

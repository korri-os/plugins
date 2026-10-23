{
  description = "Korri plugin packages and release preparation";

  inputs = {
    korri.url = "github:korri-os/korri/eab74c96134abed6453ff74c6c80bf4ebca5c52f";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # Temporary: the previous nixpkgs lock, held for the plugins that cannot
    # move yet. Every other plugin follows `nixpkgs`. Remove this input when
    # the last holder moves:
    # - Sunshine: its approved base derivations were reviewed against this
    #   revision (services/sunshine/approved-patches.nix). Moves with the
    #   patch-set rebase onto a newer upstream release.
    # - Cemu: aarch64 pins this revision's Mesa 25.3.2 Turnip; Mesa 26.2.x
    #   crashes in IR3 (plugins/cemu/README.md, "Temporary Turnip pin").
    #   Moves when that pin is replaced with a patched 26.2.x Turnip.
    nixpkgs-held.url = "github:NixOS/nixpkgs/a6531044f6d0bef691ea18d4d4ce44d0daa6e816";
    flake-utils.url = "github:numtide/flake-utils";
  };

  # Index only. Publisher owns its package set; Core supplies the build interface.
  outputs =
    {
      korri,
      nixpkgs,
      nixpkgs-held,
      flake-utils,
      ...
    }:
    (import ./nix {
      inherit
        korri
        nixpkgs
        nixpkgs-held
        flake-utils
        ;
    })
    // {
      ci = import ./nix {
        inherit
          korri
          nixpkgs
          nixpkgs-held
          flake-utils
          ;
        gitConfigFile = "/run/korri-github-source-auth/gitconfig";
      };
    };
}

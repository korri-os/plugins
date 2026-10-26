{
  description = "Korri plugin packages and release preparation";

  inputs = {
    korri.url = "github:korri-os/korri/5f4f89e2bc876ba3029cbadfcc0b8641299c90fd";
    nixpkgs-eden.url = "github:NixOS/nixpkgs/02c087f3fe673c9e317f206a627cb6b910336dbe";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # Temporary: the previous nixpkgs lock, held for the plugins that cannot
    # move yet. Every other plugin follows `nixpkgs`. Remove this input when
    # the last holder moves:
    # - Sunshine: its approved base derivations were reviewed against this
    #   revision (services/sunshine/approved-patches.nix). Moves with the
    #   patch-set rebase onto a newer upstream release.
    # - Cemu: retain its runtime dependencies while qualifying the separate
    #   patched Mesa 26.2.5 Turnip (plugins/cemu/README.md). Moving the rest
    #   of Cemu to the current pin needs separate dependency qualification.
    nixpkgs-held.url = "github:NixOS/nixpkgs/a6531044f6d0bef691ea18d4d4ce44d0daa6e816";
    flake-utils.url = "github:numtide/flake-utils";
  };

  # Index only. Publisher owns its package set; Core supplies the build interface.
  outputs =
    {
      korri,
      nixpkgs,
      nixpkgs-held,
      nixpkgs-eden,
      flake-utils,
      ...
    }:
    (import ./nix {
      inherit
        korri
        nixpkgs
        nixpkgs-held
        nixpkgs-eden
        flake-utils
        ;
    })
    // {
      ci = import ./nix {
        inherit
          korri
          nixpkgs
          nixpkgs-held
          nixpkgs-eden
          flake-utils
          ;
        gitConfigFile = "/run/korri-github-source-auth/gitconfig";
      };
    };
}

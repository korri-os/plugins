{
  description = "Korri plugin packages and release preparation";

  inputs = {
    korri.url = "github:korri-os/korri/7ad834303cef21a85d949969f22fdf788e571db6";
    nixpkgs-eden.url = "github:NixOS/nixpkgs/02c087f3fe673c9e317f206a627cb6b910336dbe";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # Temporary: the previous nixpkgs lock, held for the plugins that cannot
    # move yet. Every other plugin follows `nixpkgs`. Remove this input when
    # the last holder moves:
    # - Cemu: retain its runtime dependencies while qualifying the separate
    #   patched Mesa 26.2.5 Turnip (plugins/cemu/README.md). Moving the rest
    #   of Cemu to the current pin needs separate dependency qualification.
    nixpkgs-held.url = "github:NixOS/nixpkgs/a6531044f6d0bef691ea18d4d4ce44d0daa6e816";
    flake-utils.url = "github:numtide/flake-utils";
    # The engine map that korri-steam-host is built from (Core ADR 0083). The
    # public map is empty on purpose; the pinned engine's map is private and is
    # passed on aka with --override-input steam-engine-map path:<folder>.
    steam-engine-map = {
      url = "path:./plugins/steam/engine-host/map";
      flake = false;
    };
  };

  # Index only. Publisher owns its package set; Core supplies the build interface.
  outputs =
    {
      korri,
      nixpkgs,
      nixpkgs-held,
      nixpkgs-eden,
      flake-utils,
      steam-engine-map,
      ...
    }:
    (import ./nix {
      inherit
        korri
        nixpkgs
        nixpkgs-held
        nixpkgs-eden
        flake-utils
        steam-engine-map
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
          steam-engine-map
          ;
        gitConfigFile = "/run/korri-github-source-auth/gitconfig";
      };
    };
}

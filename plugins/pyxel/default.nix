{ pkgs, mkPlugin }:
let
  package = import ./package.nix { inherit pkgs; };
  source = pkgs.lib.fileset.toSource {
    root = ./.;
    fileset = ./plugin.ts;
  };
  plugin = mkPlugin {
    publisher.namespace = "@korri";
    inherit source;
    plugin = _: import ./plugin.nix { pyxelPackage = package; };
  };
in
{
  inherit package plugin;
}

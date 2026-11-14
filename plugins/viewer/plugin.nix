# `viewer` is clients/viewer/default.nix from the Korri input, built with this
# repository's package set (ADR 0061). The binary is GPL-3; its corresponding
# source travels in the same closure as packages.source (ADR 0059).
{ pkgs, viewer }:
let
  setup = pkgs.writeTextFile {
    name = "korri-viewer-setup.service";
    destination = "/lib/systemd/system/korri-viewer-setup.service";
    text = pkgs.lib.replaceStrings [ "@coreutils@" ] [ (toString pkgs.coreutils) ] (
      builtins.readFile ./korri-viewer-setup.service
    );
  };
  identityBootstrap = pkgs.writeScriptBin "korri-viewer-identity-bootstrap" ''
    #!${pkgs.python3}/bin/python3
    ${builtins.readFile ./identity-bootstrap.py}
  '';
in
{
  packages = {
    viewer = viewer.package;
    source = viewer.correspondingSource;
  };
  files = {
    viewer = "${viewer.package}/bin/korri-viewer";
    mapping = "${viewer.package}/share/moonlight/korri-inputplumber-gamecontrollerdb.txt";
    identity-bootstrap = "${identityBootstrap}/bin/korri-viewer-identity-bootstrap";
    # korrid refuses this plugin unless these bytes equal its own copy.
    treaty = "${viewer.package}/share/korri-viewer/viewer.ts";
  };
  services.korri-viewer-setup = "${setup}/lib/systemd/system/korri-viewer-setup.service";
}

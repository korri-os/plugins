{
  pkgs,
  upstream,
  assets,
  patches,
}:
let
  # This is a source release/build input, not an output-filtering wrapper around
  # the old engine. Removed media cannot remain in the runtime's source tree.
  selected = pkgs.runCommand "zquest-classic-reviewed-source" { } ''
    ${pkgs.python3}/bin/python3 ${./prepare-public-source.py} ${upstream} ${assets} "$out"
    cp ${./PUBLIC-CHANGES.txt} "$out/resources/PUBLIC-CHANGES.txt"
  '';
in
pkgs.applyPatches {
  name = "zquest-classic-public-source";
  src = selected;
  inherit patches;
  patchFlags = [ "-p0" ];
}

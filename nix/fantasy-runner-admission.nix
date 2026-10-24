# Real host admission for the five selected runner packages. Native execution
# has separate checks; this gate never starts a game or installs on a device.
{
  pkgs,
  hostPackage,
  packages,
}:
pkgs.runCommand "korri-fantasy-runner-admission"
  {
    nativeBuildInputs = [ pkgs.jq ];
  }
  ''
    export HOME="$TMPDIR/home"
    mkdir -p "$HOME"
    ${pkgs.lib.concatStringsSep "\n" (
      pkgs.lib.mapAttrsToList (name: package: ''
        jq -e '
          .publisher == {namespace: "@korri"} and
          .services == {} and .ports == {} and
          (has("hosts") | not) and (has("requires") | not)
        ' ${package}/manifest.json
        ${hostPackage}/bin/korri-plugin seed \
          ${package} https://cache.example.invalid > ${name}.json
        jq -e '.id == "@korri:${name}" and .desired.state == "Enabled" and .previous == null' ${name}.json
      '') packages
    )}
    touch "$out"
  ''

{
  pkgs,
  package,
  hostPackage,
  korridPackage,
}:
let
  record = pkgs.writeShellScript "record-cemu-arguments" ''
    printf '%s\0' "$@" "$HOME" "$XDG_DATA_HOME" "$PWD"
  '';
in
pkgs.runCommand "korri-cemu-admission" { nativeBuildInputs = [ pkgs.python3 ]; } ''
  python3 ${../plugins/cemu/admission-check.py} ${package} \
    ${hostPackage}/bin/korri-plugin ${korridPackage}/bin/korrid ${record}
  touch "$out"
''

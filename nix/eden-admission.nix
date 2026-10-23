{
  pkgs,
  package,
  hostPackage,
  korridPackage,
}:
let
  record = pkgs.writeShellScript "record-eden-arguments" ''
    printf '%s\0' "$@" "$HOME" "$XDG_DATA_HOME" "$PWD"
  '';
in
pkgs.runCommand "korri-eden-admission" { nativeBuildInputs = [ pkgs.python3 ]; } ''
  python3 ${../plugins/eden/admission-check.py} ${package} \
    ${hostPackage}/bin/korri-plugin ${korridPackage}/bin/korrid ${record}
  touch "$out"
''

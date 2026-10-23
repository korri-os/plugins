# Adapted from legacy:product/plugins/moonlight/removability.test.ts.
{ pkgs, plugin }:
pkgs.runCommand "korri-moonlight-native-check" { nativeBuildInputs = [ pkgs.gnugrep pkgs.python3 pkgs.openssl ]; } ''
  set -eu
  test -x ${plugin.files.moonlight}
  test -s ${plugin.files.mapping}
  test -x ${plugin.files.identity-bootstrap}
  python3 ${./test-identity-bootstrap.py} ${plugin.files.identity-bootstrap}
  unit=${plugin.services.korri-moonlight-setup}
  grep -Fx 'User=korri' "$unit"
  grep -Fx 'Type=oneshot' "$unit"
  grep -Fx 'RemainAfterExit=yes' "$unit"
  grep -E '^ExecStart=/nix/store/[^ ]+/bin/install -d -m 0700 /home/korri/.config/moonlight$' "$unit"
  ! grep -E '^Exec(StartPre|Stop|StopPost)=|rm |nix |network-online|sunshine' "$unit"
  # A removable plugin owns no Core session service, input seat or device rule.
  test ${toString (builtins.length (builtins.attrNames plugin.services))} -eq 1
  ${plugin.files.moonlight} -help >help 2>&1 || true
  grep -F -- '-autowindowresize' help
  grep -F -- 'v4l2m2m' help
  grep -F -- 'x11' help
  touch "$out"
''

# Adapted from legacy:product/plugins/moonlight/removability.test.ts.
{
  pkgs,
  plugin,
  package,
  hostPackage,
}:
pkgs.runCommand "korri-moonlight-native-check"
  {
    nativeBuildInputs = [
      pkgs.gnugrep
      pkgs.python3
      pkgs.openssl
      pkgs.jq
      pkgs.bun
      pkgs.typescript
    ];
  }
  ''
    set -eu
    # Exercise Core's actual unit parser and declaration/unit selection checks.
    # Text assertions alone previously approved an unsupported oneshot service.
    ${hostPackage}/bin/korri-plugin seed ${package} https://cache.example.invalid > receipt.json
    jq -e '.id == "@korri:moonlight" and .desired.state == "Enabled" and .previous == null' receipt.json
    test -x ${plugin.files.moonlight}
    test -s ${plugin.files.mapping}
    test -x ${plugin.files.identity-bootstrap}
    python3 ${./test-identity-bootstrap.py} ${plugin.files.identity-bootstrap}
    unit=${plugin.services.korri-moonlight-setup}
    grep -Fx 'User=korri' "$unit"
    grep -Fx 'Type=exec' "$unit"
    grep -Fx 'Group=korri' "$unit"
    grep -E '^ExecStartPre=\+/nix/store/[^ ]+/bin/install -d -m 0700 -o korri -g korri /home/korri/.config/moonlight$' "$unit"
    grep -E '^ExecStart=/nix/store/[^ ]+/bin/sleep infinity$' "$unit"
    ! grep -E '^Exec(Stop|StopPost)=|rm |nix |network-online|sunshine' "$unit"
    # A removable plugin owns no Core session service, input seat or device rule.
    test ${toString (builtins.length (builtins.attrNames plugin.services))} -eq 1
    ${plugin.files.moonlight} -help >help 2>&1 || true
    grep -F -- '-autowindowresize' help
    grep -F -- 'v4l2m2m' help
    grep -F -- 'x11' help
    mkdir settings-check
    cp ${./plugin.ts} settings-check/plugin.ts
    cp ${./settings.ts} settings-check/settings.ts
    cp ${./settings.test.mts} settings-check/settings.test.ts
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler settings-check/plugin.ts
    bun test ./settings-check/settings.test.ts
    touch "$out"
  ''

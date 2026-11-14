# Admission, native artefacts, corresponding source and settings of
# @korri:viewer. The picture and sound/input checks of the binary are Korri's
# own (clients/viewer), run with this repository's package set.
{
  pkgs,
  plugin,
  package,
  hostPackage,
  korri,
  moonlightSource,
}:
pkgs.runCommand "korri-viewer-native-check"
  {
    nativeBuildInputs = [
      pkgs.gnugrep
      pkgs.gnutar
      pkgs.xz
      pkgs.python3
      pkgs.openssl
      pkgs.jq
      pkgs.bun
      pkgs.typescript
    ];
  }
  ''
    set -eu
    # Core's own parser and declaration checks, as for every plugin.
    ${hostPackage}/bin/korri-plugin seed ${package} https://cache.example.invalid > receipt.json
    jq -e '.id == "@korri:viewer" and .desired.state == "Enabled" and .previous == null' receipt.json
    test -x ${plugin.files.viewer}
    test -s ${plugin.files.mapping}
    test -x ${plugin.files.identity-bootstrap}
    # korrid compares this file with its own copy: it must be the Korri
    # input's generated treaty, byte for byte.
    cmp ${plugin.files.treaty} ${korri}/contracts/generated/viewer.ts
    jq -e --arg treaty ${plugin.files.treaty} '.files.treaty == $treaty' ${package}/manifest.json
    python3 ${./test-identity-bootstrap.py} ${plugin.files.identity-bootstrap} ${plugin.files.viewer}
    unit=${plugin.services.korri-viewer-setup}
    grep -Fx 'User=korri' "$unit"
    grep -Fx 'Type=exec' "$unit"
    grep -Fx 'Group=korri' "$unit"
    grep -E '^ExecStartPre=\+/nix/store/[^ ]+/bin/install -d -m 0700 -o korri -g korri /home/korri/.config/moonlight$' "$unit"
    grep -E '^ExecStart=/nix/store/[^ ]+/bin/sleep infinity$' "$unit"
    ! grep -E '^Exec(Stop|StopPost)=|rm |nix |network-online|sunshine' "$unit"
    test ${toString (builtins.length (builtins.attrNames plugin.services))} -eq 1
    ${plugin.files.viewer} --help > help
    grep -F 'GPL-3.0-or-later' help
    test -s ${plugin.packages.viewer}/share/licenses/korri-viewer/LICENSE
    # GPL-3 corresponding source, in the same closure as the binary.
    tar -tJf ${plugin.packages.source}/share/korri-viewer/korri-viewer-source.tar.xz > sources
    for expected in \
      korri-viewer-source/BUILDING.txt \
      korri-viewer-source/korri/clients/viewer/default.nix \
      korri-viewer-source/korri/clients/viewer/Cargo.lock \
      korri-viewer-source/korri/clients/viewer/LICENSE \
      korri-viewer-source/korri/clients/viewer/src/main.rs \
      korri-viewer-source/korri/contracts/viewer/src/lib.rs \
      korri-viewer-source/moonlight-common-c/src/Limelight.h \
      korri-viewer-source/moonlight-common-c/CMakeLists.txt
    do
      grep -Fx "$expected" sources
    done
    grep -q '^korri-viewer-source/moonlight-common-c/enet/' sources
    grep -q '^korri-viewer-source/vendor/openssl-[0-9]' sources
    # Moonlight's settings, answering for this runner. Moonlight's plugin
    # sits beside it so the test compares the two.
    mkdir -p settings-check/viewer settings-check/moonlight
    cp ${package}/plugin.ts ${package}/settings.ts settings-check/viewer/
    cp ${./settings.test.mts} settings-check/viewer/settings.test.ts
    cp ${moonlightSource}/plugin.ts ${moonlightSource}/settings.ts settings-check/moonlight/
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler settings-check/viewer/plugin.ts
    bun test ./settings-check/viewer/settings.test.ts
    touch "$out"
  ''

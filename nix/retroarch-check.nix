{
  pkgs,
  package,
  definition,
}:
let
  autoconfig = definition.packages.autoconfig;
in
pkgs.runCommand "korri-retroarch-package-check"
  {
    nativeBuildInputs = [ pkgs.jq ];
  }
  ''
    manifest=${package}/manifest.json
    jq -e '
      .publisher == {"namespace": "@korri"} and
      (.packages | keys) == ["autoconfig", "retroarch", "retroarch-settings"] and
      (.files | keys) == ["autoconfig", "retroarch", "retroarch-settings"] and
      .requires == null and
      .services == {} and
      .sources == ["plugin.ts"]
    ' "$manifest"

    test "$(jq -r .files.retroarch "$manifest")" = ${definition.files.retroarch}
    test "$(jq -r '.files["retroarch-settings"]' "$manifest")" = ${definition.files.retroarch-settings}
    test "$(jq -r .files.autoconfig "$manifest")" = ${definition.files.autoconfig}

    retroarch_autoconfig_root="${autoconfig}/share/libretro/autoconfig"
    retroarch_xbox_config="$retroarch_autoconfig_root/udev/Microsoft X-Box 360 pad.cfg"
    upstream_xbox_config="${pkgs.retroarch-joypad-autoconfig}/share/libretro/autoconfig/udev/Microsoft X-Box 360 pad.cfg"
    test -f "$retroarch_xbox_config"
    sed '/^input_menu_toggle_btn\(_label\)\? =/d' "$upstream_xbox_config" \
      | cmp - "$retroarch_xbox_config"
    test "$(grep -Ec '^input_(b|y|select|start|up|down|left|right|a|x|l|r|l2|r2|l3|r3)_(btn|axis) =' "$retroarch_xbox_config")" = 16
    ! grep -Eq '^input_menu_toggle_btn(_label)? =' "$retroarch_xbox_config"

    autoconfig_drift_root="$TMPDIR/autoconfig-drift"
    mkdir -p "$autoconfig_drift_root/udev"
    cp "$upstream_xbox_config" "$autoconfig_drift_root/udev/Microsoft X-Box 360 pad.cfg"
    chmod u+w "$autoconfig_drift_root/udev/Microsoft X-Box 360 pad.cfg"
    printf '\ninput_unreviewed_btn = "99"\n' \
      >> "$autoconfig_drift_root/udev/Microsoft X-Box 360 pad.cfg"
    if (
      ${autoconfig.transform {
        upstreamRoot = "$autoconfig_drift_root";
        outputRoot = "$TMPDIR/autoconfig-drift-output";
      }}
    ); then
      echo "changed upstream Xbox 360 autoconfig unexpectedly passed composition" >&2
      exit 1
    fi

    rm "$autoconfig_drift_root/udev/Microsoft X-Box 360 pad.cfg"
    if (
      ${autoconfig.transform {
        upstreamRoot = "$autoconfig_drift_root";
        outputRoot = "$TMPDIR/autoconfig-missing-output";
      }}
    ); then
      echo "missing upstream Xbox 360 autoconfig unexpectedly passed composition" >&2
      exit 1
    fi

    touch "$out"
  ''

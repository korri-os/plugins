#!@shell@
set -eu
# Gamescope exposes Xwayland without requiring --expose-wayland.
# Allow an explicit offscreen platform for build-host diagnostics.
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
# Do not load the host's portal/GTK platform theme inside the game sandbox.
unset QT_QPA_PLATFORMTHEME

# Eden GUI has no NAND/save CLI options. Rebind its native path keys.
# On ARM game launches, select/check Turnip through Eden's native device index;
# preserve explicit valid selections and every other native setting.
if [ -n "${EDEN_SAVE_ROOT:-}" ]; then
  : "${XDG_CONFIG_HOME:?Eden needs XDG_CONFIG_HOME}"
  : "${XDG_DATA_HOME:?Eden needs XDG_DATA_HOME}"
  config="$XDG_CONFIG_HOME/eden/qt-config.ini"
  nand="$XDG_DATA_HOME/eden/nand"
  saves="$EDEN_SAVE_ROOT/nand"
  "@coreutils@/bin/mkdir" -p "$XDG_CONFIG_HOME/eden" "$nand" "$saves/user/save"
  # Config::BeginGroup/AdjustKey encodes spaces in native INI group names.
  "@crudini@/bin/crudini" --set "$config" 'Data%20Storage' nand_directory "$nand"
  "@crudini@/bin/crudini" --set "$config" 'Data%20Storage' save_directory "$saves"
  # A no-game GUI probe does not require a hardware Vulkan device.
  for argument in "$@"; do
    if [ "$argument" = "-g" ]; then
      @selectVulkan@
      @selectP1@
      break
    fi
  done
fi
# Eden probes cwd/user before XDG. Use an immutable cwd with no portable tree.
cd "@eden@"
exec "@eden@/bin/eden" "$@"

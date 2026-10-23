#!@shell@
set -eu
export PATH="@coreutils@/bin:$PATH"
export LD_LIBRARY_PATH="@libraries@${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
# Cemu-only patched Turnip: finish IR3 fmadz lowering (README).
@turnipDriver@
# wxStandardPaths also derives this from /proc/self/exe's /bin/ prefix.
# Pin its supported override so an inherited host override cannot hide assets.
export WX_CEMU_DATA_DIR="@out@/share/Cemu"
# Cemu's Wayland VulkanCanvas crashes against Gamescope's exposed Wayland
# server. Use its Xwayland instead; direct Wayland launches stay native.
if [ -n "${GAMESCOPE_WAYLAND_DISPLAY:-}" ]; then
  export GDK_BACKEND=x11
fi

# Native files, seeded once; never generate XML in the plugin declaration.
# --help/--version are read-only probes and must not create account state.
case "${1:-}" in --help|-h|--version|-v) exec "@out@/bin/Cemu" "$@" ;; esac
: "${HOME:?Cemu needs HOME}"
config="${XDG_CONFIG_HOME:-$HOME/.config}/Cemu"
data="${XDG_DATA_HOME:-$HOME/.local/share}/Cemu"
mkdir -p "$config" "$data"
if [ ! -e "$config/settings.xml" ]; then
  cp --no-clobber "@out@/share/Cemu/settings.xml" "$config/settings.xml"
  chmod u+w "$config/settings.xml"
fi
# Cemu recursively scans user-data/graphicPacks and its updater replaces
# downloadedGraphicPacks. Copy, do not symlink: manual updates must never write
# into the Nix store. An existing user tree is owned by the user, not this seed.
if [ ! -e "$data/graphicPacks" ]; then
  stage=$(mktemp -d "$data/.graphicPacks.XXXXXX")
  trap 'rm -rf "$stage"' EXIT
  # Account directories inherit setgid. Clear it before creating children:
  # even cp --no-preserve=mode otherwise retains it in chmod, which Core's
  # RestrictSUIDSGID rejects. Keep the account's inherited access ACLs.
  chmod a-s "$stage"
  cp -R --no-preserve=mode "@out@/share/Cemu/graphicPacks/." "$stage/"
  chmod -R a-s,u+w "$stage"
  mv -T --no-clobber "$stage" "$data/graphicPacks"
  rm -rf "$stage"
  trap - EXIT
fi
exec "@out@/bin/Cemu" "$@"

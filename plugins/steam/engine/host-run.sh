# korri-steam-host, as korrid starts it (contract of korri#518):
#   korri-steam-host --commands FIFO --host-lock FILE [--session-lock FILE] DIR/steamclient.so
# with HOME = <person>/steam-engine/home. This wrapper prepares the person's
# engine-only Steam folder (the spike's minimal home, FINDINGS.md section 11),
# then runs the host inside the Steam FHS. packages/engine.nix substitutes the
# @...@ paths. It never reads the engine's sign-in stores.
#
# Layout of <person>/steam-engine:
#   steam/                        the Steam root the engine writes
#   steam/linuxarm64/steamclient.so  link to the engine package's file
#   steam/compatibilitytools.d/@protonToolName@  link to korrid's Proton
#   home/                         HOME of the host and the game
#   home/.steam/steam             link to steam/
#   home/.steam/sdkarm64          link to steam/linuxarm64 (Proton's lsteamclient)
set -Eeuo pipefail
umask 077

say() { printf 'korri-steam-host: %s\n' "$*" >&2; }
# Every refusal here also goes to stdout, which korrid appends to the
# channel's events.jsonl: the session program and korrid read it there, as
# they read the host's own events. The text is fixed; the reason stays on stderr.
fail() {
  trap - ERR
  say "$1"
  printf '%s\n' '{"event":"launch_refused","reason":"host_failed","message":"Steam engine: the engine host could not start"}'
  exit "${2:-1}"
}
trap 'fail "start step failed at line $LINENO" 1' ERR

[[ "$#" -ge 1 ]] || fail 'usage: korri-steam-host --commands FIFO --host-lock FILE [--session-lock FILE] DIR/steamclient.so' 2
engine=${!#}
[[ "$engine" == /*/steamclient.so && -f "$engine" ]] ||
  fail 'the last argument must be the engine package'\''s absolute steamclient.so path' 2
[[ "${HOME:-}" == /*/home ]] || fail 'HOME must be <person>/steam-engine/home' 2
root=${HOME%/home}
steam="$root/steam"

# One engine per Steam folder: a session host and a job host of the same
# person must not run the engine on one folder at once. The lock is on the
# folder, held by this process and the host it becomes.
mkdir -p "$root"
exec 8>>"$root/.korri-engine.lock"
flock -w 30 8 || fail "another engine host uses this Steam folder" 1

mkdir -p "$steam/linuxarm64" "$steam/compatibilitytools.d" "$steam/steamapps" "$HOME/.steam"
ln -sfn "$engine" "$steam/linuxarm64/steamclient.so"
ln -sfn "$steam" "$HOME/.steam/steam"
ln -sfn "$steam/linuxarm64" "$HOME/.steam/sdkarm64"
# Windows games install and run only with a compatibility tool registered
# (InstallApp 29 "Invalid platform" without it, spike section 11).
if [[ "${KORRI_PROTON_CACHYOS:-}" == /* && -d "$KORRI_PROTON_CACHYOS" ]]; then
  ln -sfn "$KORRI_PROTON_CACHYOS" "$steam/compatibilitytools.d/@protonToolName@"
fi
# The folder's own compat-tool mapping, merged into the config the engine
# writes; no other value of that file changes.
@settings@/bin/steam-vdf-settings --engine "$steam" || fail 'cannot write the compat-tool mapping' 1

# The account root is setgid; directories made below it inherit the bit.
find "$root" -xdev -type d -perm -2000 -user "$(id -u)" -exec chmod g-s {} + 2>/dev/null || true
# korrid discovers installed games from steamapps/appmanifest_*.acf and owns
# the account root above this folder. Grant it listing of the path to
# steamapps and reading of the manifests, nothing more.
#
# The engine writes a new manifest while this host runs (an install), and
# korrid scans when the job ends, so steamapps itself keeps a default entry
# that makes new files directly in it readable. A default entry is also
# inherited by every new subfolder, and the engine puts game files, Wine
# prefixes (with saves) and shader caches in subfolders. So the subfolders
# the engine uses are made here with no default entry, and any entry
# inherited earlier is removed from them. A subfolder the engine makes that is
# not in this list would still inherit read for korrid.
daemon_uid=$(stat -c %u "$(dirname "$root")")
if [[ "$daemon_uid" != "$(id -u)" ]]; then
  setfacl -m "u:$daemon_uid:x" "$root"
  setfacl -m "u:$daemon_uid:rx" "$steam"
  setfacl -m "u:$daemon_uid:rx" -m "d:u:$daemon_uid:r" "$steam/steamapps"
  for sub in common downloading compatdata shadercache temp workshop sourcemods; do
    mkdir -p "$steam/steamapps/$sub"
    # Numeric (-n): getfacl prints user names by default, never the uid.
    # Bash matches the entries itself; the wrapper's PATH has no grep.
    acl=$'\n'$(getfacl -n -p "$steam/steamapps/$sub" 2>/dev/null) || acl=''
    if [[ "$acl" == *$'\n'"user:$daemon_uid:"* || "$acl" == *$'\n'"default:user:$daemon_uid:"* ]]; then
      setfacl -R -k -x "u:$daemon_uid" "$steam/steamapps/$sub" 2>/dev/null || true
    fi
  done
  find "$steam/steamapps" -maxdepth 1 -name 'appmanifest_*.acf' -exec setfacl -m "u:$daemon_uid:r" {} +
fi

# The tool the host sets per app through the engine (IClientCompat), which
# also sets the engine's platform override: Windows builds, through Proton.
export KORRI_STEAM_COMPAT_TOOL=@protonToolName@
# The engine registers only the tools it finds. It looks for
# compatibilitytools.d beside the steamclient.so it was loaded from, the
# engine package in korrid's cache (the host's last argument), not in this
# folder. Without this variable it never registers the tool: the per-app
# mapping names an unknown tool and reads back empty, and the engine installs
# Linux builds or refuses Windows-only games with 29 "Invalid platform"
# (korri#531; device proof on the RP Mini V2, 2026-11-20).
export STEAM_EXTRA_COMPAT_TOOLS_PATHS="$steam/compatibilitytools.d"
# The engine must never see a game's identity, display or session bus.
unset SteamAppId SteamGameId SteamOverlayGameId DISPLAY WAYLAND_DISPLAY DBUS_SESSION_BUS_ADDRESS
cd "$steam"
[[ -x @fhs@/bin/korri-steam-engine-fhs && -x @host@/bin/korri-steam-host ]] ||
  fail 'the Steam FHS or the host program is missing' 1
trap - ERR
exec @fhs@/bin/korri-steam-engine-fhs @host@/bin/korri-steam-host "$@"

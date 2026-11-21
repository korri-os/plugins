# steam-engine-session <appid>: the Steam plugin's engine runner (P/engine) session
# program, in the game unit (ADR 0083, contract of korri#518). It is the
# product form of the spike's scripts/mini/steam-shim.sh: no Valve client and
# no Steam UI run. korrid has started korri-steam-host for this session
# before this unit; the two talk through the launch channel:
#   $KORRI_STEAM_ENGINE_CHANNEL/commands      the host's command FIFO
#   $KORRI_STEAM_ENGINE_CHANNEL/session.lock  held by this program for its life
#   $KORRI_STEAM_ENGINE_CHANNEL/events.jsonl  the host's events (korrid appends)
# Order: take the session lock; `install <appid>` (the update before every
# launch); `launched <appid>` and its launch sync; the game through Proton;
# `exited <appid>`. The host runs the exit sync, also when this unit is
# killed (it sees the session lock free). packages/engine.nix substitutes the
# @...@ paths. No per-game logic.
set -Euo pipefail
umask 077

appid="$1"
channel="$KORRI_STEAM_ENGINE_CHANNEL"
fifo="$channel/commands"
events="$channel/events.jsonl"
root="$STEAM_ENGINE_HOME"
steam="$root/steam"
home="$root/home"
fhs=@fhs@/bin/korri-steam-engine-fhs

say() { printf 'steam-engine-session: %s\n' "$*" >&2; }
notify() {
  if [[ -n "${NOTIFY_SOCKET:-}" ]]; then
    systemd-notify --status="$1" || say "could not report: $1"
  fi
}
fail() {
  # $1: exit status; $2: the refusal korrid shows; $3: diagnostics.
  say "${3:-$2}"
  notify "plugin-launch: $2"
  exit "$1"
}
# One line to the host's FIFO. open() waits until the host reads, so it is
# bounded. The writer is this program's own bash ($BASH, an absolute store
# path): the game unit has no sh on its PATH.
to_host() {
  # The inner shell expands its own arguments.
  # shellcheck disable=SC2016
  timeout "$2" "$BASH" -c 'printf "%s\n" "$1" >"$2"' _ "$1" "$fifo" 7>&-
}
# A refusal the host has not reported itself. A wrapper in the game unit
# (gamescope) can end with 0 around this program's exit and take the STATUS
# text with it, so the session host reports the refusal in its events
# (`launch_refused`), where korrid reads it. Only a word from the host's
# closed list is sent. Best effort: a host that is gone cannot report.
# $1: the word; the rest as for fail.
refuse() {
  local word="$1"
  shift
  to_host "refused $word" 5 2>/dev/null ||
    say "could not report the refusal $word to the engine host"
  fail "$@"
}

# The generated steps of runners.engine.steps; steps only move forward.
# shellcheck source=/dev/null
source @steps@
step_index=-1
reach_step() {
  local index
  # The generated steps module assigns this array.
  # shellcheck disable=SC2154
  for index in "${!launch_steps[@]}"; do
    if [[ "${launch_steps[$index]}" == "$1" ]] && (( index > step_index )); then
      step_index=$index
      notify "korri-step: $1"
      return 0
    fi
  done
}

# 1. The session lock, for this program's whole life. Children close fd 7, so a
# Wine process that outlives the game cannot hold it. The game unit's cgroup
# goes into the file for the host's pid translation (truncating keeps the lock).
exec 7>>"$channel/session.lock"
flock -w 30 7 || refuse session_busy 126 'Steam engine: another session holds this launch' 'session lock busy'
sed -n 's/^0:://p' /proc/self/cgroup >"$channel/session.lock"

# Events of the host, from byte offset $1 on, one JSON object per line.
events_from() { tail -c +"$(( $1 + 1 ))" "$events" 2>/dev/null || true; }
events_size() { stat -c %s "$events" 2>/dev/null || echo 0; }
send() {
  say "command: $1"
  to_host "$1" 10 ||
    fail 126 'Steam engine: the engine host does not answer' "cannot write '$1' to the host"
}
# A line's string field, for the host's own fixed JSON (no nesting).
field() { jq -r --arg key "$1" '.[$key] // empty' <<<"$2" 2>/dev/null || true; }
# The host's end before the game: its engine states, a refusal of the start
# wrapper or of the host (`launch_refused host_failed`), its stop, or, once it
# has written any event, its host lock free again (a crash, for example in
# steamclient.so, writes nothing). Returns 1 while the host runs.
host_gone() {
  local all line
  all=$(events_from 0)
  if line=$(grep -aE '"event":"(engine_map_missing|engine_mismatch)"' <<<"$all" | tail -n 1) && [[ -n "$line" ]]; then
    fail 126 'Steam engine: this engine build is not available on this device' "$line"
  fi
  if line=$(grep -aF '"event":"engine_refused"' <<<"$all" | tail -n 1) && [[ -n "$line" ]]; then
    fail 126 'Steam engine: Steam refused the pinned engine' "$line"
  fi
  if line=$(grep -aF '"reason":"host_failed"' <<<"$all" | tail -n 1) && [[ -n "$line" ]]; then
    local message
    message=$(field message "$line")
    fail 126 "${message:-Steam engine: the engine host stopped}" "$line"
  fi
  if grep -aqF '"phase":"stopped"' <<<"$all"; then
    fail 126 'Steam engine: the engine host stopped' 'host phase stopped'
  fi
  if [[ -n "$all" ]] && flock -n "$channel/host.lock" true 7>&-; then
    fail 126 'Steam engine: the engine host stopped' 'host lock free: the host is gone'
  fi
  return 1
}

# 2. A signed-in (or offline) engine. Without a saved login korrid shows the
# QR sign-in; this launch waits for it, or korrid stops it on Cancel.
say "waiting for the engine host"
deadline=$((SECONDS + 1800))
until events_from 0 | grep -aqE '"event":"logon_state".*("logged_on":true|"offline":true)'; do
  host_gone || true
  (( SECONDS < deadline )) || refuse signin_timeout 124 'Steam engine: no Steam sign-in' 'no signed-in engine within 1800 s'
  sleep 0.5
done

# 3. Install or update before every launch.
mark=$(events_size)
send "install $appid"
result=""
deadline=$((SECONDS + 4000))
while [[ -z "$result" ]]; do
  while IFS= read -r line; do
    case "$line" in
      *'"event":"app_progress","appid":'"$appid",*) reach_step update ;;
      *'"event":"app_job_finished","appid":'"$appid",*'"kind":"install"'*) result=$(field result "$line") ;;
    esac
  done < <(events_from "$mark")
  [[ -n "$result" ]] && break
  host_gone || true
  (( SECONDS < deadline )) || refuse install_timeout 124 'Steam engine: the game update did not finish' 'install timeout'
  sleep 0.5
done
case "$result" in
  installed|already_installed) ;;
  offline)
    [[ -f "$steam/steamapps/appmanifest_$appid.acf" ]] ||
      refuse not_installed_offline 126 'Steam engine: the game is not installed and Steam is offline' "install result $result" ;;
  *) refuse install_failed 126 'Steam engine: Steam could not install or update the game' "install result $result" ;;
esac

# 4. The launch sync. A Steam Cloud conflict starts no game: korrid turns it
# into a save split and sends `resolve` before the next launch.
reach_step sync
mark=$(events_size)
send "launched $appid"
result=""
deadline=$((SECONDS + 130))  # the host's own limit is 120 s
while [[ -z "$result" ]]; do
  while IFS= read -r line; do
    case "$line" in
      *'"event":"sync_finished","appid":'"$appid",'"kind":"launch"'*) result=$(field result "$line") ;;
    esac
  done < <(events_from "$mark")
  [[ -n "$result" ]] && break
  host_gone || true
  (( SECONDS < deadline )) || { result=timeout; break; }
  sleep 0.5
done
say "launch sync: $result"
if [[ "$result" == conflict ]]; then
  fail 126 'steam-cloud-conflict' "Steam Cloud conflict for AppID $appid"
fi

# 5. The game, from Steam's own launch entry in appinfo.vdf.
reach_step game
installdir=$(sed -n 's/^[[:space:]]*"installdir"[[:space:]]*"\(.*\)"$/\1/p' "$steam/steamapps/appmanifest_$appid.acf" | head -n 1)
# The launch entry of the build that is installed: the installed depots'
# platform first (a Linux depot runs natively, a Windows one through Proton),
# and only an entry whose executable is on disk. Never start a missing file.
# A Windows entry's paths match the files case-insensitively, as on Windows
# (appinfo names vvvvvv.exe, the depot ships VVVVVV.exe); a Linux entry's
# match exactly. Either resolves only inside the install folder.
manifest="$steam/steamapps/appmanifest_$appid.acf"
order=$(python3 @launchEntry@ "$steam/appcache/appinfo.vdf" "$appid" --platforms "$manifest" 2>/dev/null) ||
  order="windows linux"
# $1: the folder; $2: the path in it; $3: file or dir; $4: the entry's OS.
resolve() {
  local fold=()
  [[ "$4" == windows ]] && fold=(--fold)
  python3 @launchEntry@ --resolve "$1" "$2" "$3" "${fold[@]}" 2>/dev/null
}
os="" entry="" install="" exe=""
for candidate in $order; do
  found=$(python3 @launchEntry@ "$steam/appcache/appinfo.vdf" "$appid" --os "$candidate" 2>/dev/null) || continue
  EXE="" INSTALLDIR=""
  eval "$found"
  # Steam names the folder from the manifest's installdir; it is one folder in common.
  folder=${installdir:-$INSTALLDIR}
  [[ -n "$EXE" && -n "$folder" && "$folder" != */* ]] || continue
  install=$(resolve "$steam/steamapps/common" "$folder" dir linux) || continue
  if exe=$(resolve "$install" "$EXE" file "$candidate"); then
    os=$candidate entry=$found
    break
  fi
done
[[ -n "$entry" ]] ||
  refuse no_launch_entry 126 'Steam engine: Steam has no launch entry for this game' "no launch entry for the installed build of $appid (tried: $order)"
EXE="" WORKDIR="" INSTALLDIR="" ARGV=()
eval "$entry"

account=""
[[ -f "$home/.korri-steam-account" ]] && account=$(head -c 64 "$home/.korri-steam-account")
export HOME="$home"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$steam"
export STEAM_COMPAT_DATA_PATH="$steam/steamapps/compatdata/$appid"
export STEAM_COMPAT_INSTALL_PATH="$install"
export STEAM_COMPAT_LIBRARY_PATHS="$steam/steamapps"
export STEAM_COMPAT_TOOL_PATHS="$KORRI_PROTON_CACHYOS"
export STEAM_COMPAT_SHADER_PATH="$steam/steamapps/shadercache/$appid"
export STEAM_COMPAT_APP_ID="$appid" STEAM_COMPAT_PROTON=1 STEAM_COMPAT_FLAGS=search-cwd
export SteamAppId="$appid" SteamGameId="$appid" SteamOverlayGameId="$appid"
export SteamEnv=1 SteamClientLaunch=1
[[ -n "$account" ]] && export SteamUser="$account" SteamAppUser="$account"
# The engine's IPC endpoint (spike FINDINGS section 3: Steam3Master, default port).
export Steam3Master=127.0.0.1:57343
export MESA_SHADER_CACHE_DIR="$STEAM_COMPAT_SHADER_PATH"
export LD_LIBRARY_PATH="$install:$steam/linuxarm64"
if [[ -n "${KORRI_FEX_ROOTFS:-}" ]]; then
  export FEX_ROOTFS="$KORRI_FEX_ROOTFS" FEX_APP_CONFIG_LOCATION="$KORRI_FEX_CONFIG/"
  export FEX_APP_DATA_LOCATION="$steam/fex-data/"
  mkdir -p "$FEX_APP_DATA_LOCATION"
fi
# Controllers: no Steam Input runs. The game reads Korri Seat's pads directly,
# with the settings the spike's sessions played with (section 9, `ctl-1`).
export PRESSURE_VESSEL_FILESYSTEMS_RW=/dev/input
export SDL_JOYSTICK_DISABLE_UDEV=1 SDL_JOYSTICK_HIDAPI_STEAMXBOX=0
unset SteamVirtualGamepadInfo_Proton EnableConfiguratorSupport \
  SDL_GAMECONTROLLER_ALLOW_STEAM_VIRTUAL_GAMEPAD SDL_GAMECONTROLLER_IGNORE_DEVICES LD_PRELOAD
export LIBGL_DRIVERS_PATH=/run/opengl-driver/lib/dri
export __EGL_VENDOR_LIBRARY_DIRS=/run/opengl-driver/share/glvnd/egl_vendor.d
export LIBVA_DRIVERS_PATH=/run/opengl-driver/lib/dri
export GTK_IM_MODULE=xim
mkdir -p "$STEAM_COMPAT_DATA_PATH" "$STEAM_COMPAT_SHADER_PATH"

# Valve's legacycompat folder, from korrid's legacycompat artifact (korri#589).
# Proton copies its steamclient.dll and steamclient64.dll from
# $STEAM_COMPAT_CLIENT_INSTALL_PATH/legacycompat into the prefix, where the
# game's steam_api loads them. Proton's ntdll points their exports at
# lsteamclient, which loads $HOME/.steam/sdkarm64/steamclient.so, the engine.
# Without the folder, steam_api finds no steamclient.dll and the game cannot
# start the Steam API. Only a link of this program's is ever replaced.
legacycompat="$KORRI_STEAM_LEGACYCOMPAT/legacycompat"
[[ -f "$legacycompat/steamclient.dll" && -f "$legacycompat/steamclient64.dll" ]] ||
  fail 126 'Steam engine: the Steam client files are missing' "no steamclient DLLs in $legacycompat"
if [[ -L "$steam/legacycompat" || ! -e "$steam/legacycompat" ]]; then
  ln -sfnT "$legacycompat" "$steam/legacycompat" ||
    fail 126 'Steam engine: the Steam client files are missing' "cannot link $steam/legacycompat"
else
  fail 126 'Steam engine: the Steam client files are missing' "$steam/legacycompat is not a link"
fi

# A 1x1 X window that keeps gamescope's toplevel mapped for the whole session.
# Without it gamescope 3.16.31 can ack a configure that sway dropped and abort
# (xdg_wm_base error 4) when the first Wine windows map and vanish at once
# (spike FINDINGS section 9: 7 of 17 launches aborted before, 0 of 29 after).
placeholder=""
if [[ -n "${DISPLAY:-}" ]]; then
  "$fhs" python3 @placeholder@ 7>&- &
  placeholder=$!
fi

if [[ -n "$WORKDIR" ]]; then
  cwd=$(resolve "$install" "$WORKDIR" dir "$os") ||
    refuse game_files_missing 126 'Steam engine: the game files are missing' "no working folder $WORKDIR in $install"
else
  cwd=$(dirname "$exe")
fi
cd "$cwd" || refuse game_files_missing 126 'Steam engine: the game files are missing' "cannot enter $cwd"
say "AppID $appid: $os entry, $EXE as $exe"
if [[ "$os" == windows ]]; then
  "$fhs" python3 "$KORRI_PROTON_CACHYOS/proton" waitforexitandrun "$exe" "${ARGV[@]}" 7>&- &
else
  "$fhs" "$exe" "${ARGV[@]}" 7>&- &
fi
game=$!

finish() {
  # Every process started for this app carries its SteamAppId.
  local environ pid
  for environ in /proc/[0-9]*/environ; do
    pid=${environ#/proc/}; pid=${pid%/environ}
    [[ "$pid" != "$$" && "$pid" != "$BASHPID" ]] || continue
    if grep -azqxF "SteamAppId=$appid" "$environ" 2>/dev/null; then kill -KILL "$pid" 2>/dev/null || true; fi
  done
  [[ -z "$placeholder" ]] || kill "$placeholder" 2>/dev/null || true
  # The host runs the exit sync. Wait until it has the command, so it does not
  # also take the freed session lock as an end without `exited`.
  local mark
  mark=$(events_size)
  to_host "exited $appid" 10 || say 'cannot send exited'
  for _ in $(seq 1 20); do
    events_from "$mark" | grep -aqF "\"command\":\"exited\",\"appid\":$appid," && break
    sleep 0.5
  done
}
trap 'trap - TERM INT; say "stop requested"; finish; exit 143' TERM INT
status=0
wait "$game" || status=$?
trap - TERM INT
say "AppID $appid exited (status $status)"
finish
exit 0

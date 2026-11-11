#!/usr/bin/env bash
# Run by korrid as the exact game's runtime user, in the same sandbox.
set -euo pipefail
query=false
width=0
height=0
if [[ $# == 1 && $1 == --query ]]; then
  query=true
else
  if [[ $# != 2 || ! $1 =~ ^[0-9]+$ || ! $2 =~ ^[0-9]+$ || ${#1} -gt 5 || ${#2} -gt 5 ]]; then
    echo 'gamescope display change requires width and height' >&2
    exit 2
  fi
  width=$((10#$1))
  height=$((10#$2))
  # New capture targets are aligned by korrid. A rollback must also accept
  # the nested X11 output's exact previous dimensions.
  if (( width < 1 || height < 1 || width > 65535 || height > 65535 )); then
    echo 'gamescope display change has invalid dimensions' >&2
    exit 2
  fi
fi
: "${KORRI_GAME_PIDS:?exact game process identities are required}"
: "${KORRI_GAME_CGROUP:?exact game cgroup is required}"
# Gamescope supplies these variables to its children (upstream main.cpp).
# Never scan unrelated processes or use the outer compositor DISPLAY.
nested_display=''
nested_auth=''
for pid in $KORRI_GAME_PIDS; do
  [[ $pid =~ ^[1-9][0-9]*$ ]] || exit 2
  process_display=''
  process_auth=''
  gamescope_display=''
  [[ -r /proc/$pid/environ && -r /proc/$pid/cgroup ]] || continue
  member=false
  while IFS= read -r group; do
    [[ $group == "0::$KORRI_GAME_CGROUP" ]] && member=true
  done < "/proc/$pid/cgroup"
  [[ $member == true ]] || continue
  while IFS= read -r -d '' entry; do
    case "$entry" in
      DISPLAY=*) process_display=${entry#DISPLAY=} ;;
      XAUTHORITY=*) process_auth=${entry#XAUTHORITY=} ;;
      GAMESCOPE_WAYLAND_DISPLAY=*) gamescope_display=${entry#GAMESCOPE_WAYLAND_DISPLAY=} ;;
    esac
  done < "/proc/$pid/environ"
  [[ -n $gamescope_display && -n $process_display ]] || continue
  if [[ -n $nested_display && ( $nested_display != "$process_display" || $nested_auth != "$process_auth" ) ]]; then
    echo 'gamescope display identity is ambiguous' >&2
    exit 1
  fi
  nested_display=$process_display
  nested_auth=$process_auth
done
[[ -n $nested_display ]] || { echo 'gamescope display identity is unavailable' >&2; exit 1; }
export DISPLAY=$nested_display
unset XAUTHORITY
if [[ -n $nested_auth ]]; then export XAUTHORITY=$nested_auth; fi
actual_width=''
actual_height=''
observe() {
  local geometry key value rest
  geometry=$(timeout 0.1 xwininfo -root) || return 1
  actual_width=''
  actual_height=''
  while read -r key value rest; do
    case "$key" in
      Width:) actual_width=$value ;;
      Height:) actual_height=$value ;;
    esac
  done <<< "$geometry"
  [[ $actual_width =~ ^[1-9][0-9]*$ && $actual_height =~ ^[1-9][0-9]*$ ]]
}
if [[ $query == true ]]; then
  observe
  printf '%s %s\n' "$actual_width" "$actual_height"
  exit 0
fi
timeout 0.5 xprop -root -f GAMESCOPE_XWAYLAND_MODE_CONTROL 32c \
  -set GAMESCOPE_XWAYLAND_MODE_CONTROL "0, $width, $height, 1" >/dev/null
for ((attempt = 0; attempt < 20; attempt++)); do
  observe || exit 1
  if [[ $actual_width == "$width" && $actual_height == "$height" ]]; then exit 0; fi
  sleep 0.05
done
echo 'gamescope did not confirm the requested display size' >&2
exit 1

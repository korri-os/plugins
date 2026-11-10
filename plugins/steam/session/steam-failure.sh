# Translate only AppID-scoped Steam diagnostics. Never forward raw log text:
# it can contain executable paths, account IDs and command-line secrets.
steam_failure_reason() {
  local appid="$1" line lower reason="" state=""
  local app_pattern="(^|[^[:alnum:]_])AppID[[:space:]]+$appid([^0-9]|$)"
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ $app_pattern ]] || continue
    lower=${line,,}
    if [[ "$lower" == *'state changed :'* ]]; then
      if [[ "$lower" == *'update required'* ]]; then
        state='Steam: this game needs an update'
      elif [[ "$lower" == *'fully installed'* ]]; then
        state=""
      fi
      continue
    fi
    # Suspended is ordinary scheduler activity, not a failed download. A
    # process exit code is not a launch error either (Wine helpers use -1).
    [[ "$lower" != *'(suspended)'* ]] || continue
    [[ "$lower" == *'launchapp failed'* || "$lower" == *'update canceled :'* ]] || continue
    case "$lower" in
      *'no subscription'*|*'no license'*|*'does not own'*)
        reason='Steam: this game is not owned by the signed-in account' ;;
      *'invalid platform'*|*'missing configuration'*|*'invalid app configuration'*)
        reason='Steam: this game is not available for this device' ;;
      *'missing executable'*) reason='Steam: the game executable is missing' ;;
      *'not enough disk space'*)
        reason='Steam: the game update failed because there is not enough disk space' ;;
      *'disk write failure'*)
        reason='Steam: the game update failed because Steam could not write to disk' ;;
      *'disk read failure'*)
        reason='Steam: the game update failed because Steam could not read from disk' ;;
      *'corrupt update files'*)
        reason='Steam: the game update failed because the downloaded files are corrupt' ;;
      *'content servers unreachable'*)
        reason='Steam: the game update failed because the content servers are unreachable' ;;
      *'no connection'*|*'connection timeout'*)
        reason='Steam: the game update failed because the connection failed' ;;
      *'appupdaterequired'*|*'update required'*) reason='Steam: this game needs an update' ;;
      *'launchapp failed'*) reason='Steam: Steam reported a launch error' ;;
    esac
  done
  printf '%s' "${reason:-$state}"
}

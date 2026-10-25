# Producer assertions for the plugin-owned UHID setup.
# Core checks shared receiver ownership against the actual packaged artifacts.
{
  pkgs,
  plugin,
}:
pkgs.runCommand "korri-sunshine-plugin-native-check"
  {
    nativeBuildInputs = [
      pkgs.gnugrep
      pkgs.jq
      pkgs.systemd
      pkgs.bun
      pkgs.typescript
      pkgs.python3
      pkgs.jq
    ];
  }
  ''
    set -euo pipefail
    setup=${plugin.files.setup}
    rules=${plugin.files.input-rules}
    sunshine_unit=${plugin.services.korri-sunshine}
    setup_unit=${plugin.services.korri-sunshine-input-setup}
    runtime=${plugin.files.runtime}
    apps=${plugin.files.apps}

    # The installed runtime must use the same immutable, command-free app file.
    jq -e '. == {"apps": [{"name": "Korri Stream", "cmd": "", "image-path": ""}], "env": {}}' "$apps"
    grep -F " file_apps=$apps" "$runtime"

    # Every store tool the setup helper calls must exist in its closure.
    tools="$(grep -oE '/nix/store/[a-z0-9]{32}-[^/ ]+/bin/[A-Za-z0-9_.-]+' "$setup" | sort -u)"
    test -n "$tools"
    for tool in $tools; do
      if ! test -x "$tool"; then
        echo "setup helper calls a missing tool: $tool" >&2
        exit 1
      fi
    done

    # Every store tool a rule runs must exist too.
    for tool in $(grep -oE '/nix/store/[a-z0-9]{32}-[^/ ]+/bin/[A-Za-z0-9_.-]+' "$rules" | sort -u); do
      if ! test -x "$tool"; then
        echo "udev rule runs a missing tool: $tool" >&2
        exit 1
      fi
    done

    # The plugin must not own or trigger changes to persistent core seats.
    ! grep -E 'Korri Seat|SUBSYSTEM=="input"' "$rules"
    ! grep -F -- '--subsystem-match=input' "$setup"
    ! grep -E 'RuntimeDirectory=korri-input-seat|korri-bundle-launch' "$setup_unit"
    grep -Fx 'Type=exec' "$setup_unit"
    grep -F 'ExecStartPre=+' "$setup_unit"
    grep -F 'ExecStopPost=+' "$setup_unit"
    grep -E '^ExecStart=/nix/store/[^ ]+/bin/sleep infinity$' "$setup_unit"
    ! grep -E '^ExecStart=\+|^RemainAfterExit=' "$setup_unit"
    grep -E '^Requires=.*korri-sunshine-input-setup.service.*korri-input-seat-receiver.service' "$sunshine_unit"
    ! grep -F 'korri-sunshine-input-seat-receiver.service' "$sunshine_unit"
    grep -Fx 'Environment=KORRI_INPUT_SEAT_MIRROR_SOCKET=/run/korri-input-seat/sunshine-input-seat.sock' "$sunshine_unit"

    # The host owns /dev/uinput (korri-inputd:uinput 0660). A plugin rule that
    # sets its owner, group or mode takes the node from every other holder,
    # and udev's last matching rule decides which plugin loses.
    if grep -qE 'KERNEL=="uinput"' "$rules"; then
      echo "plugin udev rule changes /dev/uinput, which the host owns" >&2
      exit 1
    fi

    # Only Sunshine opens /dev/uinput; the setup unit owns no devices.
    grep -qE '^SupplementaryGroups=(.* )?uinput( |$)' "$sunshine_unit"

    udevadm verify --resolve-names=never --no-style "$rules"
    # ProtectSystem=strict makes /run read-only, not inaccessible. The service
    # needs no write permission or extra mount for korrid's launch arguments.
    grep -Fx 'ProtectSystem=strict' "$sunshine_unit"
    ! grep -E '^(InaccessiblePaths|TemporaryFileSystem)=.*(/run|korri-launch-services)' "$sunshine_unit"
    python3 ${./test-runtime.py} ${./runtime.sh}
    mkdir settings-check
    cp ${./plugin.ts} settings-check/plugin.ts
    cp ${./settings.ts} settings-check/settings.ts
    cp ${./settings.test.mts} settings-check/settings.test.ts
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler settings-check/plugin.ts
    bun test ./settings-check/settings.test.ts
    touch "$out"
  ''

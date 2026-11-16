# Regression proof for korri#443. The packaged Sunshine serves all HTTPS on
# one thread. A peer that receives its answer and Sunshine's close_notify, then
# goes silent without closing, must not stop a second paired client from
# getting serverinfo. Runs the shipped binary in a VM; ARM uses QEMU's software
# engine, like the input-presence proof.
{ pkgs, sunshinePackage }:
let
  stateDirectory = "/var/lib/sunshine-https";
  prepare = pkgs.writeShellApplication {
    name = "prepare-sunshine-https";
    runtimeInputs = [
      pkgs.openssl
      pkgs.jq
    ];
    text = ''
      directory=${stateDirectory}
      mkdir -p "$directory"
      for client in paired silent; do
        openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj "/CN=$client" \
          -keyout "$directory/$client.key" -out "$directory/$client.crt" 2>/dev/null
      done
      # Sunshine's own state file, with both clients already paired.
      jq -n \
        --rawfile paired "$directory/paired.crt" \
        --rawfile silent "$directory/silent.crt" \
        '{root: {uniqueid: "0123456789ABCDEF", named_devices: [
          {name: "paired", uuid: "11111111-1111-1111-1111-111111111111", cert: $paired, enabled: true},
          {name: "silent", uuid: "22222222-2222-2222-2222-222222222222", cert: $silent, enabled: true}
        ]}}' > "$directory/sunshine_state.json"
      cat > "$directory/sunshine.conf" <<EOF
      port = 47989
      file_state = $directory/sunshine_state.json
      credentials_file = $directory/sunshine_credentials.json
      file_apps = $directory/apps.json
      pkey = $directory/sunshine.key
      cert = $directory/sunshine.crt
      log_path = $directory/sunshine.log
      upnp = disabled
      system_tray = disabled
      EOF
      echo '{"env": {}, "apps": []}' > "$directory/apps.json"
    '';
  };
  serverinfo =
    client:
    "curl -sS -k --max-time 5 --cert ${stateDirectory}/${client}.crt "
    + "--key ${stateDirectory}/${client}.key 'https://127.0.0.1:47984/serverinfo?uniqueid=0123456789ABCDEF'";
  vm = pkgs.testers.runNixOSTest {
    name = "sunshine-https-silent-peer";
    nodes.machine = {
      environment.systemPackages = [
        sunshinePackage
        prepare
        pkgs.curl
        pkgs.python3
      ];
      virtualisation.memorySize = 2048;
      virtualisation.qemu.options = pkgs.lib.optionals (
        pkgs.stdenv.hostPlatform.system == "aarch64-linux"
      ) [ "-machine accel=tcg" ];
    };
    testScript = ''
      machine.start()
      machine.wait_for_unit("multi-user.target")
      machine.succeed("prepare-sunshine-https")
      machine.succeed(
          "systemd-run --unit=sunshine --setenv=HOME=${stateDirectory} "
          "${sunshinePackage}/bin/sunshine ${stateDirectory}/sunshine.conf"
      )
      machine.wait_until_succeeds(
          """${serverinfo "paired"} | grep -F '<PairStatus>1</PairStatus>'""",
          timeout=180,
      )

      machine.succeed(
          "systemd-run --unit=silent-peer python3 ${./test-https-silent-peer.py} "
          "127.0.0.1 47984 ${stateDirectory}/silent.crt ${stateDirectory}/silent.key "
          "/run/silent-peer-ready 600"
      )
      machine.wait_for_file("/run/silent-peer-ready", timeout=60)
      machine.succeed("systemctl is-active silent-peer.service")

      # The silent peer still holds its connection. A second paired client
      # must get serverinfo while it does.
      with subtest("a second client gets serverinfo while a peer is silent"):
          status, output = machine.execute("""${serverinfo "paired"}""", timeout=30)
          if status != 0 or "<PairStatus>1</PairStatus>" not in output:
              machine.execute("tail -n 40 ${stateDirectory}/sunshine.log >&2")
              raise Exception(
                  f"serverinfo failed while a peer was silent (curl exit {status}): {output!r}"
              )
          machine.succeed("systemctl is-active silent-peer.service")
    '';
  };
in
{
  inherit prepare;
  vm =
    if pkgs.stdenv.hostPlatform.system == "aarch64-linux" then
      vm.overrideTestDerivation (original: {
        requiredSystemFeatures = pkgs.lib.filter (
          feature: feature != "kvm"
        ) original.requiredSystemFeatures;
      })
    else
      vm;
}

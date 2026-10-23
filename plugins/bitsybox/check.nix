{
  pkgs,
  package,
  contract,
  hostPackage,
  korridPackage,
}:
let
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
  recordArguments = pkgs.writeShellScript "record-bitsybox-launch" ''
    printf '%s\0' "$@" "$PWD"
  '';
in
pkgs.runCommand "korri-bitsybox-plugin-check"
  {
    nativeBuildInputs = [
      pkgs.bun
      pkgs.typescript
      pkgs.python3
      pkgs.xvfb-run
      pkgs.xdotool
    ];
  }
  ''
    mkdir -p work/plugins/bitsybox work/contracts/generated
    cp ${package}/plugin.ts work/plugins/bitsybox/plugin.ts
    cp ${contractSource} work/contracts/generated/korrid.ts
    cp ${./launch.test.ts} work/plugins/bitsybox/launch.test.ts
    cd work
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler plugins/bitsybox/plugin.ts
    bun plugins/bitsybox/launch.test.ts ${package} \
      ${hostPackage}/bin/korri-plugin ${korridPackage}/bin/korrid ${recordArguments}
    xvfb-run -a python3 ${./runtime.test.py} ${package} ${pkgs.stdenv.hostPlatform.system} \
      ${korridPackage}/bin/korrid ${./fixture.bitsy}
    touch "$out"
  ''

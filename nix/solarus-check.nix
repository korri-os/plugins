{
  pkgs,
  package,
  solarusPackage,
  contract,
  hostPackage,
  korridPackage,
}:
let
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
  recordArguments = pkgs.writeShellScript "record-solarus-launch" ''
    printf '%s\0' "$@" "$HOME" "$PWD"
  '';
  headless = pkgs.writeShellScript "solarus-headless-test" ''
    exec ${solarusPackage}/bin/solarus-run -no-video -no-audio "$@"
  '';
in
pkgs.runCommand "korri-solarus-plugin-check"
  {
    nativeBuildInputs = [
      pkgs.bun
      pkgs.typescript
      pkgs.python3
    ];
  }
  ''
    mkdir -p work/plugins/solarus work/contracts/generated work/nix
    cp ${package}/plugin.ts work/plugins/solarus/plugin.ts
    cp ${contractSource} work/contracts/generated/korrid.ts
    cp ${./solarus-check.ts} work/nix/solarus-check.ts
    cd work
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler plugins/solarus/plugin.ts
    bun nix/solarus-check.ts ${package} \
      ${hostPackage}/bin/korri-plugin ${korridPackage}/bin/korrid ${recordArguments}
    python3 ${./solarus-controller-check.py} ${pkgs.SDL2}/lib/libSDL2.so \
      ${solarusPackage.lib}/share/solarus/gamecontrollerdb.txt
    python3 ${./solarus-runtime-check.py} ${package} ${pkgs.stdenv.hostPlatform.system} \
      ${korridPackage}/bin/korrid ${headless} ${./solarus-quest}
    touch "$out"
  ''

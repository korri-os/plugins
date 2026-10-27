# The kind checks the caller's program, not a default RetroArch source. Source
# unpack/patch hooks are inherited from that exact derivation. The native cfg
# parser is compiled and executed on the build machine, never on the target.
# Plugin TS is evaluated for tests only; installed plugin code stays source.
{ pkgs, program }:
program.overrideAttrs (old: {
  pname = "retroarch-source-checked-settings";
  outputs = [ "out" ];
  nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [
    pkgs.buildPackages.python3
    pkgs.buildPackages.bun
  ];
  phases = [
    "unpackPhase"
    "patchPhase"
    "installPhase"
  ];
  installPhase = ''
    # The host names a file as a path inside a store output. Making $out the
    # file itself produced a bare output the device refused at inspection.
    mkdir -p "$out"
    CC=${pkgs.buildPackages.stdenv.cc}/bin/cc bash ${./build-config-parser.sh} \
      "$PWD" ${./config-parser-probe.c} "$PWD/config-parser-probe"
    cp ${./check-settings.py} check-settings.py
    cp ${./test_check_settings.py} test_check_settings.py
    python3 test_check_settings.py
    python3 ${./check-settings.py} \
      --configuration configuration.c \
      --table ${./settings-types.json} \
      --callback ${../libretro/retroarch.ts} \
      --program ${pkgs.lib.escapeShellArg "${program}/bin/retroarch"} \
      --version ${pkgs.lib.escapeShellArg program.version} \
      --output "$out/settings.json" \
      --module "$out/settings.ts"
    # The nested schema stays in policy.ts; settings.ts is this frontend's
    # source evidence. Bind the producer's layout ids in the test wrapper.
    cp ${./policy.ts} policy.ts
    cp ${./render-settings.ts} render-settings.ts
    cp ${../libretro/retroarch.ts} retroarch.ts
    # Use the producer's declaration, never a second accepted-layout list.
    cat > plugin.ts <<'EOF'
    import { createHandlers } from "./retroarch"
    export const handlers = createHandlers({
      melonds: {
        id: "@korri:melonds/melonds",
        layouts: ${builtins.toJSON (import ../libretro/cores.nix { inherit pkgs; }).melonds.layouts},
      },
    })
    EOF

    cp "$out/settings.ts" settings.ts
    cp ${./plugin.sandbox-test.ts} plugin.test.ts
    KORRI_TEST_RETROARCH_CONFIG_PARSER="$PWD/config-parser-probe" bun test ./plugin.test.ts
  '';
})

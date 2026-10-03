{
  pkgs,
  solarusPackage,
  cartridges,
}:
# Normal Nix build sandbox, no display/audio device or real account data.
pkgs.runCommand "korri-starter-pack-solarus-startup" { } ''
  ${pkgs.python3}/bin/python ${./solarus-starter-runtime-check.py} \
    ${solarusPackage}/bin/solarus-run ${cartridges}/share/starter-pack
  touch "$out"
''

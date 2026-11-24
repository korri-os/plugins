# Core's declaration evaluator is the source of truth for the tool name. The
# packages read it during evaluation (../cachyos/tool-name.nix); this check
# proves both reads agree, before and after a declaration version change, and
# that the change reaches every consumer. Only this check needs Core's host
# build; plugin packages do not.
{
  pkgs,
  evaluator,
  protonToolName,
}:
let
  inherit (pkgs.stdenv.hostPlatform) system;
  current =
    {
      aarch64-linux = "11.0-20260601-slr-arm64";
      x86_64-linux = "11.0-20260601-slr-x86_64";
    }
    .${system};
  changed = "${current}-regression";
  source = builtins.readFile ../plugin.ts;
  # builtins.toFile, not a derivation: tool-name.nix reads the file during
  # evaluation, and the publisher refuses import from derivation.
  changedSource = builtins.toFile "proton-version-change.plugin.ts" (
    pkgs.lib.replaceStrings [ ''version: "${current}"'' ] [ ''version: "${changed}"'' ] source
  );
  changedToolName = import ../cachyos/tool-name.nix {
    inherit (pkgs) lib system;
    source = changedSource;
  };
  declared =
    name: declarationSource:
    pkgs.runCommand name { nativeBuildInputs = [ pkgs.jq ]; } ''
      mkdir source
      cp ${declarationSource} source/plugin.ts
      ${evaluator}/bin/korri-publish declaration @korri "$PWD/source" plugin.ts > declaration.json
      jq -er --arg system ${system} '
        select(.name == "proton" and .artifacts.cachyos.id == "@korri:proton/cachyos") |
        .artifacts.cachyos.platforms[$system].version |
        select(type == "string" and test("^[A-Za-z0-9][A-Za-z0-9._+-]*$")) |
        "proton-cachyos-" + .
      ' declaration.json > "$out"
    '';
  consumers = toolName: {
    proton = import ../plugin.nix {
      inherit pkgs;
      protonToolName = toolName;
    };
  };
  original = consumers protonToolName;
  modified = consumers changedToolName;
in
assert pkgs.lib.hasInfix ''version: "${current}"'' source;
assert protonToolName == "proton-cachyos-${current}";
assert changedToolName == "proton-cachyos-${changed}";
pkgs.runCommand "proton-tool-name-check" { nativeBuildInputs = [ pkgs.python3 ]; } ''
  python3 - ${declared "proton-cachyos-tool-name" ../plugin.ts} ${original.proton.files.cachyos-unpack} \
    ${declared "proton-cachyos-tool-name-changed" changedSource} ${modified.proton.files.cachyos-unpack} \
    ${../../steam/session/vdf-settings.py} ${../../steam/session/steam-session.sh} ${../../steam/engine/host-run.sh} <<'PY'
  from pathlib import Path
  import os
  import re
  import subprocess
  import sys
  import tempfile

  settings = Path(sys.argv[5])
  for offset, expected in ((1, '${protonToolName}'), (3, '${changedToolName}')):
      metadata, unpack = map(Path, sys.argv[offset:offset + 2])
      # Core's evaluator derives the same name the packages read.
      assert metadata.read_text().strip() == expected, (metadata.read_text(), expected)
      vdfs = re.findall(r'/nix/store/[^" ]+/compatibilitytool[.]vdf', unpack.read_text())
      assert len(vdfs) == 1, vdfs
      assert f'"{expected}"' in Path(vdfs[0]).read_text()
      assert '@toolName@' not in Path(vdfs[0]).read_text()
      # Steam fixes no Proton version (Core ADR 0083): its programs read the
      # name from that file at launch, and the settings program maps to it.
      with tempfile.TemporaryDirectory() as home:
          config = Path(home) / 'config/config.vdf'
          config.parent.mkdir()
          config.write_bytes(Path('${../../steam/session/fixtures/config.vdf}').read_bytes())
          subprocess.run(['python3', str(settings), home, '401710'], check=True,
                         env={**os.environ, 'KORRI_STEAM_COMPAT_TOOL': expected})
          content = config.read_text()
          assert content.count(f'"{expected}"') == 2
          assert '"999" { "name" "other-proton" }' in content
  for program in sys.argv[5:8]:
      text = Path(program).read_text()
      assert '@protonToolName@' not in text, program
      assert 'proton-cachyos-' not in text, program
  PY
  touch "$out"
''

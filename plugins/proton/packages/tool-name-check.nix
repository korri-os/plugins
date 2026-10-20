{
  pkgs,
  evaluator,
  protonToolName,
}:
let
  current = "11.0-20260601-slr-arm64";
  changed = "${current}-regression";
  source = builtins.readFile ../plugin.ts;
  changedSource = pkgs.writeText "proton-version-change.plugin.ts" (
    pkgs.lib.replaceStrings [ ''version: "${current}"'' ] [ ''version: "${changed}"'' ] source
  );
  changedToolName = import ../cachyos/tool-name.nix {
    inherit pkgs evaluator;
    source = changedSource;
  };
  consumers = toolName: {
    proton = import ../plugin.nix {
      inherit pkgs;
      protonToolName = toolName;
    };
    steam = import ../../steam/packages {
      inherit pkgs;
      protonToolName = toolName;
    };
  };
  original = consumers protonToolName;
  modified = consumers changedToolName;
in
assert pkgs.lib.hasInfix ''version: "${current}"'' source;
pkgs.runCommand "proton-tool-name-check" { nativeBuildInputs = [ pkgs.python3 ]; } ''
  python3 - ${protonToolName} ${original.proton.files.cachyos-unpack} \
    ${original.steam.sessionRun}/bin/steam-session-run ${original.steam.settingsSource} \
    ${changedToolName} ${modified.proton.files.cachyos-unpack} \
    ${modified.steam.sessionRun}/bin/steam-session-run ${modified.steam.settingsSource} <<'PY'
  from pathlib import Path
  import re
  import subprocess
  import sys
  import tempfile

  old = 'proton-cachyos-${current}'
  new = 'proton-cachyos-${changed}'
  for offset, expected in ((1, old), (5, new)):
      metadata, unpack, session, settings = map(Path, sys.argv[offset:offset + 4])
      assert metadata.read_text().strip() == expected
      vdfs = re.findall(r'/nix/store/[^" ]+/compatibilitytool[.]vdf', unpack.read_text())
      assert len(vdfs) == 1, vdfs
      assert f'"{expected}"' in Path(vdfs[0]).read_text()
      assert f'compatibilitytools.d/{expected}' in session.read_text()
      assert f'TOOL = "{expected}"' in settings.read_text()
      for path in (Path(vdfs[0]), session, settings):
          assert '@protonToolName@' not in path.read_text()
      with tempfile.TemporaryDirectory() as home:
          config = Path(home) / 'config/config.vdf'
          config.parent.mkdir()
          config.write_bytes(Path('${../../steam/session/fixtures/config.vdf}').read_bytes())
          subprocess.run(['python3', str(settings), home, '401710'], check=True)
          content = config.read_text()
          assert content.count(f'"{expected}"') == 2
          assert '"999" { "name" "other-proton" }' in content
  PY
  touch "$out"
''

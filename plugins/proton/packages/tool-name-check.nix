# The tool name is written by hand in cachyos/tool-name.nix and must embed the
# artifact version plugin.ts pins. This test reads both as text; it runs no
# Core host, so plugin builds stay host-free. It also checks that every
# consumer (the vdf cachyos-unpack installs, the Steam session and the VDF
# settings helper) carries exactly that name.
{ pkgs }:
let
  cachyos = import ../cachyos/tool-name.nix;
  proton = import ../plugin.nix { inherit pkgs; };
  steam = import ../../steam/packages { inherit pkgs; };
in
pkgs.runCommand "proton-tool-name-check" { nativeBuildInputs = [ pkgs.python3 ]; } ''
  python3 - ${cachyos.toolName} ${../plugin.ts} ${proton.files.cachyos-unpack} \
    ${steam.sessionRun}/bin/steam-session-run ${steam.settingsSource} <<'PY'
  from pathlib import Path
  import re
  import subprocess
  import sys
  import tempfile

  tool = sys.argv[1]
  source, unpack, session, settings = map(Path, sys.argv[2:6])
  # The cachyos artifact's own version, not the first version string in the file.
  match = re.search(r'id:\s*"@korri:proton/cachyos",\s*(?://[^\n]*\n\s*)*version:\s*"([^"]+)"',
                    source.read_text())
  assert match, 'plugin.ts declares no version for @korri:proton/cachyos'
  assert tool == 'proton-cachyos-' + match.group(1), (tool, match.group(1))
  vdfs = re.findall(r'/nix/store/[^" ]+/compatibilitytool[.]vdf', unpack.read_text())
  assert len(vdfs) == 1, vdfs
  assert f'"{tool}"' in Path(vdfs[0]).read_text()
  assert f'compatibilitytools.d/{tool}' in session.read_text()
  assert f'TOOL = "{tool}"' in settings.read_text()
  for path in (Path(vdfs[0]), session, settings):
      assert '@protonToolName@' not in path.read_text()
  with tempfile.TemporaryDirectory() as home:
      config = Path(home) / 'config/config.vdf'
      config.parent.mkdir()
      config.write_bytes(Path('${../../steam/session/fixtures/config.vdf}').read_bytes())
      subprocess.run(['python3', str(settings), home, '401710'], check=True)
      content = config.read_text()
      assert content.count(f'"{tool}"') == 2
      assert '"999" { "name" "other-proton" }' in content
  PY
  touch "$out"
''

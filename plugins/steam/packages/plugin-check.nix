{
  pkgs,
  plugin,
  fexPlugin,
  protonPlugin,
}:
pkgs.runCommand "steam-plugin-package-check"
  {
    nativeBuildInputs = [ pkgs.python3 ];
  }
  ''
    python3 - ${plugin} ${fexPlugin} ${protonPlugin} ${
      if pkgs.stdenv.hostPlatform.isAarch64 then "arm" else "x86"
    } <<'PY'
    import json
    from pathlib import Path
    import subprocess
    import sys
    import tempfile

    package, fex, proton = map(Path, sys.argv[1:4])
    arm = sys.argv[4] == 'arm'
    manifest = json.loads((package / 'manifest.json').read_text())
    assert manifest['publisher'] == {'namespace': '@korri'}
    assert manifest['sources'] == ['plugin.ts']
    assert manifest['services'] == {}
    # Exact outputs of the plugins whose files plugin.ts passes to the session.
    assert manifest['requires'] == [str(fex), str(proton)], manifest['requires']
    for required, keys in ((fex, ['config', 'fex-unpack']), (proton, ['cachyos-unpack'])):
        files = json.loads((required / 'manifest.json').read_text())['files']
        assert sorted(files) == keys, files
    runner = manifest['files']['steam-session']
    assert Path(runner).is_file()
    assert subprocess.run([runner], capture_output=True).returncode == 2
    assert subprocess.run([runner, '401710;false'], capture_output=True).returncode == 2
    result = subprocess.run([runner, '401710'], env={}, capture_output=True)
    assert result.returncode == 2, result.stderr
    assert b'STEAM_HOME' in result.stderr
    home = tempfile.mkdtemp()
    result = subprocess.run([runner, '401710'], env={'STEAM_HOME': home, 'HOME': home},
                            capture_output=True)
    assert result.returncode == 2, result.stderr
    if arm:
        assert b'KORRI_FEX_CONFIG must be an absolute path' in result.stderr, result.stderr
        fex_files = json.loads((fex / 'manifest.json').read_text())['files']
        runtime = {
            'STEAM_HOME': home, 'HOME': home,
            'KORRI_FEX_CONFIG': fex_files['config'],
            'KORRI_FEX_ROOTFS': '/nonexistent/fex/rootfs/archlinux-2026-01-08-mesa-26.1.2',
            'KORRI_PROTON_CACHYOS': home,
        }
        result = subprocess.run([runner, '401710'], env=runtime, capture_output=True)
        assert result.returncode == 2, result.stderr
        assert b'KORRI_FEX_ROOTFS is not a directory' in result.stderr, result.stderr
    else:
        # x86_64 needs only Proton: no FEX path is checked.
        assert b'KORRI_PROTON_CACHYOS must be an absolute path' in result.stderr, result.stderr
        assert b'FEX' not in result.stderr, result.stderr
        result = subprocess.run(
            [runner, '401710'],
            env={'STEAM_HOME': home, 'HOME': home, 'KORRI_PROTON_CACHYOS': '/nonexistent/proton'},
            capture_output=True,
        )
        assert result.returncode == 2, result.stderr
        assert b'KORRI_PROTON_CACHYOS is not a directory' in result.stderr, result.stderr
    PY
    touch "$out"
  ''

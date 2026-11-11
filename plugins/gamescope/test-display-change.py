#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 bash coreutils
"""Exercise the hook as a subprocess with bounded X command responses."""
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest

HOOK = Path(__file__).with_name('display-change.sh')


class DisplayChangeTests(unittest.TestCase):
    def run_hook(self, dimensions, geometry='2448 1848', refusal=False, display=':7'):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            shell = shutil.which('bash')
            assert shell is not None
            (root / 'xprop').write_text(
                f'#!{shell}\n'
                'printf "%s\\n" "$@" > "$CAPTURE"\n'
                + ('exit 1\n' if refusal else 'exit 0\n'))
            width, height = geometry.split()
            (root / 'xwininfo').write_text(
                f'#!{shell}\n'
                f'printf "  Width: {width}\\n  Height: {height}\\n"\n')
            for name in ('xprop', 'xwininfo'):
                (root / name).chmod(0o700)
            env = dict(os.environ, PATH=f'{root}:{os.environ["PATH"]}',
                       CAPTURE=str(root / 'args'))
            if display is None:
                env.pop('DISPLAY', None)
            else:
                env['DISPLAY'] = display
            child_env = dict(env, GAMESCOPE_WAYLAND_DISPLAY='gamescope-test')
            child = subprocess.Popen(['sleep', '60'], env=child_env)
            try:
                env['KORRI_GAME_PIDS'] = str(child.pid)
                env['KORRI_GAME_CGROUP'] = Path(f'/proc/{child.pid}/cgroup').read_text().strip().removeprefix('0::')
                result = subprocess.run(['bash', str(HOOK), *dimensions], env=env,
                                        capture_output=True, text=True, timeout=30)
                args = (root / 'args').read_text() if (root / 'args').exists() else None
                return result, args
            finally:
                child.terminate()
                child.wait(timeout=5)

    def test_query_observes_hook_geometry_without_changing_it(self):
        result, args = self.run_hook(['--query'], geometry='1280 720')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '1280 720\n')
        self.assertIsNone(args)

    def test_sets_exact_mode_and_confirms_geometry(self):
        result, args = self.run_hook(['2448', '1848'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(args.splitlines(), [
            '-root', '-f', 'GAMESCOPE_XWAYLAND_MODE_CONTROL', '32c',
            '-set', 'GAMESCOPE_XWAYLAND_MODE_CONTROL', '0, 2448, 1848, 1'])

    def test_restores_unaligned_nested_output(self):
        result, _ = self.run_hook(['1281', '721'], geometry='1281 721')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_dimensions_never_write_a_property(self):
        for args in (['0', '1080'], ['65536', '1080'], ['-1', '1080'],
                     ['2448;id', '1848'], ['2448'], ['00000008', '1080']):
            with self.subTest(args=args):
                result, captured = self.run_hook(args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(captured)

    def test_absent_exact_display_does_not_fall_back_to_outer_display(self):
        result, args = self.run_hook(['2448', '1848'], display=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(args)

    def test_property_refusal_fails(self):
        result, _ = self.run_hook(['2448', '1848'], refusal=True)
        self.assertNotEqual(result.returncode, 0)

    def test_acceptance_without_geometry_change_is_not_success(self):
        result, _ = self.run_hook(['2448', '1848'], geometry='1920 1080')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('did not confirm', result.stderr)


if __name__ == '__main__':
    unittest.main()

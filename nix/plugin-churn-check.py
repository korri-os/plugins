#!/usr/bin/env nix
#! nix shell nixpkgs#python3 nixpkgs#nix --command python3
"""Evaluate real publisher outputs under scoped source changes. No builds or writes to inputs."""
import argparse
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


def copy_source(source, destination):
    shutil.copytree(
        source,
        destination,
        copy_function=shutil.copy,
        symlinks=True,
        ignore=shutil.ignore_patterns('.git', '.worktree', '.worktrees', '__pycache__'),
    )
    # Nix sources have read-only directory permissions.
    for directory in [destination, *destination.rglob('*')]:
        if directory.is_dir() and not directory.is_symlink():
            directory.chmod(0o755)


def source_hash(path):
    return subprocess.check_output(['nix', 'hash', 'path', str(path)], text=True).strip()


def append(path, text):
    path.chmod(0o644)
    with path.open('a') as handle:
        handle.write(text)


def evaluate(publisher, korri, system, selection):
    command = [
        'nix', 'eval', '--json', '--impure', '--no-write-lock-file',
        '--option', 'eval-cache', 'false',
        '--option', 'allow-import-from-derivation', 'false',
        '--override-input', 'korri', f'path:{korri}',
    ]
    identity = 'package: { output = toString package; derivation = package.drvPath; }'
    packages = subprocess.run(
        command + [f'path:{publisher}#packages.{system}', '--apply', f'''p:
          let names = (import {json.dumps(str(selection))} {{
            plugins = builtins.mapAttrs (name: _: name) p;
          }}).rpminiv2;
          in builtins.listToAttrs (map (name: {{
            inherit name; value = ({identity}) p.${{name}};
          }}) names)'''],
        text=True, capture_output=True, check=True,
    )
    checks = subprocess.run(
        command + [f'path:{publisher}#checks.{system}', '--apply', f'''c:
          builtins.mapAttrs (name: {identity}) {{
            inherit (c) korri-libretro-typecheck korri-plugin-host korri-retroarch-settings;
          }}'''],
        text=True, capture_output=True, check=True,
    )
    return {'packages': json.loads(packages.stdout), 'checks': json.loads(checks.stdout)}


def changed(before, after):
    if before.keys() != after.keys():
        raise AssertionError('The Mini V2 selection changed during the regression check')
    return {name for name in before if before[name] != after[name]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publisher', required=True, type=Path)
    parser.add_argument('--korri', required=True, type=Path, help='Clean Core flake source snapshot')
    parser.add_argument('--system', action='append', choices=['x86_64-linux', 'aarch64-linux'])
    parser.add_argument('--report', type=Path, help='Write measured evaluation results')
    args = parser.parse_args()
    publisher, korri = args.publisher.resolve(), args.korri.resolve()
    selection = korri / 'nix/product/plugin-selection.nix'
    systems = args.system or ['x86_64-linux', 'aarch64-linux']
    measurements = []
    with tempfile.TemporaryDirectory(prefix='korri-plugin-churn-') as temporary:
        root = Path(temporary)
        unrelated = root / 'unrelated-korri'
        contract = root / 'contract-korri'
        copy_source(korri, unrelated)
        if source_hash(korri) != source_hash(unrelated):
            raise AssertionError('The pristine Core copy changed NAR content; use a clean flake source snapshot')
        append(unrelated / 'README.md', '\nPlugin churn regression: unrelated documentation.\n')
        copy_source(korri, contract)
        append(contract / 'contracts/generated/korrid.ts', '\n// Contract bytes changed for the churn regression.\n')
        sources = {}
        for case, relative_path, text in [
            ('helper', 'plugins/libretro/retroarch.ts', '\n// Helper bytes changed for the churn regression.\n'),
            ('settings', 'plugins/retroarch/check-settings.py', '\n# Settings producer changed for the churn regression.\n'),
            ('retroarch', 'plugins/retroarch/plugin.ts', '\n// Plugin source changed for the churn regression.\n'),
        ]:
            destination = root / f'{case}-publisher'
            copy_source(publisher, destination)
            append(destination / relative_path, text)
            sources[case] = destination
        for system in systems:
            start = time.monotonic()
            baseline = evaluate(publisher, korri, system, selection)
            game_plugins = set(baseline['packages']) - {'korri-plugin-ssh', 'korri-plugin-sunshine'}
            cases = [
                ('unrelated', publisher, unrelated, set(), set()),
                ('contract', publisher, contract, set(), {'korri-libretro-typecheck'}),
                ('helper', sources['helper'], korri, game_plugins,
                 {'korri-libretro-typecheck', 'korri-retroarch-settings'}),
                ('settings', sources['settings'], korri, game_plugins,
                 {'korri-libretro-typecheck', 'korri-retroarch-settings'}),
                ('retroarch', sources['retroarch'], korri, {'korri-plugin-retroarch'}, set()),
            ]
            for case, publisher_source, korri_source, expected_packages, expected_checks in cases:
                case_start = time.monotonic()
                result = evaluate(publisher_source, korri_source, system, selection)
                package_changes = changed(baseline['packages'], result['packages'])
                check_changes = changed(baseline['checks'], result['checks'])
                if package_changes != expected_packages or check_changes != expected_checks:
                    raise AssertionError(
                        f'{system} {case}: packages changed {sorted(package_changes)}, '
                        f'expected {sorted(expected_packages)}; checks changed {sorted(check_changes)}, '
                        f'expected {sorted(expected_checks)}'
                    )
                record = {
                    'system': system, 'case': case,
                    'selected_packages': len(baseline['packages']),
                    'changed_packages': sorted(package_changes),
                    'changed_checks': sorted(check_changes),
                    'evaluation_seconds': round(time.monotonic() - case_start, 2),
                }
                measurements.append(record)
                print(json.dumps(record), flush=True)
            print(f'{system}: all churn assertions passed in {time.monotonic() - start:.2f}s', flush=True)
    if args.report:
        args.report.write_text(json.dumps(measurements, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr or str(error)) from error

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


def replace(path, before, after):
    path.chmod(0o644)
    text = path.read_text()
    if text.count(before) != 1:
        raise AssertionError(f'Expected one mutation target in {path}')
    path.write_text(text.replace(before, after))


def append(path, text):
    path.chmod(0o644)
    with path.open('a') as handle:
        handle.write(text)


def derivations(paths):
    data = json.loads(subprocess.check_output(
        ['nix', 'derivation', 'show', *sorted(set(paths))], text=True,
    ))
    # Nix 2.34 uses store-relative paths in its versioned JSON format.
    if 'derivations' in data:
        data = {f'/nix/store/{path}': drv for path, drv in data['derivations'].items()}
        for drv in data.values():
            drv['inputDrvs'] = {f'/nix/store/{path}': value for path, value in drv['inputs']['drvs'].items()}
            for output in drv['outputs'].values():
                if 'path' in output:
                    output['path'] = f"/nix/store/{output['path']}"
    return data


def declared_packages(packages):
    # Read the builder's real manifest construction, without building wrappers.
    wrappers = derivations(package['derivation'] for package in packages.values())
    manifests = {}
    for name, package in packages.items():
        inputs = wrappers[package['derivation']]['inputDrvs']
        matches = [path for path in inputs if path.endswith('-plugin-manifest-base.json.drv')]
        if len(matches) != 1:
            raise AssertionError(f'{name}: expected one builder manifest, found {matches}')
        manifests[name] = matches[0]
    manifest_drvs = derivations(manifests.values())
    dependencies = derivations(path for drv in manifest_drvs.values() for path in drv['inputDrvs'])
    by_output = {output['path']: path for path, drv in dependencies.items()
                 for output in drv['outputs'].values() if 'path' in output}
    return {
        f'{name}:{key}': {'output': output, 'derivation': by_output[output]}
        for name, path in manifests.items()
        for key, output in json.loads(manifest_drvs[path]['env']['text'])['packages'].items()
    }


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
            inherit (c) korri-libretro-typecheck korri-plugin-host korri-retroarch-settings korri-plugin-builder;
          }}'''],
        text=True, capture_output=True, check=True,
    )
    packages = json.loads(packages.stdout)
    return {'packages': packages, 'checks': json.loads(checks.stdout),
            'declared_packages': declared_packages(packages)}


def host_free(publisher, korri, system, baseline):
    # A real dependency check, not just an assertion about the source imports.
    command = [
        'nix', 'eval', '--json', '--no-write-lock-file',
        '--option', 'eval-cache', 'false',
        '--option', 'allow-import-from-derivation', 'false',
        '--override-input', 'korri', f'path:{korri}',
    ]
    packages = json.loads(subprocess.check_output(
        command + [f'path:{publisher}#packages.{system}', '--apply', '''p:
          builtins.mapAttrs (_: package: { output = toString package; derivation = package.drvPath; }) {
            inherit (p) korri-tailscale korri-plugin-retroarch korri-plugin-mgba korri-plugin-ssh korri-plugin-sunshine;
          }'''], text=True,
    ))
    builder = json.loads(subprocess.check_output(
        command + [f'path:{publisher}#checks.{system}.korri-plugin-builder', '--apply',
                   'package: { output = toString package; derivation = package.drvPath; }'], text=True,
    ))
    for name, identity in packages.items():
        if name in baseline['packages'] and baseline['packages'][name] != identity:
            raise AssertionError(f'{system}: refusing host recipes changed {name}')
    if builder != baseline['checks']['korri-plugin-builder']:
        raise AssertionError(f'{system}: refusing host recipes changed the builder gate')
    dependencies = subprocess.check_output(
        ['nix-store', '--query', '--requisites', builder['derivation'],
         *[package['derivation'] for package in packages.values()]], text=True,
    ).splitlines()
    forbidden = [path for path in dependencies if
                 Path(path).name.split('-', 1)[1].startswith(
                     ('korri-plugin-host-', 'korrid-', 'korri-inputd-'))]
    if forbidden:
        raise AssertionError(f'{system}: host build dependency in plugin graph: {forbidden}')
    return len(dependencies)


def changed(before, after, field=None):
    if before.keys() != after.keys():
        raise AssertionError('The Mini V2 selection changed during the regression check')
    return {name for name in before if
            (before[name][field] != after[name][field] if field else before[name] != after[name])}


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
        builder = root / 'builder-korri'
        copy_source(korri, builder)
        # Change the actual derivation construction, not an unused comment.
        replace(builder / 'services/korrid/plugin-host/builder.nix',
                'pluginSource = source;',
                'pluginSource = source; builderRegression = "changed";')
        no_host = root / 'host-free-korri'
        copy_source(korri, no_host)
        for relative in ('services/korrid/plugin-host/package.nix',
                         'services/korrid/package.nix', 'services/inputd/package.nix'):
            path = no_host / relative
            path.chmod(0o644)
            path.write_text('throw "Host recipes must not be evaluated by plugin builds"\n')
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
        toolchain = root / 'toolchain-publisher'
        copy_source(publisher, toolchain)
        # The caller owns pkgs. Change real compiler flags only for OpenSSH,
        # which plugins/ssh/plugin.nix consumes, not the whole native toolchain.
        # withCFlags is the pinned nixpkgs stdenv adapter on both architectures.
        replace(toolchain / 'nix/default.nix', 'config.allowUnfree = true;', '''config.allowUnfree = true;
      overlays = [ (_: prev: {
        openssh = prev.openssh.override {
          stdenv = prev.withCFlags [ "-fno-omit-frame-pointer" ] prev.stdenv;
        };
      }) ];''')
        for system in systems:
            start = time.monotonic()
            baseline = evaluate(publisher, korri, system, selection)
            measurements.append({'system': system, 'case': 'baseline', 'identities': baseline})
            game_plugins = set(baseline['packages']) - {'korri-plugin-ssh', 'korri-plugin-sunshine'}
            cases = [
                ('unrelated', publisher, unrelated, set(), set()),
                ('contract', publisher, contract, set(), {'korri-libretro-typecheck'}),
                ('builder', publisher, builder, set(baseline['packages']), {'korri-plugin-builder'}),
                ('helper', sources['helper'], korri, game_plugins,
                 {'korri-libretro-typecheck', 'korri-retroarch-settings'}),
                ('settings', sources['settings'], korri, game_plugins,
                 {'korri-libretro-typecheck', 'korri-retroarch-settings'}),
                ('retroarch', sources['retroarch'], korri, {'korri-plugin-retroarch'}, set()),
                ('toolchain', toolchain, korri, game_plugins | {'korri-plugin-ssh'},
                 {'korri-libretro-typecheck', 'korri-retroarch-settings'}),
            ]
            for case, publisher_source, korri_source, expected_packages, expected_checks in cases:
                case_start = time.monotonic()
                result = evaluate(publisher_source, korri_source, system, selection)
                package_changes = changed(baseline['packages'], result['packages'])
                check_changes = changed(baseline['checks'], result['checks'])
                declared_changes = changed(baseline['declared_packages'], result['declared_packages'])
                expected_declared = set()
                if case in ('helper', 'settings'):
                    expected_declared = {f'{name}:retroarch-settings' for name in game_plugins}
                elif case == 'toolchain':
                    # Netpbm's fixed-output SVN fetch uses OpenSSH. The path
                    # through GTK/SDL preserves game outputs, not drv files.
                    expected_declared = {key for key in baseline['declared_packages']
                                         if key.split(':')[0] in game_plugins and not key.endswith(':autoconfig')}
                    expected_declared.add('korri-plugin-ssh:openssh')
                if declared_changes != expected_declared:
                    raise AssertionError(
                        f'{system} {case}: declared packages changed {sorted(declared_changes)}, '
                        f'expected {sorted(expected_declared)}'
                    )
                if package_changes != expected_packages or check_changes != expected_checks:
                    raise AssertionError(
                        f'{system} {case}: packages changed {sorted(package_changes)}, '
                        f'expected {sorted(expected_packages)}; checks changed {sorted(check_changes)}, '
                        f'expected {sorted(expected_checks)}'
                    )
                output_changes = {
                    group: changed(baseline[group], result[group], 'output')
                    for group in baseline
                }
                expected_outputs = {
                    'packages': {'korri-plugin-ssh'} if case == 'toolchain' else expected_packages,
                    'checks': set() if case == 'toolchain' else expected_checks,
                    'declared_packages': {'korri-plugin-ssh:openssh'} if case == 'toolchain' else expected_declared,
                }
                if output_changes != expected_outputs:
                    raise AssertionError(f'{system} {case}: outputs changed {output_changes}, expected {expected_outputs}')
                record = {
                    'system': system, 'case': case,
                    'selected_packages': len(baseline['packages']),
                    'changed_packages': sorted(package_changes),
                    'changed_checks': sorted(check_changes),
                    'changed_declared_packages': sorted(declared_changes),
                    'changed_package_outputs': sorted(output_changes['packages']),
                    'changed_check_outputs': sorted(output_changes['checks']),
                    'changed_declared_package_outputs': sorted(output_changes['declared_packages']),
                    'evaluation_seconds': round(time.monotonic() - case_start, 2),
                }
                if case == 'toolchain':
                    key = 'korri-plugin-ssh:openssh'
                    before, after = (derivations([state['declared_packages'][key]['derivation']])
                                     for state in (baseline, result))
                    before_env, after_env = (next(iter(state.values()))['env'] for state in (before, after))
                    flag = '-fno-omit-frame-pointer'
                    if flag in before_env.get('NIX_CFLAGS_COMPILE', '').split() or flag not in after_env.get('NIX_CFLAGS_COMPILE', '').split():
                        raise AssertionError(f'{system}: toolchain fixture did not change compiler flags')
                    for field in ('src', 'patches', 'buildInputs', 'nativeBuildInputs', 'stdenv'):
                        if before_env.get(field) != after_env.get(field):
                            raise AssertionError(f'{system}: toolchain fixture unexpectedly changed {field}')
                    record['compile_inputs'] = {field: after_env.get(field) for field in
                                                ('NIX_CFLAGS_COMPILE', 'src', 'patches', 'buildInputs', 'nativeBuildInputs', 'stdenv')}
                measurements.append({**record, 'identities': result})
                print(json.dumps(record), flush=True)
            dependencies = host_free(publisher, no_host, system, baseline)
            record = {'system': system, 'case': 'host-free', 'build_dependencies': dependencies}
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

#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 nix
"""Read the publisher cache; lifecycle verification can also read Core's cache.

Like Core's trust-korri-cache.sh, use GITHUB_ENV so the trusted CI client sends
these settings to the daemon. Do not change /etc/nix/nix.conf after installation.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import uuid
from urllib.parse import urlsplit


def effective_config(env):
    return json.loads(subprocess.check_output(["nix", "config", "show", "--json"], env=env))


def cache_settings(root, env, include_core=False):
    expression = (
        f"let publisher = builtins.getFlake {json.dumps(str(root))}; "
        f"in import {json.dumps(str(root / 'nix/ci-cache-settings.nix'))} "
        f"{{ korri = publisher.inputs.korri; includeCore = {str(include_core).lower()}; }}"
    )
    return json.loads(subprocess.check_output(
        ["nix", "eval", "--json", "--impure", "--expr", expression], env=env
    ))


def configured_environment(settings, env):
    # Keep installer/client settings and add only the owner-defined URLs/keys.
    config = env.get("NIX_CONFIG", "").rstrip() + "\n" + "\n".join([
        "extra-substituters = " + " ".join(settings["substituters"]),
        "extra-trusted-public-keys = " + " ".join(settings["publicKeys"]),
        "require-sigs = true",
    ]) + "\n"
    before = effective_config(env)
    configured = env | {"NIX_CONFIG": config}
    after = effective_config(configured)
    for name, values in (
        ("substituters", settings["substituters"]),
        ("trusted-public-keys", settings["publicKeys"]),
    ):
        expected = set(before[name]["value"]) | set(values)
        if set(after[name]["value"]) != expected:
            raise RuntimeError(f"{name} differs from the existing settings plus owner identities")
    if not after["require-sigs"]["value"]:
        raise RuntimeError("Nix must require signatures")
    return configured


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-core', action='store_true', help='Lifecycle verification only; never for publishing builds')
    args = parser.parse_args()
    github_env = Path(os.environ["GITHUB_ENV"])
    root = Path(__file__).resolve().parents[2]
    settings = cache_settings(root, os.environ, include_core=args.include_core)
    if not args.include_core:
        all_settings = cache_settings(root, os.environ, include_core=True)
        core_urls = set(all_settings['substituters']) - set(settings['substituters'])
        # Native store URI parameters can change priority, not the cache owner.
        def endpoint(uri):
            parsed = urlsplit(uri)
            scheme = parsed.scheme.lower()
            port = parsed.port or {'https': 443, 'http': 80}.get(scheme)
            return scheme, (parsed.hostname or '').lower(), port, parsed.path.rstrip('/')
        inherited = effective_config(os.environ)['substituters']['value']
        if {endpoint(url) for url in inherited} & {endpoint(url) for url in core_urls}:
            raise RuntimeError('Publishing builds must start without the Core cache; inherited signatures can conflict with published metadata')
    configured = configured_environment(settings, dict(os.environ))
    delimiter = "PLUGIN_NIX_CONFIG_" + uuid.uuid4().hex
    with github_env.open("a") as stream:
        stream.write(f"NIX_CONFIG<<{delimiter}\n{configured['NIX_CONFIG']}{delimiter}\n")
    print("Verified effective substituters: " + " ".join(
        effective_config(configured)["substituters"]["value"]
    ))
    print("Verified owner-defined public keys; require-sigs = true")


if __name__ == "__main__":
    main()

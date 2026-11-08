"""Print only the existing check references for this publication's packages."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SYSTEMS = ("x86_64-linux", "aarch64-linux")
SHARED = ("korri-device-cache", "korri-plugin-builder")


def select_checks(mapping, packages):
    if not packages:
        raise ValueError("At least one package is required")
    unknown = sorted(set(packages) - mapping.keys())
    if unknown:
        raise ValueError("No reviewed publication gates for: " + ", ".join(unknown))
    return sorted(set(SHARED).union(*(mapping[name] for name in packages)))


def select_packages(mappings, platforms, packages, system):
    # Unknown outputs fail before filtering. A platform restriction must not
    # turn a typo or an entirely unsupported plugin into a successful batch.
    for mapping in mappings.values():
        select_checks(mapping, packages)
    unavailable = [
        name for name in packages
        if not any(platforms[target].get(name, True) for target in SYSTEMS)
    ]
    if unavailable:
        raise ValueError(
            "Packages unavailable on every publication architecture: "
            + ", ".join(sorted(set(unavailable)))
        )
    return [
        name for name in dict.fromkeys(packages)
        if platforms[system].get(name, True)
    ]


def evaluate(attribute):
    return json.loads(subprocess.check_output(
        ["nix", "eval", "--json", f".#{attribute}"], text=True
    ))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", choices=SYSTEMS, required=True)
    parser.add_argument("--packages-file", type=Path)
    parser.add_argument("packages", nargs="+")
    args = parser.parse_args()
    mappings = {
        system: evaluate(f"ci.publicationChecks.{system}") for system in SYSTEMS
    }
    platforms = {
        system: evaluate(f"ci.publicationPlatforms.{system}") for system in SYSTEMS
    }
    try:
        packages = select_packages(mappings, platforms, args.packages, args.system)
        if not packages:
            raise ValueError(f"No selected packages are available on {args.system}")
        checks = select_checks(mappings[args.system], packages)
    except ValueError as error:
        parser.error(str(error))
    for package in sorted(set(args.packages) - set(packages)):
        print(f"Skipping {package} on {args.system}: core platform metadata", file=sys.stderr)
    if args.packages_file:
        args.packages_file.write_text("\n".join(packages) + "\n")
    for check in checks:
        print(f".#ci.checks.{args.system}.{check}")


if __name__ == "__main__":
    main()

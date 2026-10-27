"""Print only the existing check references for this publication's packages."""

import argparse
import json
import subprocess

SYSTEMS = ("x86_64-linux", "aarch64-linux")
SHARED = ("korri-device-cache", "korri-plugin-builder")


def select_checks(mapping, packages):
    if not packages:
        raise ValueError("At least one package is required")
    unknown = sorted(set(packages) - mapping.keys())
    if unknown:
        raise ValueError("No reviewed publication gates for: " + ", ".join(unknown))
    return sorted(set(SHARED).union(*(mapping[name] for name in packages)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", choices=SYSTEMS, required=True)
    parser.add_argument("packages", nargs="+")
    args = parser.parse_args()
    mapping = json.loads(
        subprocess.check_output(
            ["nix", "eval", "--json", f".#ci.publicationChecks.{args.system}"],
            text=True,
        )
    )
    try:
        checks = select_checks(mapping, args.packages)
    except ValueError as error:
        parser.error(str(error))
    for check in checks:
        print(f".#ci.checks.{args.system}.{check}")


if __name__ == "__main__":
    main()

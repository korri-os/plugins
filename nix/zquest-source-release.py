#!/usr/bin/env python3
"""Assemble buildable corresponding source without the upstream media tree."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def replace_once(text: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, lambda _: replacement, text, flags=re.M | re.S)
    if count != 1:
        raise ValueError(
            f"Expected one source recipe binding, found {count}: {pattern}"
        )
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument(
        "--system", choices=("x86_64-linux", "aarch64-linux"), required=True
    )
    parser.add_argument("--dependency", nargs=2, action="append", default=[])
    parser.add_argument("--audit-script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(args.source, output / "engine")
    shutil.copytree(args.recipe, output / "recipe")
    # Keep the exact checked upstream resource bytes alongside the generator
    # sources. Unlike a generic GitHub source snapshot, this has no raw quests,
    # game music, default sound bank, or old bitmap-font collection.
    dependencies = dict(args.dependency)
    assert set(dependencies) == {"stduuid", "allegro5", "gme", "poolSTL"}
    for name, path in dependencies.items():
        shutil.copytree(path, output / "dependencies" / name)
    # copytree preserves read-only Nix store directory modes. Make only this
    # private export writable before pruning (never mutate the source inputs).
    for directory in output.rglob("*"):
        if directory.is_dir():
            directory.chmod(directory.stat().st_mode | 0o200)
    # Keep demo/test code and notices, but not the bundled recordings, fonts,
    # images or opaque archives. None is a native library build input: Allegro
    # gates demos/examples/tests in its root CMakeLists, and GME gates demo/.
    spec = importlib.util.spec_from_file_location(
        "source_archive_check", args.audit_script
    )
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    removed = []
    for name in dependencies:
        root = output / "dependencies" / name
        for file in sorted(root.rglob("*")):
            if not file.is_file():
                continue
            relative = file.relative_to(root)
            data = file.read_bytes()
            non_build = (
                name == "allegro5"
                and relative.parts[0] in {"demos", "examples", "tests", "android"}
            ) or (name == "gme" and relative.as_posix() in {"test.nsf", "test.vgz"})
            if non_build and checker.is_media(file, data):
                removed.append(
                    f"{hashlib.sha256(data).hexdigest()}  {file.relative_to(output)}\n"
                )
                file.unlink()
    # The engine vendors two more libraries with unused setup/example media.
    # Their native library CMake/source lists do not reference these files.
    for relative in (
        "third_party/allegro_legacy/setup/setup.dat",
        "third_party/al_loadpng/examples/alpha.png",
        "third_party/al_loadpng/examples/exdata.dat",
    ):
        file = output / "engine" / relative
        if file.is_file():
            removed.append(
                f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.relative_to(output)}\n"
            )
            file.unlink()
    (output / "SOURCE-PRUNING.txt").write_text(
        "Altered source export: non-build dependency media removed.\n"
        "Library source and all copyright/license notices are unchanged.\n"
        "Demo/example code is retained for reference, but its media-dependent\n"
        "builds/tests are unavailable. Android's prebuilt Gradle wrapper is omitted.\n"
        "Removed input SHA-256 inventory (these bytes are NOT in this archive):\n"
        + "".join(sorted(removed))
    )
    shutil.copyfile(args.audit_script, output / "source-archive-check.py")
    shutil.copyfile(args.lock, output / "flake.lock")
    recipe = (args.recipe / "package.nix").read_text()
    for name in dependencies:
        recipe = replace_once(
            recipe,
            rf"^  {name} = pkgs\.fetchFromGitHub \{{.*?^  \}};",
            f"  {name} = ./dependencies/{name};",
        )
    # The source is already patched and its resources already generated. Use
    # it directly: this recipe never downloads the unapproved source archive.
    recipe = replace_once(
        recipe,
        r"^  upstream = pkgs\.fetchFromGitHub \{.*?^  \};",
        '  upstream = { rev = "882c906b17e35b4105188e6305ae2929aeba30e3"; };',
    )
    recipe = replace_once(
        recipe,
        r"^  assets = import ./public-assets\.nix \{.*?\};",
        "  assets = ./engine/resources;",
    )
    recipe = replace_once(
        recipe,
        r"^  publicSource = import ./public-source\.nix \{.*?^  \};",
        "  publicSource = ./engine;",
    )
    # Derive the native recipe, never maintain a second list of build inputs.
    # Allegro's switches are already forced OFF by the engine CMakeLists;
    # explicitly disable GME's demo copy targets and every other test consumer.
    recipe = replace_once(
        recipe,
        r"^  cmakeFlags = \[",
        "  cmakeFlags = [\n"
        '    "-DFETCHCONTENT_FULLY_DISCONNECTED=ON"\n'
        '    "-DGME_BUILD_EXAMPLES=OFF"\n'
        '    "-DGME_BUILD_TESTING=OFF"\n'
        '    "-DBUILD_TESTING=OFF"\n'
        '    "-DWANT_DEMO=OFF"\n'
        '    "-DWANT_EXAMPLES=OFF"\n'
        '    "-DWANT_TESTS=OFF"\n',
    )
    # All local helper/patch paths keep their native relative names.
    for file in args.recipe.iterdir():
        if file.is_file() and file.name != "package.nix":
            shutil.copyfile(file, output / file.name)
    (output / "package.nix").write_text(recipe)
    lock = json.loads(args.lock.read_text())
    nixpkgs_id = lock["nodes"]["root"]["inputs"]["nixpkgs"]
    pin = lock["nodes"][nixpkgs_id]["locked"]
    assert (
        pin["type"] == "github" and pin["owner"] == "NixOS" and pin["repo"] == "nixpkgs"
    )
    expression = f'''{{ pkgs ? import (builtins.fetchTree {{
  type = "github";
  owner = "NixOS";
  repo = "nixpkgs";
  rev = "{pin["rev"]}";
  narHash = "{pin["narHash"]}";
}}) {{ system = "{args.system}"; }} }}:
assert pkgs.stdenv.hostPlatform.system == "{args.system}";
import ./package.nix {{ inherit pkgs; }}
'''
    (output / "default.nix").write_text(expression)
    (
        output / "BUILDING.txt"
    ).write_text(f"""ZQuest Classic public player corresponding source ({args.system})

This archive contains the cleaned engine source used for this architecture,
its four explicitly fetched CMake dependency sources, the generated runtime
assets, their generator/input notices, and the original and standalone build
recipes. Engine and library copyright/license notices remain with their code.
Non-build dependency demo/test media is pruned; see SOURCE-PRUNING.txt for
exact removed paths and input hashes. Library code and notices are preserved.
The retained demo/example code cannot build or run its media-dependent targets.
The standalone player recipe disables those targets. No original Nintendo
soundtrack, default font datafile, sound bank, or quest is included in this
bundle. Common game glyphs use Tiny5 fitted to the existing slot metrics.
Uncovered Unicode/symbol glyphs use the licensed ProggyVector input, which
also remains for the debugger. The Tiny5 glyph source and complete OFL 1.1
notice are in tiny5.glyphs.txt and tiny5-OFL.txt, both at the root and in
recipe/. Keep Tiny5 and ProggyVector notices with their derivatives.
See ASSET-LICENSES.md, engine/resources/public-assets-font-license.txt and
engine/LICENSE.

Build on a Linux build machine with Nix, not a target handheld:
  nix-build default.nix --no-out-link --option extra-experimental-features flakes

The default expression fetches the exact pinned Nixpkgs tooling and declared
system libraries. It uses the bundled engine/dependency sources, not the old
upstream media archive. Source is architecture-specific because it includes
the exact ARM scalar-renderer patch when applicable. The pinned Nixpkgs source
contains the build recipes and origin information for the system libraries.
No promise of byte-identical store paths after extracting a source archive is
made; the source and build instructions are provided to rebuild and modify it.

To regenerate resources with the pinned Pillow/FreeType toolchain, use the
public-assets.nix/public-assets.py files, tiny5.glyphs.txt, tiny5-OFL.txt and
engine/resources/ProggyVector-Regular.ttf. public-assets.nix copies the
vendored glyph table and OFL notice beside the generator before running it.
The regenerated assets must match engine/resources/ byte for byte.
The files in recipe/ preserve the original repository recipe and patch inputs.
The root package.nix is derived from it to use bundled sources, disable
media-dependent demo/test targets, and forbid CMake FetchContent downloads.
Run python3 source-archive-check.py . to repeat the whole-bundle media gate.
Do not reapply patches to engine/: they are already applied there.

Plugin integration source: https://github.com/korri-os/plugins
The release's revision.txt identifies its exact source commit and its path
lists identify the released plugin outputs. This source archive is not a game.
""")
    subprocess.run(
        [
            sys.executable,
            str(output / "source-archive-check.py"),
            str(output),
            "--report",
            str(output / "SOURCE-AUDIT.txt"),
        ],
        check=True,
    )
    files = sorted(p for p in output.rglob("*") if p.is_file())
    (output / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(output)}\n"
            for p in files
        )
    )
    assert "pkgs.fetchFromGitHub" not in recipe
    print(
        f"Corresponding source for {args.system}: {len(files)} files; standalone recipe uses bundled sources."
    )


if __name__ == "__main__":
    main()

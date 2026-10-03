#!/usr/bin/env nix
#! nix shell nixpkgs#python3 --command python3
"""Package the two approved source layouts without changing quest file bytes."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
import zipfile


MAX_FILES = 20_000
MAX_BYTES = 512 * 1024 * 1024


def source_files(archive):
    files = {}
    roots = set()
    total = 0
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or "\\" in member.name:
                raise ValueError("unsafe source archive path")
            if member.isdir():
                continue
            if not member.isfile() or len(path.parts) < 2:
                raise ValueError("source archive must contain only regular files")
            roots.add(path.parts[0])
            relative = PurePosixPath(*path.parts[1:]).as_posix()
            total += member.size
            if relative in files or len(files) >= MAX_FILES or total > MAX_BYTES:
                raise ValueError("duplicate file or oversized source archive")
            stream = source.extractfile(member)
            if stream is None:
                raise ValueError("unreadable source archive entry")
            content = stream.read(member.size + 1)
            if len(content) != member.size:
                raise ValueError("invalid source archive entry size")
            files[relative] = content
    if len(roots) != 1:
        raise ValueError("expected one upstream repository root")
    return files


def quest_files(files):
    # Both upstreams already put runtime files in data/. Perlshaw alone keeps
    # editor/quest metadata at repository root; package it at Solarus's required
    # archive root. This is a build-time layout change, not a runtime fallback.
    quest = {
        name.removeprefix("data/"): content
        for name, content in files.items()
        if name.startswith("data/")
    }
    for name in ["quest.dat", "project_db.dat"]:
        if name not in quest:
            quest[name] = files[name]
    if not {"main.lua", "quest.dat", "project_db.dat"} <= set(quest):
        raise ValueError("incomplete native Solarus quest")
    license_text = files["LICENSE"]
    if b"GNU GENERAL PUBLIC LICENSE" not in license_text:
        raise ValueError("missing original GPL license")
    if "LICENSE" in quest and quest["LICENSE"] != license_text:
        raise ValueError("conflicting original LICENSE")
    quest["LICENSE"] = license_text
    # VOADI's original notice grants quest.dat and adds contributor credits.
    if "attributions.txt" in files:
        quest["attributions.txt"] = files["attributions.txt"]
    return quest


def write_quest(archive, source_name, url, output_hash, destination):
    if Path(source_name).name != source_name or not source_name.endswith(".tar.gz"):
        raise ValueError("expected the original repository archive basename")
    name = source_name.removesuffix(".tar.gz")
    files = source_files(archive)
    quest = quest_files(files)
    destination = Path(destination)
    cartridges = destination / "cartridges"
    notices = destination / "notices" / name
    cartridges.mkdir(parents=True, exist_ok=True)
    notices.mkdir(parents=True, exist_ok=True)
    output = cartridges / (name + ".solarus")
    if output.exists():
        raise ValueError("duplicate packaged quest")
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as packaged:
        for path, content in sorted(quest.items()):
            entry = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            packaged.writestr(entry, content)
    # Retain original notices in their original filenames. The per-file source
    # database carries the individual artist, font, audio and script grants.
    for filename in ["LICENSE", "README.md", "attributions.txt"]:
        if filename in files:
            (notices / filename).write_bytes(files[filename])
    (notices / "project_db.dat").write_bytes(quest["project_db.dat"])
    relocated = [name for name in ["quest.dat", "project_db.dat"] if name in files]
    (notices / "source.txt").write_text(
        f"Original source: {url}\n"
        f"Original fetchurl pin: {output_hash}\n"
        f"Original archive SHA-256: {hashlib.sha256(Path(archive).read_bytes()).hexdigest()}\n"
        f"Packaged quest: {output.name}\n"
        "Modification: packaged data/ at the archive root; retained all file bytes.\n"
        f"Repository-root metadata included: {', '.join(relocated) or 'none'}\n"
        "Original GPL LICENSE included at the quest archive root.\n"
        "The root GPL grant does not replace per-file code or asset exceptions.\n"
        "Individual asset licenses and credits remain in project_db.dat.\n"
        "CC BY 3.0: https://creativecommons.org/licenses/by/3.0/\n"
        "CC BY 4.0: https://creativecommons.org/licenses/by/4.0/\n"
        "CC BY-SA 3.0: https://creativecommons.org/licenses/by-sa/3.0/\n"
        "CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/\n"
        "CC0: https://creativecommons.org/publicdomain/zero/1.0/\n"
    )


def write_credits(snapshot, destination):
    # Consume the actual first-party GitLab wiki format, not a new manifest.
    source = Path(snapshot).read_bytes()
    page = json.loads(source)
    if (
        page["format"] != "markdown"
        or not isinstance(page["content"], str)
        or not page["content"]
    ):
        raise ValueError("invalid original credits snapshot")
    destination = Path(destination)
    (destination / "credits.json").write_bytes(source)
    (destination / "credits.md").write_bytes(page["content"].encode("utf-8"))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--credits":
        write_credits(*sys.argv[2:])
    elif len(sys.argv) == 6:
        write_quest(*sys.argv[1:])
    else:
        raise SystemExit(
            "usage: package-solarus-quest.py ARCHIVE NAME URL HASH DESTINATION | --credits SNAPSHOT NOTICES"
        )

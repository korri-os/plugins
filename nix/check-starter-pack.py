#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.pillow

"""Check the real payload against fetchurl pins and independent upstream bytes."""

import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile
import tempfile
from urllib.parse import urlparse
import zipfile

from PIL import Image


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256_pin(entry):
    sri = entry["outputHash"]
    require(sri.startswith("sha256-"), "expected native SHA-256 SRI pin")
    expected = base64.b64decode(sri.removeprefix("sha256-"), validate=True)
    require(len(expected) == 32, "invalid SHA-256 pin")
    return expected


def regular_file(path, message):
    require(path.is_file() and not path.is_symlink(), message)


def read_quest_originals(records):
    """Read pinned tarballs, without calling or importing the quest packager."""
    require(
        isinstance(records, list)
        and len(records) == 2
        and all(isinstance(entry, dict) for entry in records),
        "expected two original quest source records",
    )
    require(len({entry["name"] for entry in records}) == 2, "duplicate quest sources")
    originals = []
    for entry in records:
        name = entry["name"]
        require(
            Path(name).name == name and name.endswith(".tar.gz"),
            "invalid original quest source filename",
        )
        uri = urlparse(entry["url"])
        require(
            uri.scheme == "https" and uri.hostname in {"api.github.com", "gitlab.com"},
            "unexpected original quest source",
        )
        source_path = Path(entry["sourcePath"])
        regular_file(source_path, "missing original quest tarball")
        digest = hashlib.sha256(source_path.read_bytes()).digest()
        require(digest == sha256_pin(entry), "changed original quest tarball: " + name)
        repository_files = {}
        repository_roots = set()
        with tarfile.open(source_path, "r:gz") as source:
            for member in source:
                path = PurePosixPath(member.name)
                require(
                    not path.is_absolute()
                    and ".." not in path.parts
                    and "\\" not in member.name,
                    "unsafe original quest path",
                )
                require(len(path.parts) >= 1, "empty original quest path")
                repository_roots.add(path.parts[0])
                if member.isdir():
                    continue
                require(
                    member.isfile() and len(path.parts) >= 2,
                    "original quest entry is not a repository regular file",
                )
                relative = PurePosixPath(*path.parts[1:]).as_posix()
                require(
                    relative not in repository_files, "duplicate original quest file"
                )
                stream = source.extractfile(member)
                require(stream is not None, "unreadable original quest file")
                with stream:
                    binary = stream.read()
                require(len(binary) == member.size, "truncated original quest file")
                repository_files[relative] = binary
        require(len(repository_roots) == 1, "expected one original repository root")
        # Derive the complete inventory from upstream data/, not the generated ZIP.
        quest_files = {
            path[len("data/") :]: binary
            for path, binary in repository_files.items()
            if path.startswith("data/")
        }
        require(quest_files, "missing original data/ files")
        for metadata in ["quest.dat", "project_db.dat"]:
            if metadata not in quest_files:
                require(metadata in repository_files, "missing original quest metadata")
                quest_files[metadata] = repository_files[metadata]
        require("main.lua" in quest_files, "missing original quest entrypoint")
        require(
            {"LICENSE", "README.md"} <= set(repository_files),
            "missing original repository notices",
        )
        license_bytes = repository_files["LICENSE"]
        require(
            b"GNU GENERAL PUBLIC LICENSE" in license_bytes
            and b"TERMS AND CONDITIONS" in license_bytes,
            "missing original GPL license",
        )
        require(
            "LICENSE" not in quest_files or quest_files["LICENSE"] == license_bytes,
            "conflicting original quest LICENSE",
        )
        quest_files["LICENSE"] = license_bytes
        if "attributions.txt" in repository_files:
            quest_files["attributions.txt"] = repository_files["attributions.txt"]
        originals.append(
            {
                **entry,
                "repository": name.removesuffix(".tar.gz"),
                "archive": name.removesuffix(".tar.gz") + ".solarus",
                "sourceDigest": digest.hex(),
                "files": quest_files,
                "notices": {
                    "LICENSE": license_bytes,
                    "README.md": repository_files["README.md"],
                    "project_db.dat": quest_files["project_db.dat"],
                    **(
                        {"attributions.txt": repository_files["attributions.txt"]}
                        if "attributions.txt" in repository_files
                        else {}
                    ),
                },
            }
        )
    return originals


def read_checksums(payload):
    checksums = {}
    for line in (payload / "SHA256SUMS").read_text().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        require(match is not None, "invalid checksum line")
        digest, name = match.groups()
        require(name not in checksums, "duplicate checksum entry")
        checksums[name] = digest
    return checksums


def check_quest(payload, original, checksums):
    name = original["archive"]
    path = payload / "cartridges" / name
    regular_file(path, "quest must be a regular file")
    require(
        hashlib.sha256(path.read_bytes()).hexdigest() == checksums[name],
        "changed quest checksum: " + name,
    )
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            require(len(names) == len(set(names)), "duplicate quest archive entry")
            require("LICENSE" in names, "missing original GPL LICENSE in quest")
            require(
                {"quest.dat", "project_db.dat", "main.lua"} <= set(names),
                "missing root quest metadata or entrypoint",
            )
            require(
                set(names) == set(original["files"]),
                "wrong quest file inventory: " + name,
            )
            for entry in entries:
                relative = PurePosixPath(entry.filename)
                require(
                    not relative.is_absolute()
                    and ".." not in relative.parts
                    and "\\" not in entry.filename
                    and relative.as_posix() == entry.filename
                    and not entry.is_dir()
                    and stat.S_IFMT(entry.external_attr >> 16) in {0, stat.S_IFREG}
                    and not entry.flag_bits & 1,
                    "quest archive entry must be a regular relative file",
                )
                require(
                    archive.read(entry) == original["files"][entry.filename],
                    "changed original quest file: " + name + "/" + entry.filename,
                )
    except zipfile.BadZipFile as error:
        raise ValueError("invalid quest ZIP: " + name) from error
    notices = payload / "notices" / original["repository"]
    require(
        notices.is_dir() and not notices.is_symlink(), "missing original quest notices"
    )
    for filename, binary in original["notices"].items():
        notice = notices / filename
        regular_file(notice, "missing original quest notice: " + filename)
        require(
            notice.read_bytes() == binary, "changed original quest notice: " + filename
        )
    # Additional credit supplements are allowed; the four original notices are not optional.
    source_path = notices / "source.txt"
    regular_file(source_path, "missing quest source notice")
    source_lines = source_path.read_text().splitlines()
    for expected, message in [
        ("Original source: " + original["url"], "missing quest source URL"),
        (
            "Original fetchurl pin: " + original["outputHash"],
            "missing quest source pin",
        ),
        (
            "Original archive SHA-256: " + original["sourceDigest"],
            "missing quest source digest",
        ),
        ("Packaged quest: " + name, "missing quest archive source mapping"),
    ]:
        require(expected in source_lines, message)


def check_payload(payload, originals, quests):
    require(len(originals) == 25, "expected 25 files for the 24 selected games")
    pico_names = [entry["name"] for entry in originals]
    require(len(set(pico_names)) == 25, "duplicate original cartridge names")
    names = pico_names + [quest["archive"] for quest in quests]
    require(
        len(names) == 27 and len(set(names)) == 27, "expected 27 distinct payload files"
    )
    cartridges = payload / "cartridges"
    require(
        {path.name for path in cartridges.iterdir()} == set(names),
        "unexpected or missing cartridge",
    )
    credits = (payload / "CREDITS.md").read_text()
    pico_rows, solarus_rows = [], []
    section = None
    for line in credits.splitlines():
        if line.startswith("## "):
            section = line
        if line.startswith("| ["):
            (solarus_rows if section == "## Solarus quests" else pico_rows).append(line)
    require(len(pico_rows) == 24, "expected credits for 24 games")
    require(
        credits.splitlines().count("## Solarus quests") == 1 and len(solarus_rows) == 2,
        "expected credits for two Solarus quests",
    )
    for quest in quests:
        require(
            sum(quest["archive"] in row for row in solarus_rows) == 1,
            "missing Solarus quest credit mapping",
        )
    license_text = (payload / "CC-BY-NC-SA-4.0.txt").read_text()
    require(
        license_text.startswith(
            "Attribution-NonCommercial-ShareAlike 4.0 International"
        ),
        "wrong license",
    )
    require("Disclaimer of Warranties" in license_text, "missing warranty disclaimer")
    instructions = (payload / "README.md").read_text()
    require("no PICO-8 application" in instructions, "missing player exclusion")
    require(
        "does not perform that step or add game tiles" in instructions,
        "missing manual-registration limit",
    )
    notices = payload / "notices"
    require(len(list(notices.glob("*.txt"))) == 25, "missing publisher notices")
    source_notices = "\n".join(path.read_text() for path in notices.glob("*.txt"))
    checksums = read_checksums(payload)
    require(set(checksums) == set(names), "incomplete checksum inventory")
    for entry in originals:
        name = entry["name"]
        require(
            Path(name).name == name and name.endswith(".p8.png"),
            "invalid original filename",
        )
        path = cartridges / name
        regular_file(path, "cartridge must be a regular file")
        uri = urlparse(entry["url"])
        require(
            uri.scheme == "https"
            and uri.hostname in {"www.lexaloffle.com", "raw.githubusercontent.com"},
            "unexpected original source",
        )
        require(
            entry["url"] in source_notices and any(name in row for row in pico_rows),
            "missing original source or credit mapping",
        )
        expected = sha256_pin(entry)
        binary = path.read_bytes()
        digest = hashlib.sha256(binary).digest()
        require(
            digest == expected and digest.hex() == checksums[name],
            "changed original cartridge: " + name,
        )
        require(binary.startswith(b"\x89PNG\r\n\x1a\n"), "not a PNG cartridge")
        with Image.open(path) as image:
            require(
                image.size == (160, 205) and image.mode == "RGBA",
                "invalid cartridge dimensions or channels",
            )
            memory = bytes(
                (b & 3) | ((g & 3) << 2) | ((r & 3) << 4) | ((a & 3) << 6)
                for r, g, b, a in image.getdata()
            )
        require(
            len(memory) == 32800 and any(memory[0x4300:0x8000]),
            "missing encoded cartridge code",
        )
    require(
        {"intoruins.p8.png", "intoruins_main.p8.png"} <= set(pico_names),
        "missing original offline pair",
    )
    require(
        "intoruins-7.p8.png" not in pico_names,
        "BBS title is not the offline distribution",
    )
    for quest in quests:
        check_quest(payload, quest, checksums)


def check_runtime(plugin, name, native_files):
    manifest = json.loads((plugin / "manifest.json").read_text())
    label = "FAKE-08" if name == "fake08" else "Solarus"
    require(
        manifest["publisher"] == {"namespace": "@korri"},
        "wrong " + label + " publisher claim",
    )
    require(
        f'export const name = "{name}"' in (plugin / "plugin.ts").read_text(),
        "wrong required plugin identity",
    )
    require(
        set(native_files) <= set(manifest["packages"]),
        "required plugin lacks frontend, core or engine",
    )
    require(
        not manifest.get("requires", []), "required runtime must remain a leaf plugin"
    )
    for key, relative in native_files.items():
        program = Path(manifest["packages"][key]) / relative
        require(
            program.is_absolute() and manifest["files"].get(key) == str(program),
            "wrong required native artifact: " + key,
        )
        require(program.is_file(), "missing required native artifact")
        with program.open("rb") as stream:
            require(stream.read(4) == b"\x7fELF", "required native artifact is not ELF")


def check_plugin(plugin, payload, fake08_plugin, solarus_plugin):
    manifest = json.loads((plugin / "manifest.json").read_text())
    require(
        manifest.get("requires") == [str(fake08_plugin), str(solarus_plugin)],
        "missing exact FAKE-08 and Solarus plugin dependencies",
    )
    check_runtime(
        fake08_plugin,
        "fake08",
        {
            "retroarch": "bin/retroarch",
            "fake08": "lib/retroarch/cores/fake08_libretro.so",
        },
    )
    check_runtime(solarus_plugin, "solarus", {"solarus": "bin/solarus-run"})
    require(manifest["publisher"] == {"namespace": "@korri"}, "wrong publisher")
    require(
        manifest["entry"] == "plugin.ts" and manifest["sources"] == ["plugin.ts"],
        "unexpected source inventory",
    )
    require(
        manifest["services"] == {} and manifest["ports"] == {},
        "data pack must request no native services or ports",
    )
    require(
        manifest["packages"] == {"cartridges": str(payload.parent.parent)},
        "unexpected runtime package",
    )
    expected = {
        "cartridges": payload / "cartridges",
        "credits": payload / "CREDITS.md",
        "license": payload / "CC-BY-NC-SA-4.0.txt",
        "notices": payload / "notices",
        "checksums": payload / "SHA256SUMS",
        "instructions": payload / "README.md",
    }
    require(
        manifest["files"] == {name: str(path) for name, path in expected.items()},
        "wrong packaged file references",
    )
    require(
        all(path.exists() for path in expected.values()), "missing named payload file"
    )
    source = (plugin / "plugin.ts").read_text()
    require(
        set(re.findall(r"export const (\w+) =", source))
        == {"name", "title", "description"},
        "unexpected plugin contribution",
    )
    require('export const name = "starter-pack"' in source, "wrong plugin identity")
    require('export const title = "Starter pack"' in source, "wrong plugin title")


def writable_copy(source, destination):
    shutil.copytree(source, destination)
    destination.chmod(0o755)
    for path in destination.rglob("*"):
        path.chmod(0o755 if path.is_dir() else 0o644)


def negative_checks(payload, originals, quests):
    with tempfile.TemporaryDirectory() as directory:
        damaged = Path(directory) / "pack"
        writable_copy(payload, damaged)
        victim = damaged / "cartridges" / originals[0]["name"]
        victim.write_bytes(victim.read_bytes() + b"changed")
        expect_failure(
            lambda: check_payload(damaged, originals, quests),
            "changed original cartridge",
        )
        shutil.copyfile(payload / "cartridges" / originals[0]["name"], victim)
        (damaged / "cartridges" / "intoruins_main.p8.png").unlink()
        expect_failure(
            lambda: check_payload(damaged, originals, quests),
            "unexpected or missing cartridge",
        )
        shutil.copyfile(
            payload / "cartridges" / "intoruins_main.p8.png",
            damaged / "cartridges" / "intoruins_main.p8.png",
        )
        (damaged / "CC-BY-NC-SA-4.0.txt").write_text("wrong license")
        expect_failure(
            lambda: check_payload(damaged, originals, quests), "wrong license"
        )
        shutil.copyfile(
            payload / "CC-BY-NC-SA-4.0.txt", damaged / "CC-BY-NC-SA-4.0.txt"
        )
        (damaged / "CREDITS.md").write_text("no credits")
        expect_failure(
            lambda: check_payload(damaged, originals, quests), "expected credits"
        )


def rewrite_quest(source, destination, change):
    with (
        zipfile.ZipFile(source) as original,
        zipfile.ZipFile(destination, "w") as damaged,
    ):
        for entry in original.infolist():
            replacement = change(entry.filename, original.read(entry))
            if replacement is not None:
                name, binary = replacement
                # ZIP encoding is not an upstream pin. Change it freely in the
                # negative fixture; acceptance must depend on upstream file bytes.
                damaged.writestr(name, binary, compress_type=zipfile.ZIP_STORED)


def update_checksum(payload, name):
    checksums = read_checksums(payload)
    checksums[name] = hashlib.sha256(
        (payload / "cartridges" / name).read_bytes()
    ).hexdigest()
    (payload / "SHA256SUMS").write_text(
        "".join(
            f"{digest}  {filename}\n" for filename, digest in sorted(checksums.items())
        )
    )


def negative_quest_checks(payload, originals, quests):
    with tempfile.TemporaryDirectory() as directory:
        damaged = Path(directory) / "pack"
        writable_copy(payload, damaged)
        # Use the smaller real quest to keep recompressed negative fixtures small.
        quest = min(
            quests,
            key=lambda entry: (
                (payload / "cartridges" / entry["archive"]).stat().st_size
            ),
        )
        name = quest["archive"]
        source = payload / "cartridges" / name
        victim = damaged / "cartridges" / name
        victim.unlink()
        expect_failure(
            lambda: check_payload(damaged, originals, quests),
            "unexpected or missing cartridge",
        )
        shutil.copyfile(source, victim)
        victim.write_bytes(victim.read_bytes() + b"changed")
        expect_failure(
            lambda: check_payload(damaged, originals, quests), "changed quest checksum"
        )
        for change, fragment in [
            (
                lambda name, binary: (
                    (name, binary + b"changed")
                    if name == "main.lua"
                    else (name, binary)
                ),
                "changed original quest file",
            ),
            (
                lambda name, binary: None if name == "LICENSE" else (name, binary),
                "missing original GPL LICENSE in quest",
            ),
            (
                lambda name, binary: (
                    "data/quest.dat" if name == "quest.dat" else name,
                    binary,
                ),
                "missing root quest metadata",
            ),
            (
                lambda name, binary: (
                    None if name == "project_db.dat" else (name, binary)
                ),
                "missing root quest metadata",
            ),
            (
                lambda name, binary: (
                    (name, binary + b"changed") if name == "LICENSE" else (name, binary)
                ),
                "changed original quest file",
            ),
        ]:
            rewrite_quest(source, victim, change)
            update_checksum(damaged, name)
            expect_failure(lambda: check_payload(damaged, originals, quests), fragment)
        rewrite_quest(source, victim, lambda name, binary: (name, binary))
        with zipfile.ZipFile(victim, "a") as archive:
            archive.writestr("unapproved.lua", "extra source")
        update_checksum(damaged, name)
        expect_failure(
            lambda: check_payload(damaged, originals, quests),
            "wrong quest file inventory",
        )
        shutil.copyfile(source, victim)
        shutil.copyfile(payload / "SHA256SUMS", damaged / "SHA256SUMS")
        notices = damaged / "notices" / quest["repository"]
        original_notices = payload / "notices" / quest["repository"]
        for filename in ["LICENSE", "README.md", "project_db.dat"]:
            (notices / filename).write_bytes(b"changed original notice")
            expect_failure(
                lambda: check_payload(damaged, originals, quests),
                "changed original quest notice: " + filename,
            )
            shutil.copyfile(original_notices / filename, notices / filename)
        source_text = (original_notices / "source.txt").read_text()
        for original, fragment in [
            (quest["url"], "missing quest source URL"),
            (quest["outputHash"], "missing quest source pin"),
        ]:
            (notices / "source.txt").write_text(
                source_text.replace(original, "removed")
            )
            expect_failure(lambda: check_payload(damaged, originals, quests), fragment)
        shutil.copyfile(original_notices / "source.txt", notices / "source.txt")
        checksum_lines = (payload / "SHA256SUMS").read_text().splitlines()
        (damaged / "SHA256SUMS").write_text(
            "\n".join(line for line in checksum_lines if not line.endswith("  " + name))
            + "\n"
        )
        expect_failure(
            lambda: check_payload(damaged, originals, quests),
            "incomplete checksum inventory",
        )
        shutil.copyfile(payload / "SHA256SUMS", damaged / "SHA256SUMS")
        credits = (payload / "CREDITS.md").read_text()
        (damaged / "CREDITS.md").write_text(
            "\n".join(
                line
                for line in credits.splitlines()
                if not (line.startswith("| [") and name in line)
            )
        )
        expect_failure(
            lambda: check_payload(damaged, originals, quests),
            "expected credits for two Solarus quests",
        )


def negative_dependency_checks(plugin, payload, fake08_plugin, solarus_plugin):
    with tempfile.TemporaryDirectory() as directory:
        damaged = Path(directory) / "plugin"
        writable_copy(plugin, damaged)
        manifest_path = damaged / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        fake08_native = json.loads((fake08_plugin / "manifest.json").read_text())[
            "files"
        ]["fake08"]
        solarus_manifest = json.loads((solarus_plugin / "manifest.json").read_text())
        # Neither a raw core/engine package nor its executable is a Korri plugin.
        for requires in [
            [],
            [fake08_native],
            [str(solarus_plugin)],
            [str(fake08_plugin)],
            [fake08_native, str(solarus_plugin)],
            [str(fake08_plugin), solarus_manifest["files"]["solarus"]],
            [str(fake08_plugin), solarus_manifest["packages"]["solarus"]],
            [str(solarus_plugin), str(fake08_plugin)],
        ]:
            manifest["requires"] = requires
            manifest_path.write_text(json.dumps(manifest))
            expect_failure(
                lambda: check_plugin(damaged, payload, fake08_plugin, solarus_plugin),
                "missing exact FAKE-08 and Solarus plugin dependencies",
            )


def negative_identity_checks(plugin, payload, fake08_plugin, solarus_plugin):
    with tempfile.TemporaryDirectory() as directory:
        damaged = Path(directory) / "plugin"
        writable_copy(plugin, damaged)
        manifest_path = damaged / "manifest.json"
        original_manifest = manifest_path.read_text()
        for key, value, fragment in [
            ("publisher", {"namespace": "@simonwjackson"}, "wrong publisher"),
            ("ports", {"allowedTCPPorts": [2222]}, "no native services or ports"),
            ("packages", {}, "unexpected runtime package"),
            ("files", {}, "wrong packaged file references"),
        ]:
            manifest = json.loads(original_manifest)
            manifest[key] = value
            manifest_path.write_text(json.dumps(manifest))
            expect_failure(
                lambda: check_plugin(damaged, payload, fake08_plugin, solarus_plugin),
                fragment,
            )
        manifest_path.write_text(original_manifest)
        source_path = damaged / "plugin.ts"
        original_source = source_path.read_text()
        for before, after, fragment in [
            (
                'name = "starter-pack"',
                'name = "pico8-starter-pack"',
                "wrong plugin identity",
            ),
            (
                'title = "Starter pack"',
                'title = "PICO-8 starter pack"',
                "wrong plugin title",
            ),
        ]:
            source_path.write_text(original_source.replace(before, after))
            expect_failure(
                lambda: check_plugin(damaged, payload, fake08_plugin, solarus_plugin),
                fragment,
            )
        source_path.write_text(original_source + "\nexport const games = {}\n")
        expect_failure(
            lambda: check_plugin(damaged, payload, fake08_plugin, solarus_plugin),
            "unexpected plugin contribution",
        )


def expect_failure(action, fragment):
    try:
        action()
    except ValueError as error:
        require(fragment in str(error), "unexpected rejection: " + str(error))
    else:
        raise ValueError("invalid package was accepted: " + fragment)


def main():
    if len(sys.argv) != 7:
        raise SystemExit(
            "usage: check-starter-pack.py PAYLOAD ORIGINAL_FETCHURL_PINS "
            "QUEST_FETCHURL_PINS PLUGIN FAKE08_PLUGIN SOLARUS_PLUGIN"
        )
    payload, pins, quest_pins, plugin, fake08_plugin, solarus_plugin = map(
        Path, sys.argv[1:]
    )
    originals = json.loads(pins.read_text())
    quests = read_quest_originals(json.loads(quest_pins.read_text()))
    check_payload(payload, originals, quests)
    check_plugin(plugin, payload, fake08_plugin, solarus_plugin)
    negative_checks(payload, originals, quests)
    negative_quest_checks(payload, originals, quests)
    negative_dependency_checks(plugin, payload, fake08_plugin, solarus_plugin)
    negative_identity_checks(plugin, payload, fake08_plugin, solarus_plugin)
    print(
        "Verified 25 original cartridge pins and images, two byte-identical upstream quests, "
        "27 checksums, 24 PICO-8 and two Solarus credits, original GPL and source notices, "
        "unchanged Starter pack treaty, exact FAKE-08/Solarus plugin dependencies, "
        "@korri runtime claims, native ELF files and rejection controls."
    )


if __name__ == "__main__":
    main()

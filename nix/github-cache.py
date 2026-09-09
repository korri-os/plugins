#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 nix gh
"""Publish standard signed Nix file caches as GitHub Release assets.

Nix owns cache metadata, closure export and signatures. Only URL changes when
splitting a cache between a NAR release and the shared metadata release.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote, urlsplit


def run(*args):
    return subprocess.check_output(args, text=True, timeout=1800).strip()


def regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"expected a regular file: {path}")
    return path


def metadata(path):
    text = regular(path).read_text()
    fields = {}
    for line in text.splitlines():
        key, separator, value = line.partition(": ")
        if not separator or (key in fields and key != "Sig"):
            raise ValueError(f"invalid Nix metadata: {path.name}")
        fields[key] = value
    if not fields.get("Sig"):
        raise ValueError("cache must be signed by Nix before preparation")
    return text, fields


def https_base(value):
    url = urlsplit(value)
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or any(c.isspace() for c in value)
    ):
        raise ValueError(
            "NAR base must be an HTTPS URL without credentials, query or fragment"
        )
    return value.rstrip("/") + "/"


def digest(path):
    with regular(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def verify_nar(path, fields):
    # FileHash is Nix's compressed-file hash, not the signed NarHash. The
    # consumer still verifies the NAR and its signature with the native importer.
    if path.stat().st_size != int(fields["FileSize"]):
        raise ValueError(f"NAR size mismatch: {path.name}")
    expected = run(
        "nix",
        "hash",
        "convert",
        "--hash-algo",
        "sha256",
        "--to",
        "base16",
        fields["FileHash"],
    )
    if digest(path) != expected:
        raise ValueError(f"NAR hash mismatch: {path.name}")
    if path.stat().st_size >= 2 * 1024**3:
        raise ValueError("GitHub Release assets must be smaller than 2 GiB")


def prepare(cache, output, base):
    base = https_base(base)
    if output.exists():
        raise ValueError("output already exists; do not overwrite a prepared cache")
    records = sorted(cache.glob("*.narinfo"))
    if not records:
        raise ValueError("file cache contains no narinfos")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        staged = Path(temporary) / "prepared"
        nars, notes = staged / "nars", staged / "metadata"
        nars.mkdir(parents=True)
        notes.mkdir()
        shutil.copyfile(regular(cache / "nix-cache-info"), notes / "nix-cache-info")
        for path in records:
            if not re.fullmatch(r"[0-9abcdfghijklmnpqrsvwxyz]{32}\.narinfo", path.name):
                raise ValueError("invalid narinfo filename")
            text, fields = metadata(path)
            # These files came from nix copy, not from a downloaded manifest.
            url = fields["URL"]
            if not re.fullmatch(r"nar/[A-Za-z0-9+._-]+", url) or "/../" in url:
                raise ValueError("expected a local Nix nar/ URL")
            source = cache / url
            if source.parent.is_symlink():
                raise ValueError("NAR directory cannot be a symlink")
            verify_nar(regular(source), fields)
            target = nars / source.name
            if target.exists() and digest(target) != digest(source):
                raise ValueError("conflicting NAR filename")
            shutil.copyfile(source, target)
            # URL is not part of Nix's signed fingerprint. Preserve all other
            # fields byte-for-byte, including every Sig line.
            (notes / path.name).write_text(
                "\n".join(
                    "URL: " + base + source.name if line.startswith("URL: ") else line
                    for line in text.splitlines()
                )
                + "\n"
            )
        staged.rename(output)


def export(cache, key, paths):
    # An output path is an installable in Nix. Reject expressions and flake
    # references here, rather than relying only on device build policy.
    if not paths or any(
        not re.fullmatch(
            r"/nix/store/[0-9abcdfghijklmnpqrsvwxyz]{32}-[A-Za-z0-9+._?=-]+", path
        )
        for path in paths
    ):
        raise ValueError("export requires exact /nix/store output paths")
    if cache.exists():
        raise ValueError("export cache already exists")
    regular(key)
    if key.stat().st_mode & 0o077 or str(key.resolve()).startswith("/nix/store/"):
        raise ValueError("signing key must be private and outside the Nix store")
    destination = (
        cache.resolve().as_uri() + "?secret-key=" + quote(str(key.resolve()), safe="")
    )
    subprocess.run(
        [
            "nix",
            "copy",
            "--max-jobs",
            "0",
            "--option",
            "builders",
            "",
            "--option",
            "fallback",
            "false",
            "--to",
            destination,
            *paths,
        ],
        check=True,
        timeout=1800,
    )


def api(endpoint):
    return json.loads(run("gh", "api", "--hostname", "github.com", endpoint))


def release_records(repo, tag):
    # The by-tag endpoint is for published releases. Drafts require listing.
    found = []
    page = 1
    while True:
        batch = api(f"repos/{repo}/releases?per_page=100&page={page}")
        if not isinstance(batch, list):
            raise ValueError("invalid GitHub release list")
        found.extend(record for record in batch if record["tag_name"] == tag)
        if len(batch) < 100:
            break
        page += 1
    if len(found) > 1:
        raise ValueError("multiple releases use the same tag")
    return found


def release(repo, tag):
    found = release_records(repo, tag)
    if not found or type(found[0].get("id")) is not int:
        raise ValueError("expected exactly one release with this tag")
    return found[0]


def assets(repo, release_id):
    result = {}
    page = 1
    while True:
        batch = api(
            f"repos/{repo}/releases/{release_id}/assets?per_page=100&page={page}"
        )
        if not isinstance(batch, list):
            raise ValueError("invalid GitHub asset list")
        for asset in batch:
            if asset["name"] in result:
                raise ValueError("duplicate remote asset name")
            result[asset["name"]] = asset
        if len(batch) < 100:
            return result
        page += 1


def matches(asset, path):
    return (
        asset.get("state") == "uploaded"
        and asset.get("size") == path.stat().st_size
        and asset.get("digest") == "sha256:" + digest(path)
    )


def equivalent_metadata(repo, asset, path):
    if (
        not path.name.endswith(".narinfo")
        or asset.get("state") != "uploaded"
        or not 0 < asset.get("size", 0) <= 64 * 1024
    ):
        return False
    # Keep the first published URL for shared dependencies. Signatures and
    # every other Nix field must match. This is not a new approval or key grant.
    data = subprocess.check_output(
        [
            "gh",
            "api",
            "--hostname",
            "github.com",
            f"repos/{repo}/releases/assets/{asset['id']}",
            "--header",
            "Accept: application/octet-stream",
        ],
        timeout=60,
    )
    if len(data) != asset["size"] or "sha256:" + hashlib.sha256(
        data
    ).hexdigest() != asset.get("digest"):
        raise ValueError("remote metadata digest mismatch")
    remote = data.decode().splitlines()
    local = path.read_text().splitlines()
    remote_urls = [line[5:] for line in remote if line.startswith("URL: ")]
    if len(remote_urls) != 1:
        return False
    https_base(remote_urls[0])
    return [line for line in remote if not line.startswith("URL: ")] == [
        line for line in local if not line.startswith("URL: ")
    ]


def upload_files(repo, tag, paths):
    selected = release(repo, tag)
    identity = selected["id"]
    existing = assets(repo, identity)
    # Detect every collision before the first write. Never --clobber, DELETE,
    # or replace a narinfo with a new location/signature under the same name.
    retained = {}
    for path in paths:
        regular(path)
        if path.name in existing and not matches(existing[path.name], path):
            if not equivalent_metadata(repo, existing[path.name], path):
                raise ValueError(
                    f"remote asset differs: {path.name}; no overwrite allowed"
                )
            retained[path.name] = existing[path.name]
    if len(set(existing) | {p.name for p in paths}) > 1000:
        raise ValueError("release would exceed GitHub's 1,000-asset limit")
    for path in paths:
        if path.name in existing:
            continue
        current = release(repo, tag)
        if current["id"] != identity or current["draft"] != selected["draft"]:
            raise ValueError("release changed during upload")
        if current.get("immutable"):
            raise ValueError("release is immutable and lacks a required asset")
        raw = run(
            "gh",
            "api",
            "--hostname",
            "github.com",
            "--method",
            "POST",
            f"https://uploads.github.com/repos/{repo}/releases/{identity}/assets?name={quote(path.name, safe='')}",
            "--header",
            "Content-Type: application/octet-stream",
            "--input",
            str(path),
        )
        if not matches(json.loads(raw), path):
            raise ValueError(
                "GitHub upload digest mismatch; inspect the partial release"
            )
    if release(repo, tag)["id"] != identity:
        raise ValueError("release changed after upload")
    stored = assets(repo, identity)
    for path in paths:
        if path.name in retained:
            # Download counters can change during publication. They are not
            # asset identity or integrity fields.
            valid = all(
                stored.get(path.name, {}).get(key) == retained[path.name].get(key)
                for key in ("id", "name", "state", "size", "digest")
            )
        else:
            valid = path.name in stored and matches(stored[path.name], path)
        if not valid:
            raise ValueError("uploaded assets failed verification")


def validate_destination(repo, tag, cache_tag):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or any(
        s in (".", "..") for s in repo.split("/")
    ):
        raise ValueError("invalid GitHub repository")
    if (
        any(
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", value)
            for value in (tag, cache_tag)
        )
        or tag == cache_tag
    ):
        raise ValueError("use distinct bounded NAR and cache tags")


def upload(prepared, repo, tag, cache_tag, part):
    validate_destination(repo, tag, cache_tag)
    base = f"https://github.com/{repo}/releases/download/{tag}/"
    records = sorted((prepared / "metadata").glob("*.narinfo"))
    if not records:
        raise ValueError("no prepared narinfos")
    nars = {}
    for path in records:
        _, fields = metadata(path)
        if not fields["URL"].startswith(base):
            raise ValueError("narinfo destination differs from the selected release")
        name = fields["URL"][len(base) :]
        if not re.fullmatch(r"[A-Za-z0-9+._-]+", name):
            raise ValueError("invalid NAR asset name")
        nar = prepared / "nars" / name
        verify_nar(regular(nar), fields)
        nars[name] = nar
    if part == "nars":
        upload_files(repo, tag, sorted(nars.values()))
    else:
        payload_release = release(repo, tag)
        if payload_release["draft"]:
            raise ValueError(
                "publish the verified NAR release before uploading cache metadata"
            )
        remote = assets(repo, payload_release["id"])
        if any(
            name not in remote or not matches(remote[name], path)
            for name, path in nars.items()
        ):
            raise ValueError("public NAR assets do not match the prepared bytes")
        index_release = release(repo, cache_tag)
        if index_release["draft"] or index_release.get("immutable"):
            raise ValueError("cache metadata release must be public and mutable")
        upload_files(
            repo, cache_tag, [prepared / "metadata" / "nix-cache-info", *records]
        )


def combine(output, inputs):
    if output.exists() or not inputs:
        raise ValueError("supply input caches and a new output directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        staged = Path(temporary) / "prepared"
        for kind in ("nars", "metadata"):
            (staged / kind).mkdir(parents=True)
            for source in inputs:
                directory = source / kind
                if directory.is_symlink() or not directory.is_dir():
                    raise ValueError("invalid prepared cache directory")
                for path in sorted(directory.iterdir()):
                    target = staged / kind / path.name
                    regular(path)
                    if target.exists() and digest(target) != digest(path):
                        raise ValueError(f"conflicting prepared file: {path.name}")
                    shutil.copyfile(path, target)
        staged.rename(output)


def publish(prepared, repo, tag, cache_tag, revision):
    validate_destination(repo, tag, cache_tag)
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("supply the exact checked source commit")
    commit = api(f"repos/{repo}/commits/{quote('refs/tags/' + tag, safe='')}")
    if commit["sha"] != revision:
        raise ValueError("NAR tag must point at the checked source commit")
    cache = release(repo, cache_tag)
    if cache["draft"] or cache.get("immutable"):
        raise ValueError("prepare a public mutable cache release first")
    # Do not treat a failed request as an absent release.
    found = release_records(repo, tag)
    if not found:
        run(
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            repo,
            "--verify-tag",
            "--draft",
            "--title",
            tag,
            "--notes",
            f"Prebuilt Nix cache payloads from {revision}. Package paths are in the workflow artifacts.",
        )
    payload = release(repo, tag)
    upload(prepared, repo, tag, cache_tag, "nars")
    if payload["draft"]:
        current = release(repo, tag)
        if current["id"] != payload["id"] or not current["draft"]:
            raise ValueError("NAR release changed before publication")
        run(
            "gh",
            "api",
            "--hostname",
            "github.com",
            "--method",
            "PATCH",
            f"repos/{repo}/releases/{payload['id']}",
            "--field",
            "draft=false",
        )
    # The importer cannot see new metadata until its payload is public and
    # GitHub reports a matching digest for every uploaded file.
    upload(prepared, repo, tag, cache_tag, "metadata")


def build(system, packages, paths_file):
    if system not in ("x86_64-linux", "aarch64-linux"):
        raise ValueError("unsupported build system")
    if not packages or any(
        not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name) for name in packages
    ):
        raise ValueError("select package output names, not Nix expressions or flags")
    paths = run(
        "nix",
        "build",
        "--no-link",
        "--print-out-paths",
        *[f".#packages.{system}.{name}" for name in packages],
    )
    with paths_file.open("x") as target:
        target.write(paths + "\n")


def main():
    parser = argparse.ArgumentParser(prog="korri-cache", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--repo", required=True)
    validate_parser.add_argument("--tag", required=True)
    validate_parser.add_argument("--cache-tag", required=True)
    build_parser = commands.add_parser("build")
    build_parser.add_argument("--system", required=True)
    build_parser.add_argument("--paths-file", type=Path, required=True)
    build_parser.add_argument("packages", nargs="+")
    export_parser = commands.add_parser("export")
    export_parser.add_argument("cache", type=Path)
    export_parser.add_argument("--key-file", type=Path, required=True)
    export_parser.add_argument("paths", nargs="+")
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("cache", type=Path)
    prepare_parser.add_argument("output", type=Path)
    prepare_parser.add_argument("--nar-base-url", required=True)
    combine_parser = commands.add_parser("combine")
    combine_parser.add_argument("output", type=Path)
    combine_parser.add_argument("inputs", type=Path, nargs="+")
    publish_parser = commands.add_parser("publish")
    publish_parser.add_argument("prepared", type=Path)
    publish_parser.add_argument("--repo", required=True)
    publish_parser.add_argument("--tag", required=True)
    publish_parser.add_argument("--cache-tag", required=True)
    publish_parser.add_argument("--revision", required=True)
    upload_parser = commands.add_parser("upload")
    upload_parser.add_argument("prepared", type=Path)
    upload_parser.add_argument("--repo", required=True)
    upload_parser.add_argument("--tag", required=True)
    upload_parser.add_argument("--cache-tag", required=True)
    upload_parser.add_argument("--part", choices=["nars", "metadata"], required=True)
    args = parser.parse_args()
    if args.command == "validate":
        validate_destination(args.repo, args.tag, args.cache_tag)
    elif args.command == "build":
        build(args.system, args.packages, args.paths_file)
    elif args.command == "export":
        export(args.cache, args.key_file, args.paths)
    elif args.command == "prepare":
        prepare(args.cache, args.output, args.nar_base_url)
    elif args.command == "combine":
        combine(args.output, args.inputs)
    elif args.command == "publish":
        publish(args.prepared, args.repo, args.tag, args.cache_tag, args.revision)
    else:
        upload(args.prepared, args.repo, args.tag, args.cache_tag, args.part)


if __name__ == "__main__":
    try:
        main()
    except (
        ValueError,
        KeyError,
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        sys.exit(str(error))

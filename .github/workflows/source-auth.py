#!/usr/bin/env python3
"""Job-scoped GitHub credentials for Nix's daemon and fixed-output fetchers."""

import argparse
import base64
import grp
import json
import netrc
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
import uuid

DIRECTORY = Path("/run/korri-github-source-auth")
HOSTS = ("github.com", "api.github.com", "codeload.github.com")


def write_files(root, token, nix, hosts=HOSTS, origins=None):
    # Actions job tokens are no longer plain alphanumerics (run 39734003897).
    # Accept URL-safe token characters; anything that could break a netrc or
    # Git config line (whitespace, quotes, backslash, comment markers) stays out.
    if not re.fullmatch(r"[A-Za-z0-9_.~+/=-]{20,4096}", token):
        # Report only the length and the non-alphanumeric character classes.
        others = sorted({c for c in token if not c.isalnum()})
        print(
            f"GITHUB_TOKEN format: length {len(token)}, other characters {others!r}",
            file=sys.stderr,
        )
        raise ValueError("GITHUB_TOKEN has an unexpected format")
    # Setup mounts a dedicated tmpfs here first; a test root does not exist yet.
    root.mkdir(mode=0o700, exist_ok=True)
    if any(root.iterdir()):
        raise FileExistsError(f"{root} is not empty")
    credentials = root / "netrc"
    descriptor = os.open(credentials, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(descriptor, "w") as stream:
        for host in hosts:
            stream.write(f"machine {host}\nlogin x-access-token\npassword {token}\n")
    origins = origins or [f"https://{host}/" for host in hosts]
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    descriptor = os.open(
        root / "gitconfig", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400
    )
    with os.fdopen(descriptor, "w") as stream:
        for origin in origins:
            stream.write(
                f'[http "{origin}"]\nextraHeader = Authorization: Basic {basic}\n'
            )
    # Curl-based fetchFromGitHub fetchers do not enable netrc by default.
    (root / "curlrc").write_text(
        "netrc-optional\nnetrc-file = /homeless-shelter/.netrc\n"
    )
    (root / "curlrc").chmod(0o444)
    (root / "nix").symlink_to(Path(nix).resolve())
    # The hook contains code and paths only, never a credential value.
    source = Path(__file__).read_text().split("\n", 1)[1]
    (root / "hook").write_text(f"#!{sys.executable}\n{source}")
    (root / "hook").chmod(0o500)


def github_fixed_output(derivation, hosts):
    if not any(output.get("hash") for output in derivation["outputs"].values()):
        return False
    attributes = derivation.get("structuredAttrs") or derivation.get("env", {})
    urls = attributes.get("urls", [])
    if isinstance(urls, str):
        urls = urls.split()
    urls = [*urls, attributes.get("url", "")]
    for value in urls:
        url = urlsplit(value)
        # Loopback HTTP is solely useful to the authenticated local test server.
        secure = url.scheme == "https" or (
            url.scheme == "http" and url.hostname in ("127.0.0.1", "::1")
        )
        if secure and url.hostname in hosts and not url.username and not url.password:
            return True
    return False


def pre_build(root, derivation, sandbox):
    if not sandbox:
        raise RuntimeError("GitHub source authentication requires Nix sandboxing")
    # This is a read-only store query. --store local avoids recursively calling
    # the daemon from its own pre-build hook. The daemon executes this as root.
    result = subprocess.run(
        [str(root / "nix"), "derivation", "show", "--store", "local", derivation],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Cannot inspect source derivation for credential scope")
    document = json.loads(result.stdout)
    descriptions = document.get("derivations", document)
    hosts = netrc.netrc(str(root / "netrc")).hosts
    description = next(iter(descriptions.values()))
    if github_fixed_output(description, hosts):
        attributes = description.get("structuredAttrs") or description.get("env", {})
        if "nix-prefetch-git" in attributes.get("fetcher", "") and attributes.get(
            "gitConfigFile"
        ) != str(DIRECTORY / "gitconfig"):
            print(
                "Refusing an unconfigured GitHub fetchgit build; this Core dependency must be substituted",
                file=sys.stderr,
            )
            raise RuntimeError("GitHub fetchgit lacks the CI credential path")
        print("extra-sandbox-paths")
        print(f"/homeless-shelter/.netrc={root}/netrc")
        print(f"/homeless-shelter/.curlrc={root}/curlrc")
        print(f"{DIRECTORY}/gitconfig={root}/gitconfig")
        print()


def setup(nix):
    if os.geteuid() != 0:
        raise RuntimeError("Source authentication setup requires runner root")
    token = os.environ["GITHUB_TOKEN"]
    # GITHUB_TOKEN is already masked by Actions. Also register the Basic-auth
    # encoding, without ever putting either form in a command-line argument.
    print(f"::add-mask::{token}", flush=True)
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    print(f"::add-mask::{basic}", flush=True)
    root = DIRECTORY
    if any(character.isspace() for character in str(root)):
        raise ValueError("Runner temporary path must not contain whitespace")
    if not Path(nix).is_file():
        raise RuntimeError(
            "Nix must be installed before configuring source authentication"
        )
    features = ["--extra-experimental-features", "nix-command"]
    try:
        shown = subprocess.check_output(
            [nix, *features, "config", "show", "--json"], text=True
        )
    except subprocess.CalledProcessError:
        # Nix before 2.20 names this command `show-config`.
        shown = subprocess.check_output(
            [nix, *features, "show-config", "--json"], text=True
        )
    config = json.loads(shown)
    if config["pre-build-hook"]["value"]:
        raise RuntimeError("Refusing to replace an existing Nix pre-build hook")
    if config["sandbox"]["value"] is not True:
        raise RuntimeError("GitHub source authentication requires Nix sandboxing")
    group = grp.getgrnam("nixbld")
    # Nix executes the hook from this directory. Runner image
    # ubuntu24/20261111.127 mounts /run noexec, and Nix then reports only that
    # the hook "failed with exit code 1" (dry run 43888141736). A dedicated tmpfs
    # keeps the credentials in memory and lets the hook run, whatever /run's
    # own mount options are.
    root.mkdir(mode=0o700)
    subprocess.run(
        [
            "mount",
            "-t",
            "tmpfs",
            "-o",
            "mode=0700,nosuid,nodev,size=1m",
            "korri-github-source-auth",
            str(root),
        ],
        check=True,
    )
    if os.statvfs(root).f_flag & os.ST_NOEXEC:
        raise RuntimeError("Nix cannot execute a hook from a noexec mount")
    write_files(root, token, nix)
    os.chown(root, 0, group.gr_gid)
    root.chmod(0o711)
    # Nix's client-side flake fetcher also reads netrc-file. The invoking
    # runner already owns this job token; nixbld needs read-only sandbox access.
    owner = int(os.environ["SUDO_UID"])
    for name in ("netrc", "gitconfig"):
        os.chown(root / name, owner, group.gr_gid)
        (root / name).chmod(0o440)
    # Only paths enter NIX_CONFIG/GITHUB_ENV. The token stays outside the checkout
    # and store, in /run, until an always() cleanup step removes it.
    settings = (
        os.environ.get("NIX_CONFIG", "").rstrip()
        + "\n"
        + "\n".join(
            [
                f"pre-build-hook = {root}/hook",
                f"netrc-file = {root}/netrc",
            ]
        )
        + "\n"
    )
    delimiter = "SOURCE_AUTH_" + uuid.uuid4().hex
    with Path(os.environ["GITHUB_ENV"]).open("a") as stream:
        stream.write(f"NIX_CONFIG<<{delimiter}\n{settings}{delimiter}\n")
    print(
        "Configured job-scoped GitHub source authentication; credential values are masked."
    )


def erase(root):
    """Overwrite every regular file under root with zeros, then remove the tree.

    A process that still holds a file open, or has its current directory in
    root, can then read neither the token nor any other credential file.
    """
    for directory, subdirectories, files in os.walk(root, topdown=False):
        for name in files:
            path = Path(directory) / name
            # The nix entry is a symlink into the store: remove the link only.
            if not path.is_symlink() and path.is_file():
                path.chmod(0o600)
                size = path.stat().st_size
                with path.open("r+b") as stream:
                    stream.write(bytes(size))
                    stream.flush()
                    os.fsync(stream.fileno())
            path.unlink()
        for name in subdirectories:
            (Path(directory) / name).rmdir()


def cleanup(root=DIRECTORY):
    if root.is_mount():
        # Erase while the dedicated tmpfs is still mounted. A lazy unmount only
        # detaches it, and a process inside it could read what it still held.
        erase(root)
        unmounted = subprocess.run(
            ["umount", str(root)],
            capture_output=True,
            text=True,
            check=False,
            # The busy test below reads util-linux's untranslated message.
            env=os.environ | {"LC_ALL": "C"},
        )
        if unmounted.returncode:
            if "busy" not in unmounted.stderr:
                raise RuntimeError("Cannot unmount the source authentication tmpfs")
            # A process still has its current directory or a file there. The
            # tmpfs is already empty; detach it and let the kernel free it.
            subprocess.run(["umount", "--lazy", str(root)], check=True)
    if root.exists():
        erase(root)
        root.rmdir()
    removed = {f"pre-build-hook = {root}/hook", f"netrc-file = {root}/netrc"}
    settings = (
        "\n".join(
            line
            for line in os.environ.get("NIX_CONFIG", "").splitlines()
            if line not in removed
        )
        + "\n"
    )
    delimiter = "SOURCE_AUTH_" + uuid.uuid4().hex
    with Path(os.environ["GITHUB_ENV"]).open("a") as stream:
        stream.write(f"NIX_CONFIG<<{delimiter}\n{settings}{delimiter}\n")
    print("Removed job-scoped source credentials.")


def main():
    if len(sys.argv) == 3 and sys.argv[1].endswith(".drv"):
        pre_build(Path(__file__).resolve().parent, sys.argv[1], sys.argv[2])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("setup", "cleanup"))
    parser.add_argument("--nix", help="Installed Nix executable; setup only")
    args = parser.parse_args()
    if args.operation == "setup":
        setup(args.nix)
    else:
        cleanup()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Never echo configuration, fetched data, subprocess output or token.
        # Setup reports the exception type and the failing line so a CI failure
        # is diagnosable; the hook path stays silent.
        print("GitHub source authentication setup/hook failed", file=sys.stderr)
        if len(sys.argv) > 1 and sys.argv[1] in ("setup", "cleanup"):
            trace = error.__traceback__
            while trace.tb_next is not None:
                trace = trace.tb_next
            print(
                f"{type(error).__name__} at source-auth.py line {trace.tb_lineno}",
                file=sys.stderr,
            )
        raise SystemExit(1) from None

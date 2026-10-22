#!/usr/bin/env python3
"""Test credential scoping and an actual daemon-sandboxed authenticated fetchgit."""

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("source_auth", HERE / "source-auth.py")
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)


def run(*command, **kwargs):
    return subprocess.run(
        command, text=True, capture_output=True, check=False, **kwargs
    )


class SourceAuthTests(unittest.TestCase):
    @unittest.skipUnless("--integration" in sys.argv, "requires local Nix daemon")
    def test_ci_build_requires_the_canonical_output_path(self):
        publisher = HERE.parents[1]
        pkgs = run(
            "nix",
            "eval",
            "--raw",
            "--impure",
            "--expr",
            f"(builtins.getFlake {json.dumps(str(publisher))}).inputs.nixpkgs.outPath",
        ).stdout.strip()
        system = run(
            "nix", "eval", "--raw", "--impure", "--expr", "builtins.currentSystem"
        ).stdout.strip()
        with tempfile.TemporaryDirectory(prefix="ci-output-equality-") as temporary:
            root = Path(temporary)
            for same in (True, False):
                selected = "canonical" if same else "changed"
                (root / "flake.nix").write_text(f'''{{
                    inputs.nixpkgs.url = "path:{pkgs}";
                    outputs = {{ self, nixpkgs }}: let
                      pkgs = import nixpkgs {{ system = "{system}"; }};
                      canonical = pkgs.runCommand "ci-output-equality" {{}} "touch $out";
                      changed = pkgs.runCommand "ci-output-changed" {{}} "touch $out";
                    in {{ packages.{system}.fixture = canonical;
                          ci.packages.{system}.fixture = {selected}; }};
                }}''')
                paths = root / f"paths-{same}.txt"
                result = subprocess.run(
                    [
                        sys.executable,
                        str(publisher / "nix/github-cache.py"),
                        "build",
                        "--ci-source-auth",
                        "--system",
                        system,
                        "--paths-file",
                        str(paths),
                        "fixture",
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if same:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(Path(paths.read_text().strip()).exists())
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("changes output path", result.stderr)
                    self.assertFalse(paths.exists())

    def test_scope_is_fixed_output_and_exact_credential_host(self):
        def description(url, fixed=True):
            return {
                "outputs": {"out": {"hash": "sha256-pinned"} if fixed else {}},
                "structuredAttrs": {"url": url},
            }

        for host in auth.HOSTS:
            self.assertTrue(
                auth.github_fixed_output(
                    description(f"https://{host}/repo"), auth.HOSTS
                )
            )
        for url in [
            "https://example.com/repo",
            "https://github.com.evil.invalid/repo",
            "http://github.com/repo",
            "https://user:password@github.com/repo",
        ]:
            self.assertFalse(auth.github_fixed_output(description(url), auth.HOSTS))
        self.assertFalse(
            auth.github_fixed_output(
                description("https://github.com/repo", False), auth.HOSTS
            )
        )
        self.assertTrue(
            auth.github_fixed_output(
                {
                    "outputs": {"out": {"hash": "pinned"}},
                    "env": {"urls": "https://github.com/archive.tar.gz"},
                },
                auth.HOSTS,
            )
        )

    def test_secret_is_only_in_private_native_netrc(self):
        with tempfile.TemporaryDirectory(prefix="source-auth-unit-") as temporary:
            root = Path(temporary) / "auth"
            token = secrets.token_hex(24)
            auth.write_files(root, token, shutil.which("nix"))
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
            self.assertEqual((root / "netrc").stat().st_mode & 0o777, 0o400)
            self.assertEqual((root / "gitconfig").stat().st_mode & 0o777, 0o400)
            self.assertEqual(
                set(auth.netrc.netrc(str(root / "netrc")).hosts), set(auth.HOSTS)
            )
            for name in ("hook", "curlrc"):
                self.assertNotIn(token, (root / name).read_text())
            with self.assertRaises(FileExistsError):
                auth.write_files(root, token, shutil.which("nix"))
            with self.assertRaises(ValueError):
                auth.write_files(
                    Path(temporary) / "invalid", "bad\ncredential", shutil.which("nix")
                )

    @unittest.skipUnless(
        "--integration" in sys.argv,
        "requires trusted local Nix daemon, Git and setfacl",
    )
    def test_real_fetchgit_authenticates_without_changing_or_leaking_outputs(self):
        with tempfile.TemporaryDirectory(prefix="source-auth-fod-") as temporary:
            work = Path(temporary)
            repository = work / "http/repository.git"
            checkout = work / "checkout"
            expected = work / "expected"
            checkout.mkdir()
            expected.mkdir()
            payload = secrets.token_hex(16) + "\n"
            (checkout / "content.txt").write_text(payload)
            (expected / "content.txt").write_text(payload)
            repository.parent.mkdir()
            for command in [
                ("git", "init", str(checkout)),
                ("git", "-C", str(checkout), "add", "content.txt"),
                (
                    "git",
                    "-C",
                    str(checkout),
                    "-c",
                    "user.name=Source fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "commit",
                    "-m",
                    "fixture",
                ),
                ("git", "clone", "--bare", str(checkout), str(repository)),
            ]:
                result = run(*command)
                self.assertEqual(result.returncode, 0, result.stderr)
            revision = run(
                "git", "-C", str(checkout), "rev-parse", "HEAD"
            ).stdout.strip()
            token = secrets.token_hex(24)
            encoded = base64.b64encode(f"x-access-token:{token}".encode()).decode()
            counters = {"authorized": 0, "denied": 0}
            git = shutil.which("git")

            class AuthenticatedGitHandler(BaseHTTPRequestHandler):
                def log_message(self, *_):
                    pass

                def do_GET(self):
                    self.respond()

                def do_POST(self):
                    self.respond()

                def respond(self):
                    if self.headers.get("Authorization") != f"Basic {encoded}":
                        counters["denied"] += 1
                        self.send_error(403, "Authentication required")
                        return
                    counters["authorized"] += 1
                    if self.path == "/payload":
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(payload.encode())))
                        self.end_headers()
                        self.wfile.write(payload.encode())
                        return
                    uri = urlsplit(self.path)
                    data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                    env = os.environ | {
                        "GIT_PROJECT_ROOT": str(repository.parent),
                        "GIT_HTTP_EXPORT_ALL": "1",
                        "PATH_INFO": uri.path,
                        "QUERY_STRING": uri.query,
                        "REQUEST_METHOD": self.command,
                        "REMOTE_USER": "source-fixture",
                        "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                        "CONTENT_LENGTH": str(len(data)),
                    }
                    response = subprocess.run(
                        [git, "http-backend"],
                        input=data,
                        capture_output=True,
                        env=env,
                        check=True,
                    ).stdout
                    headers, _, body = response.partition(b"\r\n\r\n")
                    parsed = [
                        line.decode().split(":", 1) for line in headers.splitlines()
                    ]
                    status = next(
                        (
                            int(value.strip().split()[0])
                            for name, value in parsed
                            if name == "Status"
                        ),
                        200,
                    )
                    self.send_response(status)
                    for name, value in parsed:
                        if name.lower() not in ("status", "content-length"):
                            self.send_header(name, value.strip())
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

            server = ThreadingHTTPServer(("127.0.0.1", 0), AuthenticatedGitHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            url = f"http://127.0.0.1:{server.server_port}/repository.git"
            root = work / "auth"
            auth.write_files(
                root,
                token,
                shutil.which("nix"),
                hosts=("127.0.0.1",),
                origins=(f"http://127.0.0.1:{server.server_port}/",),
            )
            # The fixture owner can grant this ACL without changing host config
            # or using sudo. CI setup uses the same nixbld group via chgrp.
            for directory in (work, root):
                traverse = run("setfacl", "-m", "g:nixbld:--x,m::--x", str(directory))
                self.assertEqual(traverse.returncode, 0, traverse.stderr)
                directory.chmod(0o711)
            for name in ("netrc", "gitconfig"):
                acl = run("setfacl", "-m", "g:nixbld:r--,m::r--", str(root / name))
                self.assertEqual(acl.returncode, 0, acl.stderr)
            publisher = HERE.parents[1]
            pkgs = run(
                "nix",
                "eval",
                "--raw",
                "--impure",
                "--expr",
                f"(builtins.getFlake {json.dumps(str(publisher))}).inputs.nixpkgs.outPath",
            )
            self.assertEqual(pkgs.returncode, 0, pkgs.stderr)
            hashed = run("nix", "hash", "path", str(expected))
            self.assertEqual(hashed.returncode, 0, hashed.stderr)
            expression = work / "fetch.nix"
            expression.write_text(f'''let pkgs = import {pkgs.stdout.strip()} {{ system = builtins.currentSystem; }};
                in pkgs.fetchgit {{ url = {json.dumps(url)}; rev = {json.dumps(revision)};
                hash = {json.dumps(hashed.stdout.strip())};
                gitConfigFile = "{auth.DIRECTORY}/gitconfig";
                preFetch = ''test "$HOME" = /homeless-shelter; test "$(id -u)" != 0;
                if test -e /homeless-shelter/.netrc; then test -r /homeless-shelter/.netrc || (echo credential-not-readable; exit 1); fi''; }}''')
            common = [
                "nix",
                "build",
                "--no-link",
                "--print-out-paths",
                "--option",
                "sandbox",
                "true",
                "--option",
                "builders",
                "",
                "--option",
                "netrc-file",
                "/dev/null",
                "--file",
                str(expression),
            ]
            denied = run(*common, "--option", "pre-build-hook", "", timeout=180)
            self.assertNotEqual(denied.returncode, 0)
            self.assertIn("403", denied.stderr)
            unconfigured = work / "unconfigured.nix"
            unconfigured.write_text(
                expression.read_text().replace(
                    f'gitConfigFile = "{auth.DIRECTORY}/gitconfig";', ""
                )
            )
            requests_before_refusal = dict(counters)
            refused = run(
                "nix",
                "build",
                "--no-link",
                "--option",
                "pre-build-hook",
                str(root / "hook"),
                "--file",
                str(unconfigured),
                timeout=180,
            )
            self.assertNotEqual(refused.returncode, 0)
            # Nix hides the pre-build hook's stderr. Its failed exit and the
            # unchanged server counters prove refusal happened before fetching.
            self.assertIn(
                f'program "{root / "hook"}" failed with exit code 1', refused.stderr
            )
            self.assertEqual(counters, requests_before_refusal)
            accepted = run(
                *common, "--option", "pre-build-hook", str(root / "hook"), timeout=180
            )
            # Never include a possibly sensitive subprocess diagnostic in an assertion.
            diagnostic = accepted.stderr.replace(token, "<redacted>").replace(
                encoded, "<redacted>"
            )
            self.assertEqual(
                accepted.returncode,
                0,
                "authenticated daemon fetchgit failed: " + diagnostic,
            )
            output = Path(accepted.stdout.strip())
            self.assertEqual((output / "content.txt").read_text(), payload)
            self.assertGreater(counters["authorized"], 0)
            self.assertGreater(counters["denied"], 0)
            derivation = run(
                "nix", "eval", "--raw", "--file", str(expression), "drvPath"
            )
            self.assertEqual(derivation.returncode, 0, derivation.stderr)
            description = run("nix", "derivation", "show", derivation.stdout.strip())
            log = run("nix", "log", derivation.stdout.strip())
            dump = subprocess.check_output(["nix-store", "--dump", str(output)])
            for value in (token.encode(), encoded.encode()):
                self.assertNotIn(value, dump)
                for text in (
                    denied.stdout,
                    denied.stderr,
                    accepted.stdout,
                    accepted.stderr,
                    description.stdout,
                    description.stderr,
                    log.stdout,
                    log.stderr,
                ):
                    self.assertNotIn(value.decode(), text)
            curl_expression = work / "curl.nix"
            flat_hash = run("nix", "hash", "file", str(expected / "content.txt"))
            self.assertEqual(flat_hash.returncode, 0, flat_hash.stderr)
            curl_expression.write_text(f"""let pkgs = import {pkgs.stdout.strip()} {{ system = builtins.currentSystem; }};
                in pkgs.fetchurl {{ url = "http://127.0.0.1:{server.server_port}/payload";
                hash = {json.dumps(flat_hash.stdout.strip())}; }}""")
            fetched = run(
                "nix",
                "build",
                "--no-link",
                "--print-out-paths",
                "--option",
                "pre-build-hook",
                str(root / "hook"),
                "--file",
                str(curl_expression),
                timeout=180,
            )
            self.assertEqual(
                fetched.returncode, 0, "authenticated daemon fetchurl failed"
            )
            self.assertEqual(Path(fetched.stdout.strip()).read_text(), payload)
            for secret in (token, encoded):
                self.assertNotIn(secret, fetched.stdout + fetched.stderr)
            normal = work / "normal.nix"
            normal.write_text(f"""let pkgs = import {pkgs.stdout.strip()} {{ system = builtins.currentSystem; }};
                in pkgs.runCommand "source-auth-not-mounted-{secrets.token_hex(4)}" {{}} ''
                test ! -e /homeless-shelter/.netrc
                test ! -e {auth.DIRECTORY}/gitconfig
                touch "$out"
                '' """)
            isolated = run(
                "nix",
                "build",
                "--no-link",
                "--option",
                "pre-build-hook",
                str(root / "hook"),
                "--file",
                str(normal),
                timeout=180,
            )
            self.assertEqual(
                isolated.returncode, 0, "ordinary build received source credentials"
            )


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])

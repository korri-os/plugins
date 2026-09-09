#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 nix openssl bash
"""Exercise the publisher with real signed Nix caches, HTTPS and empty stores."""

import functools
import http.server
import hashlib
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest

SCRIPT = Path(__file__).with_name("github-cache.py")


def run(*args, env=None, succeeds=True):
    result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=120)
    if succeeds and result.returncode:
        raise AssertionError((args, result.stdout, result.stderr))
    if not succeeds and not result.returncode:
        raise AssertionError((args, "unexpected success"))
    return result


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class SignedCache(unittest.TestCase):
    def check_uploads(self, root, exported, env):
        fixture = root / "github"
        fixture.mkdir()
        fixture_state = fixture / "state.json"
        fixture_state.write_text(
            json.dumps(
                {
                    "releases": [
                        {
                            "id": 1,
                            "tag_name": "build-1",
                            "draft": True,
                            "immutable": False,
                        },
                        {
                            "id": 2,
                            "tag_name": "cache",
                            "draft": False,
                            "immutable": False,
                        },
                        {
                            "id": 3,
                            "tag_name": "build-2",
                            "draft": False,
                            "immutable": False,
                        },
                    ],
                    "assets": [],
                }
            )
        )
        commands = root / "commands"
        commands.mkdir()
        # The adapter is a real subprocess with durable, configurable outcomes.
        gh = commands / "gh"
        gh.write_text(
            "#!"
            + sys.executable
            + "\n"
            + Path(__file__).with_name("github-cache-github-fixture.py").read_text()
        )
        gh.chmod(0o755)
        env = dict(
            env, RELEASE_FIXTURE=str(fixture), PATH=str(commands) + ":" + env["PATH"]
        )
        base = "https://github.com/owner/plugins/releases/download/"
        prepared = root / "github-prepared"
        run(
            sys.executable,
            str(SCRIPT),
            "prepare",
            str(exported),
            str(prepared),
            "--nar-base-url",
            base + "build-1/",
            env=env,
        )

        def upload(part, folder=prepared, tag="build-1", succeeds=True):
            return run(
                sys.executable,
                str(SCRIPT),
                "upload",
                str(folder),
                "--repo",
                "owner/plugins",
                "--tag",
                tag,
                "--cache-tag",
                "cache",
                "--part",
                part,
                env=env,
                succeeds=succeeds,
            )

        # Partial upload is resumable, without deleting/replacing any asset.
        state = json.loads(fixture_state.read_text())
        state["fail_after_upload"] = True
        fixture_state.write_text(json.dumps(state))
        upload("nars", succeeds=False)
        state = json.loads(fixture_state.read_text())
        self.assertEqual(len(state["assets"]), 1)
        del state["fail_after_upload"]
        fixture_state.write_text(json.dumps(state))
        upload("nars")
        refused = upload("metadata", succeeds=False)
        self.assertIn("publish", refused.stderr)
        state = json.loads(fixture_state.read_text())
        self.assertFalse(any(a["release"] == 2 for a in state["assets"]))
        before = fixture_state.read_bytes()
        refused = run(
            sys.executable,
            str(SCRIPT),
            "publish",
            str(prepared),
            "--repo",
            "owner/plugins",
            "--tag",
            "build-1",
            "--cache-tag",
            "cache",
            "--revision",
            "2" * 40,
            env=env,
            succeeds=False,
        )
        self.assertIn("checked source", refused.stderr)
        self.assertEqual(before, fixture_state.read_bytes())
        run(
            sys.executable,
            str(SCRIPT),
            "publish",
            str(prepared),
            "--repo",
            "owner/plugins",
            "--tag",
            "build-1",
            "--cache-tag",
            "cache",
            "--revision",
            "1" * 40,
            env=env,
        )
        state = json.loads(fixture_state.read_text())
        self.assertFalse(state["releases"][0]["draft"])
        before = fixture_state.read_bytes()
        upload("metadata")
        self.assertEqual(before, fixture_state.read_bytes())
        # A second batch often shares dependencies. Retain their first signed
        # metadata and URL rather than overwriting or refusing the whole batch.
        another = root / "github-second"
        run(
            sys.executable,
            str(SCRIPT),
            "prepare",
            str(exported),
            str(another),
            "--nar-base-url",
            base + "build-2/",
            env=env,
        )
        upload("nars", another, "build-2")
        before = fixture_state.read_bytes()
        upload("metadata", another, "build-2")
        self.assertEqual(before, fixture_state.read_bytes())
        # First publication also creates and publishes a new draft by ID.
        third = root / "github-third"
        run(
            sys.executable,
            str(SCRIPT),
            "prepare",
            str(exported),
            str(third),
            "--nar-base-url",
            base + "build-3/",
            env=env,
        )
        run(
            sys.executable,
            str(SCRIPT),
            "publish",
            str(third),
            "--repo",
            "owner/plugins",
            "--tag",
            "build-3",
            "--cache-tag",
            "cache",
            "--revision",
            "1" * 40,
            env=env,
        )
        state = json.loads(fixture_state.read_text())
        new_release = next(r for r in state["releases"] if r["tag_name"] == "build-3")
        self.assertFalse(new_release["draft"])
        self.assertTrue(new_release["immutable"])
        # A conflicting remote file stops before writing anything else.
        state = json.loads(fixture_state.read_text())
        first = next(
            a
            for a in state["assets"]
            if a["release"] == 2 and a["name"].endswith(".narinfo")
        )
        text = (
            (fixture / str(first["id"])).read_text().replace("NarSize: ", "NarSize: 9")
        )
        (fixture / str(first["id"])).write_text(text)
        first["digest"] = "sha256:" + hashlib.sha256(text.encode()).hexdigest()
        first["size"] = len(text)
        fixture_state.write_text(json.dumps(state))
        before = fixture_state.read_bytes()
        upload("metadata", succeeds=False)
        self.assertEqual(before, fixture_state.read_bytes())
        # Asset pagination and capacity are checked before the next upload set.
        state = json.loads(fixture_state.read_text())
        state["assets"] = [a for a in state["assets"] if a["release"] != 3]
        state["assets"].extend(
            {"id": i + 1000, "name": f"existing-{i}", "release": 3} for i in range(1000)
        )
        fixture_state.write_text(json.dumps(state))
        before = fixture_state.read_bytes()
        refused = upload("nars", another, "build-2", succeeds=False)
        self.assertIn("1,000", refused.stderr)
        self.assertEqual(before, fixture_state.read_bytes())

    def test_multiple_packages_download_without_a_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env = {k: v for k, v in os.environ.items() if not k.startswith("NIX_")}
            env.update(
                {
                    "HOME": str(root / "home"),
                    "NIX_REMOTE": "local",
                    "NIX_STORE_DIR": str(root / "store"),
                    "NIX_STATE_DIR": str(root / "state"),
                    "NIX_LOG_DIR": str(root / "log"),
                    "NIX_CONF_DIR": str(root / "conf"),
                    "NIX_USER_CONF_FILES": "/dev/null",
                    "XDG_CACHE_HOME": str(root / "cache"),
                    "NIX_CONFIG": "experimental-features = nix-command\nsandbox = false\nbuild-users-group =\nsubstituters =\nmax-jobs = 0\nbuilders =\nfallback = false\nrequire-sigs = true\n",
                }
            )
            for name in ("home", "conf"):
                (root / name).mkdir()
            secret, public = root / "secret", root / "public"
            run(
                "nix-store",
                "--generate-binary-cache-key",
                "test-cache-1",
                str(secret),
                str(public),
                env=env,
            )
            fixture = root / "fixture.nix"
            fixture.write_text("""{ shell, text }: builtins.derivation {
  name = "cache-test"; system = builtins.currentSystem;
  builder = shell; args = [ "-c" "printf '%s' \\\"$text\\\" > \\\"$out\\\"" ];
  inherit text; preferLocalBuild = true; allowSubstitutes = true;
}""")
            paths = []
            for text in ("first plugin", "second plugin"):
                result = run(
                    "nix",
                    "build",
                    "--file",
                    str(fixture),
                    "--argstr",
                    "shell",
                    shutil.which("bash"),
                    "--argstr",
                    "text",
                    text,
                    "--no-link",
                    "--json",
                    "--max-jobs",
                    "1",
                    env=env,
                )
                paths.append(json.loads(result.stdout)[0]["outputs"]["out"])
            unsigned = root / "unsigned"
            run("nix", "copy", "--to", unsigned.as_uri(), *paths, env=env)
            exported = root / "exported"
            run(
                "nix",
                "copy",
                "--to",
                exported.as_uri() + "?secret-key=" + str(secret),
                *paths,
                env=env,
            )
            # A real TLS endpoint hosts the payloads. Nix follows one redirect,
            # as it does for public GitHub Release downloads.
            site = root / "site"
            site.mkdir()
            cert, key = root / "tls.crt", root / "tls.key"
            run(
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                str(key),
                "-out",
                str(cert),
                "-days",
                "1",
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=IP:127.0.0.1",
            )

            class RedirectHandler(Handler):
                def do_GET(self):
                    if self.path.startswith("/download/"):
                        self.send_response(302)
                        self.send_header(
                            "Location", "/nars/" + self.path.rsplit("/", 1)[-1]
                        )
                        self.end_headers()
                    else:
                        super().do_GET()

            server = http.server.ThreadingHTTPServer(
                ("127.0.0.1", 0), functools.partial(RedirectHandler, directory=site)
            )
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            base = f"https://127.0.0.1:{server.server_port}"
            try:
                bad = run(
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(unsigned),
                    str(root / "bad"),
                    "--nar-base-url",
                    base + "/download/",
                    env=env,
                    succeeds=False,
                )
                self.assertIn("signed", bad.stderr)
                run(
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(exported),
                    str(site / "prepared"),
                    "--nar-base-url",
                    base + "/download/",
                    env=env,
                )
                prepared = site / "prepared"
                combined = root / "combined"
                run(
                    sys.executable,
                    str(SCRIPT),
                    "combine",
                    str(combined),
                    str(prepared),
                    str(prepared),
                    env=env,
                )
                self.assertEqual(
                    len(list((combined / "metadata").glob("*.narinfo"))), 2
                )
                shutil.copytree(prepared / "nars", site / "nars")
                metadata = prepared / "metadata"
                self.assertEqual(len(list(metadata.glob("*.narinfo"))), 2)
                for record in metadata.glob("*.narinfo"):
                    original = (exported / record.name).read_text()
                    self.assertEqual(
                        [
                            s
                            for s in record.read_text().splitlines()
                            if s.startswith("Sig:")
                        ],
                        [s for s in original.splitlines() if s.startswith("Sig:")],
                    )
                self.check_uploads(root, exported, env)
                for name in ("store", "state", "log", "cache"):
                    shutil.rmtree(root / name, ignore_errors=True)
                env["NIX_SSL_CERT_FILE"] = str(cert)
                env["NIX_CONFIG"] += (
                    f"substituters = {base}/prepared/metadata\nsubstitute = true\n"
                )
                denied = run(
                    "nix-store", "--realise", paths[0], env=env, succeeds=False
                )
                self.assertIn("not signed", denied.stderr)
                env["NIX_CONFIG"] += (
                    "trusted-public-keys = " + public.read_text().strip() + "\n"
                )
                for path, text in zip(paths, ("first plugin", "second plugin")):
                    run("nix-store", "--realise", path, env=env)
                    self.assertEqual(Path(path).read_text(), text)
                # Removing downloaded outputs and corrupting the actual NAR
                # proves the native importer still checks bytes after URL rewrite.
                for name in ("store", "state", "log", "cache"):
                    shutil.rmtree(root / name, ignore_errors=True)
                for nar in (site / "nars").iterdir():
                    nar.write_bytes(b"corrupt payload")
                run("nix-store", "--realise", paths[0], env=env, succeeds=False)
                missing = run(
                    "nix",
                    "build",
                    "--file",
                    str(fixture),
                    "--argstr",
                    "shell",
                    shutil.which("bash"),
                    "--argstr",
                    "text",
                    "not cached",
                    "--no-link",
                    env=env,
                    succeeds=False,
                )
                self.assertRegex(
                    missing.stderr,
                    "Unable to start any build|local builds are disabled",
                )
            finally:
                server.shutdown()
                thread.join()
                server.server_close()


class CliInputs(unittest.TestCase):
    def test_export_refuses_build_requests(self):
        for value in (".#korri-tailscale", "github:owner/repo", "--impure"):
            result = run(
                sys.executable,
                str(SCRIPT),
                "export",
                "/tmp/unused",
                "--key-file",
                "/tmp/absent",
                "--",
                value,
                succeeds=False,
            )
            self.assertIn("exact /nix/store", result.stderr)

    def test_prepare_refuses_insecure_locations(self):
        for value in (
            "http://example.com/nars/",
            "https://user:secret@example.com/",
            "https://example.com/?token=secret",
        ):
            result = run(
                sys.executable,
                str(SCRIPT),
                "prepare",
                "/tmp/absent",
                "/tmp/unused",
                "--nar-base-url",
                value,
                succeeds=False,
            )
            self.assertIn("HTTPS URL", result.stderr)

    def test_build_refuses_expression_inputs(self):
        result = run(
            sys.executable,
            str(SCRIPT),
            "build",
            "--system",
            "aarch64-linux",
            "--paths-file",
            "/tmp/unused",
            "github:other/repo",
            succeeds=False,
        )
        self.assertIn("package output names", result.stderr)

    def test_tags_are_batch_names_not_plugin_names(self):
        run(
            sys.executable,
            str(SCRIPT),
            "validate",
            "--repo",
            "owner/plugins",
            "--tag",
            "release-2026-09",
            "--cache-tag",
            "cache",
        )
        run(
            sys.executable,
            str(SCRIPT),
            "validate",
            "--repo",
            "owner/plugins",
            "--tag",
            "cache",
            "--cache-tag",
            "cache",
            succeeds=False,
        )


if __name__ == "__main__":
    unittest.main()

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
import tarfile
import tempfile
import threading
import unittest

SCRIPT = Path(__file__).with_name("github-cache.py")
# Run the real publisher CLI, but record each time.sleep request made by the
# publisher on stderr instead of waiting. Other callers, such as subprocess's
# own wait loop, keep the real sleep.
RECORDED_SLEEP = """
import runpy, sys, time
script, wait = sys.argv[1], time.sleep
def sleep(seconds):
    if sys._getframe(1).f_code.co_filename != script:
        return wait(seconds)
    print(f'slept {seconds}', file=sys.stderr)
time.sleep = sleep
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name='__main__')
"""


def sleeps(result):
    return [
        float(line.removeprefix("slept "))
        for line in result.stderr.splitlines()
        if line.startswith("slept ")
    ]


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
    def check_upstreams(self, root, site, base, cert, secret, public, fixture, env):
        env = dict(env, NIX_SSL_CERT_FILE=str(cert))
        env["NIX_CONFIG"] += (
            "trusted-public-keys = " + public.read_text().strip() + "\n"
        )

        def build(text, dependencies=()):
            return run(
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
                "--print-out-paths",
                "--max-jobs",
                "1",
                "--impure",
                "--arg",
                "dependencies",
                "[ "
                + " ".join(
                    '(builtins.storePath "' + path + '")' for path in dependencies
                )
                + " ]",
                env=env,
            ).stdout.strip()

        source = root / "dependency"
        source.write_text("upstream dependency")
        # Existing content-addressed inputs still require an actual trusted
        # signature. No content-address conversion is performed by prepare.
        dependency = run(
            "nix", "store", "add-file", str(source), env=env
        ).stdout.strip()
        missing_text = f"genuinely missing dependency {dependency}"
        missing = build(missing_text, [dependency])
        wrappers = [
            build(f"plugin {i}: {dependency} {missing}", [dependency, missing])
            for i in range(2)
        ]
        closure = root / "closure"
        upstream = site / "upstream"
        for cache, paths in ((closure, wrappers), (upstream, [dependency])):
            run(
                "nix",
                "copy",
                "--to",
                cache.as_uri() + "?secret-key=" + str(secret),
                *paths,
                env=env,
            )
        dep_note = next(upstream.glob("*.narinfo"))
        dep_text = dep_note.read_text()
        self.assertIn("CA: ", dep_text)
        dep_nar = next(s[5:] for s in dep_text.splitlines() if s.startswith("URL: "))
        self.assertEqual(len(list(closure.glob("*.narinfo"))), 4)
        counter = 0

        def prepare(*urls, succeeds=True, environment=env):
            nonlocal counter
            counter += 1
            output = site / f"filtered-{counter}"
            result = run(
                sys.executable,
                str(SCRIPT),
                "prepare",
                str(closure),
                str(output),
                "--nar-base-url",
                base + f"/filtered-{counter}/nars/",
                *[arg for url in urls for arg in ("--upstream-cache", url)],
                env=environment,
                succeeds=succeeds,
            )
            if not succeeds:
                self.assertFalse(output.exists(), result.stderr)
            return output, result

        # A missing cache must not turn every dependency into a genuine miss.
        _, result = prepare(base + "/upstream", base + "/absent", succeeds=False)
        self.assertIn("404", result.stderr)
        empty = site / "empty"
        empty.mkdir()
        shutil.copyfile(upstream / "nix-cache-info", empty / "nix-cache-info")
        # A healthy empty cache can miss paths supplied by a second cache.
        filtered, _ = prepare(base + "/empty", base + "/upstream")
        expected = {
            Path(p).name.split("-", 1)[0] + ".narinfo" for p in [*wrappers, missing]
        }
        self.assertEqual(
            {p.name for p in (filtered / "metadata").glob("*.narinfo")}, expected
        )
        self.assertFalse((filtered / "nars" / Path(dep_nar).name).exists())
        self.assertEqual(len(list((filtered / "nars").iterdir())), 3)
        with tarfile.open(filtered / "offline-metadata.tar.gz", "r:gz") as bundle:
            records = {member.name: bundle.extractfile(member).read() for member in bundle}
        self.assertEqual(set(records), {"nix-cache-info", *(p.name for p in closure.glob("*.narinfo"))})
        self.assertEqual(records[dep_note.name], dep_text.encode())
        self.assertEqual(records["nix-cache-info"], (closure / "nix-cache-info").read_bytes())
        complete, _ = prepare()
        self.assertEqual(
            (filtered / "offline-metadata.tar.gz").read_bytes(),
            (complete / "offline-metadata.tar.gz").read_bytes(),
        )
        self.assertEqual(len(list((complete / "metadata").glob("*.narinfo"))), 4)
        empty_only, _ = prepare(base + "/empty")
        self.assertEqual(len(list((empty_only / "metadata").glob("*.narinfo"))), 4)
        info = empty / "nix-cache-info"
        valid_info = info.read_text()
        for text in (
            "",
            "<html>not a cache</html>\n",
            "StoreDir: /wrong\n",
            valid_info + "Priority: invalid\n",
            "x" * (64 * 1024 + 1),
        ):
            info.write_text(text)
            prepare(base + "/empty", succeeds=False)
        info.write_text(valid_info)

        # Two package wrappers reuse an upstream dependency from an empty store.
        for name in ("store", "state", "log", "cache"):
            shutil.rmtree(root / name, ignore_errors=True)
        env["NIX_CONFIG"] += (
            f"substituters = {base}/{filtered.name}/metadata {base}/upstream\n"
            "substitute = true\n"
        )
        for i, wrapper in enumerate(wrappers):
            run("nix-store", "--realise", wrapper, env=env)
            self.assertEqual(
                Path(wrapper).read_text(), f"plugin {i}: {dependency} {missing}"
            )
        self.assertEqual(Path(dependency).read_text(), "upstream dependency")
        self.assertEqual(Path(missing).read_text(), missing_text)
        run(
            "nix",
            "copy",
            "--to",
            upstream.as_uri() + "?secret-key=" + str(secret),
            missing,
            env=env,
        )
        wrappers_only, _ = prepare(base + "/upstream")
        self.assertEqual(
            {p.name for p in (wrappers_only / "metadata").glob("*.narinfo")},
            {Path(p).name.split("-", 1)[0] + ".narinfo" for p in wrappers},
        )
        self.assertEqual(len(list((wrappers_only / "nars").iterdir())), 2)

        # cache.nixos.org omits References for dependency-free outputs (for
        # example xgcc-14.3.0-libgcc). Nix treats omission as the empty set.
        self.assertIn("References: \n", dep_text)
        dep_note.write_text(dep_text.replace("References: \n", ""))
        prepare(base + "/upstream")
        dep_note.write_text(dep_text)

        # Every configured upstream is checked, even after another has the path.
        for code in (401, 403, 429, 500, 503):
            for endpoint in ("status", "path-status"):
                _, result = prepare(
                    base + "/upstream", base + f"/{endpoint}/{code}", succeeds=False
                )
                self.assertIn(str(code), result.stderr)
        prepare(base + "/disconnect", succeeds=False)
        prepare(base + "/downgrade", succeeds=False)
        untrusted = dict(env, NIX_CONFIG=env["NIX_CONFIG"] + "trusted-public-keys =\n")
        _, result = prepare(base + "/upstream", succeeds=False, environment=untrusted)
        self.assertIn("untrusted", result.stderr)
        wrong_tls = dict(env, NIX_SSL_CERT_FILE="/dev/null")
        prepare(base + "/upstream", succeeds=False, environment=wrong_tls)
        for before, after in (
            ("NarSize: ", "NarSize: 9"),
            ("NarHash: sha256:", "NarHash: sha256:0"),
            ("References: ", "References: " + Path(missing).name + " "),
            ("StorePath: ", "StorePath: /wrong"),
            ("Sig: test-cache-1:", "Sig: unknown-key:"),
            ("URL: ", "URL: http://insecure.example/"),
            ("CA: ", "CA: malformed:"),
        ):
            dep_note.write_text(dep_text.replace(before, after))
            prepare(base + "/upstream", succeeds=False)
        signature = next(s for s in dep_text.splitlines() if s.startswith("Sig: "))
        signature_prefix, signature_bytes = signature.rsplit(":", 1)
        corrupt_signature = (
            signature_prefix
            + ":"
            + ("A" if signature_bytes[0] != "A" else "B")
            + signature_bytes[1:]
        )
        dep_note.write_text(dep_text.replace(signature, corrupt_signature))
        _, result = prepare(base + "/upstream", succeeds=False)
        self.assertIn("untrusted", result.stderr)
        for text in (
            "not narinfo\n",
            dep_text + "NarSize: 1\n",
            dep_text.replace("Sig: ", "Unknown: "),
            "x" * (64 * 1024 + 1),
        ):
            dep_note.write_text(text)
            prepare(base + "/upstream", succeeds=False)
        dep_note.write_text(dep_text)
        # No dependency payloads need to be downloaded by prepare itself.
        (upstream / dep_nar).unlink()
        prepare(base + "/upstream")

    def check_uploads(self, root, exported, env, cache_url):
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
        remote = root / "index.git"
        run("git", "init", "--bare", str(remote), env=env)
        seed = root / "index-seed"
        run("git", "init", "-b", "cache-index", str(seed), env=env)
        (seed / ".nojekyll").touch()
        run("git", "-C", str(seed), "add", ".", env=env)
        run("git", "-C", str(seed), "-c", "user.name=test", "-c", "user.email=test@example.org", "commit", "-m", "seed", env=env)
        run("git", "-C", str(seed), "push", str(remote), "cache-index", env=env)
        env = dict(env, GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0=f"url.{remote}.insteadOf", GIT_CONFIG_VALUE_0="https://github.com/owner/plugins.git")
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

        # The workflow records /nix/store outputs. This test's isolated Nix
        # store uses a temporary prefix; retain its real hashes and names.
        paths = [
            "/nix/store/" + Path(line.removeprefix("StorePath: ")).name
            for record in sorted(exported.glob("*.narinfo"))
            for line in record.read_text().splitlines()
            if line.startswith("StorePath: ")
        ]

        def record_batch(folder):
            (folder / "revision.txt").write_text("1" * 40 + "\n")
            (folder / "paths-x86_64-linux.txt").write_text("\n".join(paths) + "\n")

        record_batch(prepared)
        repository = prepared / "repository"
        repository.mkdir()
        archive = repository / "source-any.tar"
        archive.write_bytes(b"signed archive transport fixture")
        (repository / "catalog.json").write_text(json.dumps({
            "records": [{
                "plugin_id": "@korri:source", "release_version": "build-1", "platform": "any",
                "store_path": paths[0], "archive_url": base + "build-1/" + archive.name,
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "publicKey": "korri-plugins-1:" + "A" * 43 + "=",
            }], "latest": {"@korri:source": "build-1"},
        }))

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
                "--index-branch",
                "cache-index",
                "--cache-url",
                cache_url,
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
            "--index-branch",
            "cache-index",
            "--cache-url",
            cache_url,
            "--revision",
            "2" * 40,
            env=env,
            succeeds=False,
        )
        self.assertIn("checked source", refused.stderr)
        self.assertEqual(before, fixture_state.read_bytes())
        (prepared / "revision.txt").write_text("2" * 40 + "\n")
        refused = run(
            sys.executable,
            str(SCRIPT),
            "publish",
            str(prepared),
            "--repo",
            "owner/plugins",
            "--tag",
            "build-1",
            "--index-branch",
            "cache-index",
            "--cache-url",
            cache_url,
            "--revision",
            "2" * 40,
            env=env,
            succeeds=False,
        )
        self.assertIn("NAR tag must point", refused.stderr)
        self.assertEqual(before, fixture_state.read_bytes())
        record_batch(prepared)
        run(
            sys.executable,
            str(SCRIPT),
            "publish",
            str(prepared),
            "--repo",
            "owner/plugins",
            "--tag",
            "build-1",
            "--index-branch",
            "cache-index",
            "--cache-url",
            cache_url,
            "--revision",
            "1" * 40,
            env=env,
        )
        state = json.loads(fixture_state.read_text())
        self.assertFalse(state["releases"][0]["draft"])
        self.assertEqual(
            len([r for r in state["releases"] if r["tag_name"] == "build-1"]), 1
        )
        batch_assets = {a["name"]: a for a in state["assets"] if a["release"] == 1}
        for name in ("revision.txt", "paths-x86_64-linux.txt", "catalog.json", "source-any.tar"):
            self.assertEqual(
                (fixture / str(batch_assets[name]["id"])).read_bytes(),
                (repository / name if name in ("catalog.json", "source-any.tar") else prepared / name).read_bytes(),
            )
        self.assertFalse(
            any(
                a["release"] == 2
                and (a["name"].startswith("paths-") or a["name"] == "revision.txt")
                for a in state["assets"]
            )
        )
        self.assertEqual(
            run("git", "--git-dir", str(remote), "show", "cache-index:catalog.json", env=env).stdout.strip(),
            (repository / "catalog.json").read_text().strip(),
        )
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
        record_batch(another)
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
        record_batch(third)
        command = [
            sys.executable,
            "-c",
            RECORDED_SLEEP,
            str(SCRIPT),
            "publish",
            str(third),
            "--repo",
            "owner/plugins",
            "--tag",
            "build-3",
            "--index-branch",
            "cache-index",
            "--cache-url",
            cache_url,
            "--revision",
            "1" * 40,
        ]
        # A genuine create failure must stop before uploads or publication.
        state = json.loads(fixture_state.read_text())
        state["fail_before_release_create"] = True
        fixture_state.write_text(json.dumps(state))
        before = fixture_state.read_bytes()
        refused = run(*command, env=env, succeeds=False)
        self.assertIn("release creation failed", refused.stderr)
        self.assertEqual(before, fixture_state.read_bytes())
        # The failed create was rechecked for the whole bounded wait.
        self.assertEqual(sum(sleeps(refused)), 60)
        del state["fail_before_release_create"]
        # Another creator (or a lost response) can leave a draft even though
        # our create request failed. Reuse it, without creating another draft.
        state["fail_after_release_create"] = True
        fixture_state.write_text(json.dumps(state))
        run(*command, env=env)
        state = json.loads(fixture_state.read_text())
        self.assertEqual(
            len([r for r in state["releases"] if r["tag_name"] == "build-3"]), 1
        )
        # Identical publication retries must accept the existing release too.
        before = fixture_state.read_bytes()
        run(*command, env=env)
        self.assertEqual(before, fixture_state.read_bytes())
        new_release = next(r for r in state["releases"] if r["tag_name"] == "build-3")
        self.assertFalse(new_release["draft"])
        self.assertTrue(new_release["immutable"])
        # Identical retries include the listing, even after immutability locks it.
        before = fixture_state.read_bytes()
        upload("nars", third, "build-3")
        self.assertEqual(before, fixture_state.read_bytes())
        (third / "paths-x86_64-linux.txt").write_text(paths[0] + "\n")
        refused = upload("nars", third, "build-3", succeeds=False)
        self.assertEqual(before, fixture_state.read_bytes())
        record_batch(third)

        def publish_new(tag, succeeds=True):
            folder = root / f"github-{tag}"
            if not folder.exists():
                run(
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(exported),
                    str(folder),
                    "--nar-base-url",
                    base + tag + "/",
                    env=env,
                )
                record_batch(folder)
            return run(
                *command[:4],
                "publish",
                str(folder),
                "--repo",
                "owner/plugins",
                "--tag",
                tag,
                "--index-branch",
                "cache-index",
                "--cache-url",
                cache_url,
                "--revision",
                "1" * 40,
                env=env,
                succeeds=succeeds,
            )

        def releases(tag):
            state = json.loads(fixture_state.read_text())
            return [r for r in state["releases"] if r["tag_name"] == tag]

        # GitHub's release list can lag a successful create. Wait for the new
        # draft, then publish it, without creating a second release.
        state = json.loads(fixture_state.read_text())
        del state["fail_after_release_create"]
        state["list_lag"] = 3
        fixture_state.write_text(json.dumps(state))
        result = publish_new("build-4")
        self.assertEqual(len(sleeps(result)), 3)
        [lagged] = releases("build-4")
        self.assertFalse(lagged["draft"])
        self.assertNotIn("hidden", json.loads(fixture_state.read_text()))
        # The same lag can follow a create whose response was lost.
        state = json.loads(fixture_state.read_text())
        state.update(fail_after_release_create=True, list_lag=2)
        fixture_state.write_text(json.dumps(state))
        result = publish_new("build-5")
        self.assertEqual(len(sleeps(result)), 2)
        [lagged] = releases("build-5")
        self.assertFalse(lagged["draft"])
        state = json.loads(fixture_state.read_text())
        del state["fail_after_release_create"]
        # A release that never appears stops after the bound, before uploads.
        state["list_lag"] = 1000
        fixture_state.write_text(json.dumps(state))
        refused = publish_new("build-6", succeeds=False)
        self.assertIn("did not appear in GitHub's release list", refused.stderr)
        self.assertEqual(sum(sleeps(refused)), 60)
        [missing] = releases("build-6")
        self.assertTrue(missing["draft"])
        state = json.loads(fixture_state.read_text())
        self.assertFalse(any(a["release"] == missing["id"] for a in state["assets"]))
        del state["hidden"]
        fixture_state.write_text(json.dumps(state))
        # A conflicting Git index file stops without changing release assets.
        run("git", "-C", str(seed), "pull", str(remote), "cache-index", env=env)
        first = next((prepared / "metadata").glob("*.narinfo"))
        (seed / first.name).write_text(first.read_text().replace("NarSize: ", "NarSize: 9"))
        run("git", "-C", str(seed), "add", ".", env=env)
        run("git", "-C", str(seed), "-c", "user.name=test", "-c", "user.email=test@example.org", "commit", "-m", "conflict", env=env)
        run("git", "-C", str(seed), "push", str(remote), "cache-index", env=env)
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
            fixture.write_text("""{ shell, text, dependencies ? [] }: builtins.derivation {
  name = "cache-test"; system = builtins.currentSystem;
  builder = shell; args = [ "-c" "printf '%s' \\\"$text\\\" > \\\"$out\\\"" ];
  inherit text dependencies; preferLocalBuild = true; allowSubstitutes = true;
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
                    if self.path.startswith("/index/"):
                        name = self.path.removeprefix("/index/")
                        result = subprocess.run(["git", "--git-dir", str(root / "index.git"), "show", f"cache-index:{name}"], capture_output=True)
                        self.send_response(404 if result.returncode else 200)
                        self.end_headers()
                        self.wfile.write(result.stdout)
                    elif self.path.startswith("/download/"):
                        self.send_response(302)
                        self.send_header(
                            "Location", "/nars/" + self.path.rsplit("/", 1)[-1]
                        )
                        self.end_headers()
                    elif self.path.startswith("/path-status/"):
                        if self.path.endswith("/nix-cache-info"):
                            self.path = "/upstream/nix-cache-info"
                            super().do_GET()
                        else:
                            self.send_error(int(self.path.split("/")[2]))
                    elif self.path.startswith("/status/"):
                        self.send_error(int(self.path.split("/")[2]))
                    elif self.path.startswith("/disconnect/"):
                        self.close_connection = True
                    elif self.path.startswith("/downgrade/"):
                        self.send_response(302)
                        self.send_header("Location", "http://127.0.0.1/absent")
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
                (prepared / "revision.txt").write_text("1" * 40 + "\n")
                batch_paths = [
                    "/nix/store/" + Path(line.removeprefix("StorePath: ")).name
                    for record in sorted(exported.glob("*.narinfo"))
                    for line in record.read_text().splitlines()
                    if line.startswith("StorePath: ")
                ]
                (prepared / "paths-x86_64-linux.txt").write_text("\n".join(batch_paths) + "\n")
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
                self.check_uploads(root, exported, dict(env, NIX_SSL_CERT_FILE=str(cert)), base + "/index/")
                self.check_upstreams(
                    root, site, base, cert, secret, public, fixture, env
                )
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

    def test_prepare_refuses_insecure_upstreams(self):
        for value in (
            "http://example.com",
            "https://user:secret@example.com",
            "https://example.com?token=secret",
        ):
            result = run(
                sys.executable,
                str(SCRIPT),
                "prepare",
                "/tmp/absent",
                "/tmp/unused",
                "--nar-base-url",
                "https://example.com/nars",
                "--upstream-cache",
                value,
                succeeds=False,
            )
            self.assertIn("HTTPS URL", result.stderr)

    def test_batch_artifacts_combine_and_refuse_conflicts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = [root / "x86", root / "arm"]
            path = "/nix/store/" + "0" * 32 + "-plugin\n"
            for folder, system in zip(inputs, ("x86_64-linux", "aarch64-linux")):
                (folder / "nars").mkdir(parents=True)
                (folder / "metadata").mkdir()
                (folder / "offline-metadata.tar.gz").write_bytes(system.encode())
                (folder / "revision.txt").write_text("1" * 40 + "\n")
                (folder / f"paths-{system}.txt").write_text(path)

            output = root / "combined"
            command = [
                sys.executable,
                str(SCRIPT),
                "combine",
                str(output),
                *map(str, inputs),
            ]
            run(*command)
            self.assertEqual((output / "revision.txt").read_text(), "1" * 40 + "\n")
            self.assertEqual((output / "paths-x86_64-linux.txt").read_text(), path)
            self.assertEqual((output / "paths-aarch64-linux.txt").read_text(), path)
            self.assertEqual((output / "offline-metadata-x86_64-linux.tar.gz").read_bytes(), b"x86_64-linux")
            self.assertEqual((output / "offline-metadata-aarch64-linux.tar.gz").read_bytes(), b"aarch64-linux")
            shutil.rmtree(output)
            (inputs[1] / "revision.txt").write_text("2" * 40 + "\n")
            self.assertIn(
                "conflicting prepared file: revision.txt",
                run(*command, succeeds=False).stderr,
            )
            self.assertFalse(output.exists())
            (inputs[1] / "revision.txt").write_text("1" * 40 + "\n")
            (inputs[1] / "paths-x86_64-linux.txt").write_text(
                path.replace("-plugin", "-different")
            )
            self.assertIn(
                "each prepared cache must name one build system",
                run(*command, succeeds=False).stderr,
            )
            self.assertFalse(output.exists())
            (inputs[1] / "paths-x86_64-linux.txt").unlink()
            listing = inputs[1] / "paths-aarch64-linux.txt"
            for invalid in ("", "./result\n", path + "--impure\n", path.rstrip()):
                listing.write_text(invalid)
                self.assertIn(
                    "expected exact Nix output paths",
                    run(*command, succeeds=False).stderr,
                )
                self.assertFalse(output.exists())
            listing.unlink()
            listing.symlink_to(inputs[0] / "paths-x86_64-linux.txt")
            self.assertIn(
                "expected a regular file", run(*command, succeeds=False).stderr
            )
            self.assertFalse(output.exists())

    def test_publish_requires_commit_and_package_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            refused = run(
                sys.executable,
                str(SCRIPT),
                "publish",
                temp,
                "--repo",
                "owner/plugins",
                "--tag",
                "build-1",
                "--index-branch",
                "cache-index",
                "--cache-url",
                "https://owner.github.io/plugins/",
                "--revision",
                "1" * 40,
                succeeds=False,
            )
            self.assertIn("batch requires package paths", refused.stderr)

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
            "--index-branch",
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
            "--index-branch",
            "cache",
            succeeds=False,
        )


if __name__ == "__main__":
    unittest.main()

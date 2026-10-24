#!/usr/bin/env -S nix shell nixpkgs#python3 -c python3
"""Check the one-off metadata exporter against the file-backed GitHub API."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("github-cache.py")


class MetadataMigrationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        commands = self.root / "commands"
        commands.mkdir()
        gh = commands / "gh"
        gh.write_text(
            "#!"
            + sys.executable
            + "\n"
            + Path(__file__).with_name("github-cache-github-fixture.py").read_text()
        )
        gh.chmod(0o755)
        self.environment = dict(
            os.environ,
            RELEASE_FIXTURE=str(self.root),
            PATH=str(commands) + ":" + os.environ["PATH"],
        )
        self.state = {
            "releases": [{"id": 1, "tag_name": "cache", "draft": False}],
            "assets": [],
        }
        self.original = {}
        self.add("nix-cache-info", b"StoreDir: /nix/store\n")
        for index in range(105):
            name = f"{index:032d}.narinfo"
            data = f"StorePath: /nix/store/{index:032d}-example\nURL: https://github.com/owner/plugins/releases/download/build-previous/{index}.nar.xz\nNarHash: sha256:{'0' * 52}\nNarSize: 1\nReferences: \nSig: existing-signature-bytes\n".encode()
            self.add(name, data)

    def add(self, name, data):
        identity = len(self.state["assets"]) + 10
        self.state["assets"].append(
            {
                "id": identity,
                "name": name,
                "release": 1,
                "state": "uploaded",
                "size": len(data),
                "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
        )
        (self.root / str(identity)).write_bytes(data)
        self.original[name] = data

    def invoke(self, succeeds=True):
        state_path = self.root / "state.json"
        state_path.write_text(json.dumps(self.state))
        original_state = state_path.read_bytes()
        output = self.root / "metadata"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "migrate-metadata",
                str(output),
                "--repo",
                "owner/plugins",
            ],
            env=self.environment,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode == 0, succeeds, result.stderr)
        self.assertEqual(state_path.read_bytes(), original_state)
        return output, result

    def test_all_pages_copy_exact_bytes_and_preserve_signatures_and_nar_urls(self):
        output, result = self.invoke()
        self.assertIn("Verified 106 metadata files", result.stdout)
        self.assertEqual(
            {p.name: p.read_bytes() for p in output.iterdir()}, self.original
        )

    def test_digest_mismatch_leaves_no_completed_output(self):
        self.state["assets"][1]["digest"] = "sha256:" + "0" * 64
        output, result = self.invoke(succeeds=False)
        self.assertIn("digest mismatch", result.stderr)
        self.assertFalse(output.exists())

    def test_unexpected_assets_refuse_instead_of_publishing_unrelated_files(self):
        self.add("unrelated.txt", b"not metadata")
        output, result = self.invoke(succeeds=False)
        self.assertIn("only cache metadata", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

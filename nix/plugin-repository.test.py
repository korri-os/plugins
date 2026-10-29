"""Merge the real publisher's catalog shape and enforce immutable archive bytes."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "publisher", Path(__file__).with_name("github-cache.py")
)
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class PluginRepositoryTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.inputs = []
        for system in ("x86_64-linux", "aarch64-linux"):
            folder = self.root / system
            self.inputs.append(folder)
            for kind in ("nars", "metadata", "repository"):
                (folder / kind).mkdir(parents=True)
            (folder / "revision.txt").write_text("1" * 40 + "\n")
            (folder / f"paths-{system}.txt").write_text(
                "/nix/store/" + "0" * 32 + "-plugin\n"
            )
            (folder / "offline-metadata.tar.gz").write_bytes(system.encode())
            records = []
            for name, platform in (("native", system), ("source", "any")):
                archive = folder / "repository" / f"{name}-{platform}.tar"
                archive.write_bytes(f"{name}-{platform}".encode())
                records.append({
                    "plugin_id": f"@korri:{name}",
                    "release_version": "build-1",
                    "platform": platform,
                    "store_path": "/nix/store/" + "0" * 32 + f"-{name}-{platform}",
                    "archive_url": "https://github.com/owner/plugins/releases/download/build-1/" + archive.name,
                    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    "publicKey": "korri-plugins-1:" + "A" * 43 + "=",
                })
            self.write_catalog(folder, {"records": records, "latest": {
                "@korri:native": "build-1", "@korri:source": "build-1"
            }})
        self.output = self.root / "combined"

    def catalog(self, folder):
        return json.loads((folder / "repository/catalog.json").read_text())

    def write_catalog(self, folder, value):
        (folder / "repository/catalog.json").write_text(json.dumps(value))

    def test_merges_native_platforms_and_deduplicates_identical_any(self):
        publisher.combine(self.output, self.inputs)
        catalog = self.catalog(self.output)
        self.assertEqual(len(catalog["records"]), 3)
        self.assertEqual({r["platform"] for r in catalog["records"]}, {
            "x86_64-linux", "aarch64-linux", "any"
        })
        self.assertEqual(catalog["latest"], self.catalog(self.inputs[0])["latest"])
        files = publisher.repository_files(
            self.output,
            "https://github.com/owner/plugins/releases/download/build-1/",
        )
        self.assertEqual(len(files), 4)
        self.assertIn(self.output / "repository/catalog.json", files)
        # Bytes are stable across architecture artifact download order.
        other = self.root / "other"
        publisher.combine(other, list(reversed(self.inputs)))
        self.assertEqual(
            (other / "repository/catalog.json").read_bytes(),
            (self.output / "repository/catalog.json").read_bytes(),
        )

    def test_rejects_conflicting_any_records_and_latest_marks(self):
        original = self.catalog(self.inputs[1])
        for change in ("record", "latest", "native-any"):
            catalog = copy.deepcopy(original)
            if change == "record":
                catalog["records"][1]["title"] = "different"
            elif change == "latest":
                catalog["latest"]["@korri:native"] = "different"
            else:
                catalog["records"][0]["platform"] = "any"
            self.write_catalog(self.inputs[1], catalog)
            with self.assertRaises(ValueError):
                publisher.combine(self.output, self.inputs)
            self.assertFalse(self.output.exists())

    def test_missing_architecture_catalog_is_not_silently_omitted(self):
        (self.inputs[1] / "repository/catalog.json").unlink()
        with self.assertRaises(ValueError):
            publisher.combine(self.output, self.inputs)
        self.assertFalse(self.output.exists())

    def test_refuses_damaged_archive_wrong_release_url_and_extra_payload(self):
        folder = self.inputs[0]
        base = "https://github.com/owner/plugins/releases/download/build-1/"
        archive = folder / "repository/source-any.tar"
        archive.write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            publisher.repository_files(folder, base)
        archive.write_bytes(b"source-any")
        with self.assertRaisesRegex(ValueError, "destination"):
            publisher.repository_files(folder, base.replace("build-1", "build-2"))
        (folder / "repository/secret").write_bytes(b"must not upload")
        with self.assertRaisesRegex(ValueError, "unexpected"):
            publisher.repository_files(folder, base)


if __name__ == "__main__":
    unittest.main()

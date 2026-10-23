# ruff: noqa: FLY002
# Keep private-pattern test strings assembled; the public privacy scan must not flag its own fixtures.
import tempfile
import unittest
from pathlib import Path

from check_samples import check_checksums, check_fps, check_privacy, is_private


class PublicEvidenceTests(unittest.TestCase):
    def test_rejects_private_identifiers_and_storage_paths(self):
        examples = [
            f"/var/lib/korri/users/{'f' * 64}/saves",
            '"--autolaunch", "' + "f" * 32 + '"',
            ".".join(["10", "42", "0", "2"]),
            ".".join(["192", "168", "0", "2"]),
            ".".join(["100", "64", "0", "2"]),
            "/srv/" + "lakes/private",
            "/var/lib/" + "korri-private-cache.example/cache",
            "/home/" + "private-user/game",
        ]
        for text in examples:
            with self.subTest(text=text):
                self.assertTrue(is_private(text))
        self.assertFalse(is_private("/var/lib/korri/users/<account>/saves"))
        self.assertFalse(is_private("<device-usb-ip> <owner-storage> /home/korri"))

    def test_rejects_partial_subnets_personal_logins_and_signing_keys(self):
        examples = [
            ".".join(["10", "42", ""]),
            ".".join(["10", "42", "3", ""]),
            ".".join(["10", "42", "3", "x"]),
            ".".join(["192", "168", ""]),
            "private-user" + "@" + "unzen",
            "ssh-ng://private-user" + "@" + "nix-builder-fuji",
            "signer-1:" + "A" * 43 + "=",
            '{"@owner":{"publicKey":"redact-me"}}',
        ]
        for text in examples:
            with self.subTest(text=text):
                self.assertTrue(is_private(text))
        for text in [
            "<device-usb-ip> <owner-storage-login> <builder-login>",
            '{"@<publisher>":{"publicKey":"<publisher-public-key>"}}',
            '{"@korri":{}}',
            "sha256:" + "a" * 64,
            "fuji yari zao unzen",
        ]:
            with self.subTest(text=text):
                self.assertFalse(is_private(text))

    def test_privacy_scan_includes_bench_and_product_readmes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "bench"
            root.mkdir()
            for readme in (root / "README.md", root.parent / "README.md"):
                readme.write_text("private-user" + "@" + "fuji")
                with self.assertRaises(ValueError):
                    check_privacy(root)
                readme.write_text("<builder-login>")
            self.assertEqual(check_privacy(root), 2)

    def test_committed_evidence_is_redacted_and_all_fps_arrays_reproduce(self):
        root = Path(__file__).resolve().parent
        self.assertGreater(check_privacy(root), 0)
        self.assertGreater(check_fps(root), 0)
        self.assertGreater(check_checksums(root), 0)


if __name__ == "__main__":
    unittest.main()

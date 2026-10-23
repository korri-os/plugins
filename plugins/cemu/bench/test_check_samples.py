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

    def test_committed_evidence_is_redacted_and_all_fps_arrays_reproduce(self):
        root = Path(__file__).resolve().parent
        self.assertGreater(check_privacy(root), 0)
        self.assertGreater(check_fps(root), 0)
        self.assertGreater(check_checksums(root), 0)


if __name__ == "__main__":
    unittest.main()

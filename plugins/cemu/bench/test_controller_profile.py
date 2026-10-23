import os
import tempfile
import unittest
from pathlib import Path

from controller_profile import ControllerProfile


class ControllerProfileTests(unittest.TestCase):
    def test_existing_native_file_round_trips_exact_bytes_and_metadata(self):
        # These are opaque XML transport fixtures, not a proposed Cemu schema.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profiles = root / "controllerProfiles"
            profiles.mkdir()
            destination = profiles / "controller0.xml"
            destination.write_bytes(b"<root>original</root>\n")
            destination.chmod(0o640)
            os.utime(destination, ns=(1_000_000_000, 2_000_000_000))
            before = destination.stat()
            template = root / "bench.xml"
            template.write_bytes(b"<root>bench</root>\n")
            profile = ControllerProfile(destination, template, root)
            profile.apply()
            self.assertEqual(destination.read_bytes(), template.read_bytes())
            profile.restore()
            self.assertEqual(destination.read_bytes(), b"<root>original</root>\n")
            after = destination.stat()
            self.assertEqual(
                (before.st_mode, before.st_uid, before.st_gid, before.st_mtime_ns),
                (after.st_mode, after.st_uid, after.st_gid, after.st_mtime_ns),
            )
            self.assertTrue(profile.state["restored"])

    def test_concurrent_edits_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "controllerProfiles").mkdir()
            destination = root / "controllerProfiles/controller0.xml"
            destination.write_text("<root>original</root>")
            template = root / "bench.xml"
            template.write_text("<root>bench</root>")
            profile = ControllerProfile(destination, template, root)
            profile.apply()
            destination.write_text("<root>other writer</root>")
            with self.assertRaisesRegex(RuntimeError, "manual review"):
                profile.restore()
            self.assertEqual(destination.read_text(), "<root>other writer</root>")
            self.assertEqual(
                (root / "controller-profile.before.xml").read_text(),
                "<root>original</root>",
            )

    def test_no_implicit_profile_creation_or_symlink_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "controllerProfiles").mkdir()
            template = root / "bench.xml"
            template.write_text("<root />")
            destination = root / "controllerProfiles/controller0.xml"
            with self.assertRaises(FileNotFoundError):
                ControllerProfile(destination, template, root)
            destination.symlink_to(template)
            with self.assertRaises((OSError, ValueError)):
                ControllerProfile(destination, template, root)
            self.assertEqual(template.read_text(), "<root />")


if __name__ == "__main__":
    unittest.main()

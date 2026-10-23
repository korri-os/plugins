import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from save_safety import SaveSafety


class InMemorySaves:
    def __init__(self, record):
        self.records = {"head-a": record}
        self.current: str | None = "head-a"
        self.methods = []
        self.in_use = []
        self.status = "Synced"
        self.restore_content = None

    def call(self, method, payload, timeout_s=30):
        self.methods.append((method, payload))
        if method == "app.saves.check":
            return {"status": self.status, "inUse": self.in_use, "warnings": []}
        if method == "app.saves.restore":
            self.records["restored"] = self.restore_content or dict(
                self.records[payload["snapshotId"]], parents=[self.current]
            )
            self.current = "restored"
        return {
            "current": self.current,
            "records": [
                {"snapshotId": key, "record": value}
                for key, value in self.records.items()
            ],
        }


class SaveSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.objects = self.root / "objects"
        self.objects.mkdir()
        self.data = b"actual progress bytes"
        self.sha = hashlib.sha256(self.data).hexdigest()
        (self.objects / self.sha).write_bytes(self.data)
        self.record = {
            "parents": [],
            "locations": [
                {
                    "key": "mlc",
                    "kind": "save",
                    "files": [
                        {
                            "path": "game_data.sav",
                            "sha256": "sha256:" + self.sha,
                            "bytes": len(self.data),
                        }
                    ],
                }
            ],
        }
        self.rpc = InMemorySaves(self.record)
        self.guard = SaveSafety(
            self.rpc, "botw", "@korri:cemu/cemu", self.objects, self.root
        )

    def tearDown(self):
        backup = self.guard.state.get("privateBackup")
        if backup:
            shutil.rmtree(str(backup))
        self.temp.cleanup()

    def test_preflight_hashes_every_blob_and_restore_preserves_payload_and_ancestry(
        self,
    ):
        self.guard.preflight()
        self.guard.verify_before_launch()
        backup = Path(str(self.guard.state["privateBackup"]))
        self.assertEqual((backup / self.sha).read_bytes(), self.data)
        self.rpc.records["bench"] = dict(self.record, parents=["head-a"])
        self.rpc.current = "bench"
        self.guard.restore()
        self.assertEqual(self.rpc.current, "restored")
        self.assertEqual(self.guard.state["additionalSnapshotsBeforeRestore"], 1)
        self.assertTrue(self.guard.state["identicalPayload"])
        self.assertTrue(self.guard.state["originalInAncestry"])
        self.assertEqual(self.guard.state["restoredFilesVerified"], 1)
        self.assertEqual(
            json.loads((self.root / "save-safety.json").read_text())["status"],
            "restored and verified",
        )
        self.assertEqual(
            [
                payload
                for method, payload in self.rpc.methods
                if method == "app.saves.restore"
            ],
            [{"gameId": "botw", "snapshotId": "head-a"}],
        )

    def test_incomplete_and_corrupt_original_refuse_before_any_restore(self):
        path = self.objects / self.sha
        path.unlink()
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            self.guard.preflight()
        path.write_bytes(b"x" * len(self.data))
        with self.assertRaisesRegex(RuntimeError, "hash is invalid"):
            self.guard.preflight()
        self.guard.restore()
        self.assertNotIn(
            "app.saves.restore", [method for method, _ in self.rpc.methods]
        )

    def test_missing_post_run_payload_fails_and_keeps_private_backup(self):
        self.guard.preflight()
        (self.objects / self.sha).unlink()
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            self.guard.restore()
        self.assertEqual(self.guard.state["status"], "restore failed")
        self.assertEqual(
            (Path(str(self.guard.state["privateBackup"])) / self.sha).read_bytes(),
            self.data,
        )

    def test_concurrent_head_or_in_use_refuses(self):
        self.guard.preflight()
        self.rpc.current = "other"
        with self.assertRaisesRegex(RuntimeError, "changed during preflight"):
            self.guard.verify_before_launch()
        self.rpc.in_use = [{"device": "peer", "since": 1}]
        with self.assertRaisesRegex(RuntimeError, "in use"):
            self.guard.restore()

    def test_split_missing_head_and_wrong_ancestry_refuse(self):
        self.rpc.status = "Split"
        with self.assertRaisesRegex(RuntimeError, "split"):
            self.guard.preflight()
        self.rpc.status = "Synced"
        self.rpc.current = None
        with self.assertRaisesRegex(RuntimeError, "unambiguous"):
            self.guard.preflight()
        self.rpc.current = "head-a"
        self.guard.preflight()
        self.rpc.restore_content = dict(self.record, parents=[])
        with self.assertRaisesRegex(RuntimeError, "does not descend"):
            self.guard.restore()

    def test_bad_restoration_is_not_reported_as_safe(self):
        self.guard.preflight()
        self.rpc.restore_content = dict(self.record, locations=[])
        with self.assertRaisesRegex(RuntimeError, "payload differs"):
            self.guard.restore()
        self.assertEqual(self.guard.state["status"], "restore failed")


if __name__ == "__main__":
    unittest.main()

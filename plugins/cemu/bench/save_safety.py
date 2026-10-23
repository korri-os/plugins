"""Supported saves RPCs plus read-only blob verification (ADR 0014/store.rs).

The RPC has no guest launch or snapshot opt-out. Restore appends a continuation;
it does not rewind IDs or stop bench snapshots entering retention.
"""

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Protocol

from gameplay_gate import object_record

Record = dict[str, object]


class SavesRpc(Protocol):
    def call(self, method: str, payload: Record, timeout_s: float = 30) -> Record: ...


def entries(history: Record) -> dict[str, Record]:
    values = history.get("records")
    if not isinstance(values, list):
        raise TypeError("Malformed SaveHistory.records")
    result = {}
    for value in values:
        entry = object_record(value)
        result[str(entry["snapshotId"])] = object_record(entry["record"])
    return result


def payload(record: Record) -> list[tuple[str, str, str, str, int]]:
    locations = record.get("locations")
    if not isinstance(locations, list):
        raise TypeError("Malformed SnapshotRecord.locations")
    result = []
    for item in locations:
        location = object_record(item)
        files = location["files"]
        if not isinstance(files, list):
            raise TypeError("Malformed SnapshotLocation.files")
        for item_file in files:
            file = object_record(item_file)
            size = file["bytes"]
            sha = str(file["sha256"])
            if (
                not isinstance(size, int)
                or size < 0
                or not re.fullmatch(r"sha256:[a-f0-9]{64}", sha)
            ):
                raise ValueError("Malformed SaveFile digest/size")
            result.append(
                (
                    str(location["key"]),
                    str(location["kind"]),
                    str(file["path"]),
                    sha,
                    size,
                )
            )
        # Empty locations are also part of the original declaration.
        if not files:
            result.append((str(location["key"]), str(location["kind"]), "", "", 0))
    return sorted(result)


def verify_payload(record: Record, objects: Path, backup: Path | None = None) -> int:
    count = 0
    for _key, _kind, _path, sha, size in payload(record):
        if not sha:
            continue
        path = objects / sha.removeprefix("sha256:")
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
            raise RuntimeError(
                "Person's save head payload is incomplete; refusing bench/restore"
            )
        with path.open("rb") as source:
            if "sha256:" + hashlib.file_digest(source, "sha256").hexdigest() != sha:
                raise RuntimeError("Person's save head payload hash is invalid")
        if backup:
            destination = backup / path.name
            if not destination.exists():
                shutil.copyfile(path, destination)
                destination.chmod(0o600)
        count += 1
    return count


def descends_from(current: str, ancestor: str, records: dict[str, Record]) -> bool:
    pending = [current]
    seen = set()
    while pending:
        snapshot = pending.pop()
        if snapshot == ancestor:
            return True
        if snapshot in seen:
            continue
        seen.add(snapshot)
        parents = records.get(snapshot, {}).get("parents", [])
        if not isinstance(parents, list) or not all(
            isinstance(parent, str) for parent in parents
        ):
            raise ValueError("Malformed snapshot parents")
        pending.extend(parents)
    return False


class SaveSafety:
    def __init__(
        self, rpc: SavesRpc, game: str, runner: str, objects: Path, folder: Path
    ):
        self.rpc = rpc
        self.game = game
        self.runner = runner
        self.objects = objects
        self.folder = folder
        self.original = ""
        self.record: Record = {}
        self.before: dict[str, Record] = {}
        self.state: Record = {"status": "not checked"}

    def write(self) -> None:
        (self.folder / "save-safety.json").write_text(
            json.dumps(self.state, indent=2) + "\n"
        )

    def check(self) -> None:
        check = self.rpc.call(
            "app.saves.check", {"gameId": self.game, "runnerId": self.runner}
        )
        if check.get("inUse") or check.get("status") == "Split":
            raise RuntimeError(
                "Save split or another device in use; refusing bench/restore"
            )

    def preflight(self) -> None:
        self.check()  # Pull known peer heads before recording the person's actual continuation.
        history = self.rpc.call("app.saves.history", {"gameId": self.game})
        self.before = entries(history)
        current = history.get("current")
        if not isinstance(current, str) or current not in self.before:
            raise RuntimeError("No unambiguous existing save head; refusing bench")
        self.record = self.before[current]
        count = verify_payload(self.record, self.objects)
        backup = Path(tempfile.mkdtemp(prefix="korri-cemu-save-"))
        os.chmod(backup, 0o700)
        verify_payload(self.record, self.objects, backup)
        (backup / "head.json").write_text(json.dumps(history, indent=2) + "\n")
        (backup / "head.json").chmod(0o600)
        self.original = current
        self.state = {
            "status": "original payload verified",
            "originalHead": current,
            "filesVerified": count,
            "privateBackup": str(backup),
        }
        self.write()

    def verify_before_launch(self) -> None:
        history = self.rpc.call("app.saves.history", {"gameId": self.game})
        if history.get("current") != self.original:
            raise RuntimeError(
                "Person's save head changed during preflight; refusing bench"
            )
        verify_payload(self.record, self.objects)

    def restore(self) -> None:
        if not self.original:
            return
        try:
            self.check()
            history = self.rpc.call("app.saves.history", {"gameId": self.game})
            records = entries(history)
            added = set(records) - set(self.before)
            self.state["additionalSnapshotsBeforeRestore"] = len(added)
            self.state["additionalSnapshotIds"] = sorted(added)
            verify_payload(self.record, self.objects)
            restored = self.rpc.call(
                "app.saves.restore",
                {"gameId": self.game, "snapshotId": self.original},
                timeout_s=60,
            )
            records = entries(restored)
            current = restored.get("current")
            if not isinstance(current, str) or current not in records:
                raise RuntimeError("Restore did not select a continuation")
            if payload(records[current]) != payload(self.record):
                raise RuntimeError(
                    "Restored continuation payload differs from person's head"
                )
            if not descends_from(current, self.original, records):
                raise RuntimeError(
                    "Restored continuation does not descend from person's head"
                )
            count = verify_payload(records[current], self.objects)
            verified = self.rpc.call("app.saves.history", {"gameId": self.game})
            if verified.get("current") != current:
                raise RuntimeError(
                    "Concurrent head change after restore; operator review required"
                )
            self.state.update(
                {
                    "status": "restored and verified",
                    "restoredHead": current,
                    "restoredFilesVerified": count,
                    "identicalPayload": True,
                    "originalInAncestry": True,
                    "restoreSnapshots": len(set(records) - set(entries(history))),
                }
            )
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            self.state["status"] = "restore failed"
            self.state["error"] = str(exc)
            raise
        finally:
            self.write()

    def summary(self) -> str:
        return "\n".join(
            [
                f"Save safety: {self.state.get('status')}.",
                f"Original head: `{self.original or 'not recorded'}`; restored continuation: `{self.state.get('restoredHead', 'not selected')}`.",
                f"Payload equal: {self.state.get('identicalPayload', False)}; original in ancestry: {self.state.get('originalInAncestry', False)}.",
                f"Additional snapshots before restore: {self.state.get('additionalSnapshotsBeforeRestore', 'unknown')}; restore snapshots: {self.state.get('restoreSnapshots', 0)}.",
                "See private `save-safety.json` for payload verification and backup. Additional records can include peer arrivals.",
                "Risk: bench and restore snapshots still enter real history and count toward retention. No supported guest/skip-snapshot launch exists.",
            ]
        )

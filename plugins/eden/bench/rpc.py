"""Subset of Core's generated korrid.ts treaty; localhost only, no new RPC.

Portal flow: app.session.reserve -> app.session.start -> exact stop/cancel.
Caller supplies the existing root-readable capability file; never persist it.
"""

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import NoReturn, cast

Record = dict[str, object]


def record(value: object) -> Record:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise ValueError("RPC expected an object")
    return cast(Record, value)


class RpcFailure(RuntimeError):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        # Generic failures never echo server messages or request bodies.
        super().__init__(f"RPC failed: {code}")


class IdleProofError(RuntimeError):
    def __init__(self, reason: str, evidence: Record):
        self.evidence = evidence
        super().__init__(reason)


def retained_idle_proof(
    failure: RpcFailure, own_launches: set[str], units: str, root: Path
) -> Record:
    """A previous terminal exit is not unknown/native-active state or our failure.

    Uses actual cgroup contents, never st_size (cgroup pseudo-files have size 0).
    root is the existing Core game slice, with a filesystem seam for tests.
    """
    match = re.fullmatch(r"host launch ([a-f0-9]{32}) failed: .+", failure.message)
    evidence: Record = {
        "retainedStatus": {"code": failure.code, "message": failure.message},
        "acceptedAsIdle": False,
        "activeUnitListing": units,
    }
    if failure.code != "HostLaunchFailed" or not match:
        raise IdleProofError(
            "Retained status is not an identified terminal launch failure", evidence
        )
    launch = match[1]
    evidence.update({"launchId": launch, "outsideThisRun": launch not in own_launches})
    if launch in own_launches:
        raise IdleProofError(
            "Our own failed launch cannot be accepted as idle", evidence
        )
    groups: dict[str, list[int]] = {}
    evidence["cgroups"] = groups

    def walk_error(error: OSError) -> NoReturn:
        raise error

    try:
        if not root.is_dir():
            raise FileNotFoundError("Core game cgroup is unavailable")
        for directory, subdirectories, _ in os.walk(root, onerror=walk_error):
            if any((Path(directory) / child).is_symlink() for child in subdirectories):
                raise OSError("Unexpected cgroup symlink")
            path = Path(directory) / "cgroup.procs"
            groups[str(path)] = [int(value) for value in path.read_text().split()]
            if any(pid <= 0 for pid in groups[str(path)]):
                raise ValueError("Invalid native PID")
        if not groups:
            raise OSError("No native cgroup observations")
    except (OSError, ValueError) as exc:
        evidence["nativeError"] = type(exc).__name__
        raise IdleProofError(
            "Native state unreadable or unknown; idle is unproven", evidence
        ) from exc
    if units.strip() or any(groups.values()):
        raise IdleProofError(
            "Native game/acquire unit or cgroup is populated", evidence
        )
    evidence["acceptedAsIdle"] = True
    return evidence


class Rpc:
    def __init__(self, port: int, capability_file: Path):
        if not 1 <= port <= 65535:
            raise ValueError("Invalid localhost port")
        self.url = f"http://127.0.0.1:{port}/rpc"
        self.idle_observations: list[Record] = []
        self.capability = capability_file.read_text().strip()
        if not self.capability:
            raise ValueError("Empty RPC capability")

    def call(self, tag: str, payload: Record) -> Record:
        req = urllib.request.Request(
            self.url,
            json.dumps({"_tag": tag, "payload": payload}).encode(),
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.capability}",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = record(json.load(response))
        if result.get("_tag") != tag:
            raise ValueError("RPC response tag mismatch")
        outcome = record(result.get("outcome"))
        if outcome.get("_tag") == "Err":
            detail = record(outcome.get("payload"))
            raise RpcFailure(str(detail.get("code")), str(detail.get("message", "")))
        if outcome.get("_tag") != "Ok":
            raise ValueError("Unknown RPC outcome")
        return record(outcome.get("payload"))

    def require_idle(self, own_launches: set[str] | None = None) -> None:
        try:
            status = self.call("app.session.status", {})
        except RpcFailure as exc:
            if exc.code in ("SessionCompleted", "NoActiveSession"):
                return
            if exc.code == "HostLaunchFailed":
                try:
                    listing = subprocess.check_output(
                        [
                            "systemctl",
                            "list-units",
                            "--plain",
                            "--no-legend",
                            "--no-pager",
                            "--state=active,activating,deactivating,reloading",
                            "korri-game-*",
                            "korri-acquire-*",
                        ],
                        text=True,
                        timeout=5,
                    )
                except (OSError, subprocess.SubprocessError) as error:
                    self.idle_observations.append(
                        {
                            "retainedStatus": {
                                "code": exc.code,
                                "message": exc.message,
                            },
                            "acceptedAsIdle": False,
                            "nativeError": type(error).__name__,
                        }
                    )
                    raise RuntimeError(
                        "Native unit observation failed; idle unproven"
                    ) from error
                try:
                    proof = retained_idle_proof(
                        exc,
                        own_launches or set(),
                        listing,
                        Path("/sys/fs/cgroup/korri.slice/korri-games.slice"),
                    )
                except IdleProofError as error:
                    self.idle_observations.append(error.evidence)
                    raise
                self.idle_observations.append(proof)
                return
            raise
        if (
            status.get("active")
            or status.get("pendingLaunches")
            or status.get("observationFailure")
        ):
            raise RuntimeError("Session busy or observation failed; refusing to launch")

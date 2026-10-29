"""Mute one PipeWire sink for a bench run, then put back its previous state.

Uses the device's own `wpctl` as the session user. The sink is named, not
numbered: PipeWire can renumber nodes, so every call resolves the name again.
"""

import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

Runner = Callable[[list[str]], str]


def run_wpctl(command: list[str]) -> str:
    return subprocess.check_output(
        command, text=True, stderr=subprocess.DEVNULL, timeout=10
    )


class Speaker:
    def __init__(
        self,
        sink: str,
        user: str,
        runtime: Path,
        folder: Path,
        runner: Runner = run_wpctl,
    ):
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", sink):
            raise ValueError("Sink must be a PipeWire node name")
        self.sink = sink
        self.prefix = [
            "runuser",
            "-u",
            user,
            "--",
            "env",
            f"XDG_RUNTIME_DIR={runtime}",
            f"DBUS_SESSION_BUS_ADDRESS=unix:path={runtime}/bus",
            "wpctl",
        ]
        self.folder = folder
        self.runner = runner
        self.before: bool | None = None
        self.state: dict[str, object] = {"sink": sink, "restored": False}

    def wpctl(self, *args: str) -> str:
        return self.runner([*self.prefix, *args])

    def node(self) -> str:
        pattern = re.compile(r"(\d+)\.\s+" + re.escape(self.sink) + r"(\s|$)")
        for line in self.wpctl("status", "-n").splitlines():
            found = pattern.search(line)
            if found:
                return found.group(1)
        raise RuntimeError(f"PipeWire sink {self.sink} not found")

    def muted(self, node: str) -> bool:
        volume = self.wpctl("get-volume", node).strip()
        if not volume.startswith("Volume:"):
            raise RuntimeError(f"Unexpected wpctl volume reply: {volume!r}")
        return "[MUTED]" in volume

    def persist(self) -> None:
        (self.folder / "speaker.json").write_text(
            json.dumps(self.state, indent=2) + "\n"
        )

    def set_muted(self, muted: bool) -> None:
        node = self.node()
        self.wpctl("set-mute", node, "1" if muted else "0")
        if self.muted(node) != muted:
            raise RuntimeError(f"PipeWire sink {self.sink} mute did not change")

    def mute(self) -> None:
        """Record the previous mute state once, then mute."""
        if self.before is None:
            self.before = self.muted(self.node())
            self.state["mutedBefore"] = self.before
            self.persist()
        self.set_muted(True)

    def hold(self) -> None:
        """Mute again if something unmuted the sink during the run."""
        if self.before is None:
            return
        node = self.node()
        if not self.muted(node):
            self.state["remuted"] = int(str(self.state.get("remuted", 0))) + 1
            self.set_muted(True)

    def restore(self) -> None:
        if self.before is None:
            return
        try:
            self.set_muted(self.before)
            self.state["restored"] = True
        finally:
            self.persist()

    def summary(self) -> str:
        if self.before is None:
            return "not changed"
        previous = "muted" if self.before else "unmuted"
        restored = "restored" if self.state["restored"] else "NOT restored"
        return (
            f"`{self.sink}` muted for the run; previous state ({previous}) {restored}"
        )

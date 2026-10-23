"""Scoped replacement of an EXISTING Cemu-native controller XML file.

No Cemu fields are authored or interpreted. The operator supplies a profile
created by Cemu with bench seat P2 selected. Native directory grounding:
nix-on-rocks guest/launchers/botw-guest.sh:120-122, controllerProfiles/*.xml.
"""

import hashlib
import json
import os
import stat
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

LIMIT = 1024 * 1024


def read_xml(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > LIMIT:
            raise ValueError("Controller profile must be a regular XML file <= 1 MiB")
        with os.fdopen(os.dup(fd), "rb") as source:
            data = source.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise ValueError("Controller profile grew beyond 1 MiB")
        try:
            ET.fromstring(data)
        except ET.ParseError as exc:
            raise ValueError("Controller profile is not valid XML") from exc
        return data
    finally:
        os.close(fd)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ControllerProfile:
    def __init__(self, destination: Path, template: Path, folder: Path):
        if (
            destination.suffix != ".xml"
            or destination.parent.name != "controllerProfiles"
        ):
            raise ValueError("Select an existing Cemu controllerProfiles/*.xml file")
        self.destination = destination.parent.resolve(strict=True) / destination.name
        if self.destination == template.resolve(strict=True):
            raise ValueError(
                "Controller template and active profile must be separate files"
            )
        self.template = read_xml(template)
        self.original = read_xml(self.destination)
        self.metadata = self.destination.stat(follow_symlinks=False)
        self.parent_identity = self.destination.parent.stat().st_ino
        self.attributes = {
            name: os.getxattr(self.destination, name, follow_symlinks=False)
            for name in os.listxattr(self.destination, follow_symlinks=False)
        }
        self.folder = folder
        self.applied = False
        self.state: dict[str, object] = {
            "path": str(self.destination),
            "originalSha256": digest(self.original),
            "templateSha256": digest(self.template),
            "restored": False,
        }

    def persist(self) -> None:
        (self.folder / "controller-profile.json").write_text(
            json.dumps(self.state, indent=2) + "\n"
        )

    def replace(self, data: bytes, restore: bool) -> None:
        directory = os.open(
            self.destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        name = ".korri-bench-" + uuid.uuid4().hex
        try:
            if os.fstat(directory).st_ino != self.parent_identity:
                raise RuntimeError(
                    "Cemu controller directory changed; refusing profile write"
                )
            fd = os.open(
                name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory
            )
            with os.fdopen(fd, "wb") as output:
                output.write(data)
                output.flush()
                os.fchown(output.fileno(), self.metadata.st_uid, self.metadata.st_gid)
                os.fchmod(output.fileno(), stat.S_IMODE(self.metadata.st_mode))
                for key, value in self.attributes.items():
                    os.setxattr(output.fileno(), key, value)
                if restore:
                    os.utime(
                        output.fileno(),
                        ns=(self.metadata.st_atime_ns, self.metadata.st_mtime_ns),
                    )
                os.fsync(output.fileno())
            os.replace(
                name, self.destination.name, src_dir_fd=directory, dst_dir_fd=directory
            )
            os.fsync(directory)
        finally:
            try:
                os.unlink(name, dir_fd=directory)
            except FileNotFoundError:
                pass
            os.close(directory)

    def apply(self) -> None:
        if read_xml(self.destination) != self.original:
            raise RuntimeError("Controller profile changed before launch")
        (self.folder / "controller-profile.before.xml").write_bytes(self.original)
        (self.folder / "controller-profile.template.xml").write_bytes(self.template)
        self.persist()
        self.applied = True  # restoration also covers an interrupted/partial apply
        self.replace(self.template, restore=False)
        self.state["applied"] = True
        self.persist()

    def restore(self) -> None:
        if not self.applied:
            return
        after = read_xml(self.destination)
        self.state["afterSha256"] = digest(after)
        (self.folder / "controller-profile.after.xml").write_bytes(after)
        if after == self.original:
            self.state["restored"] = True
            self.persist()
            return
        if after != self.template:
            self.persist()
            raise RuntimeError(
                "Cemu/controller profile changed during run; original retained for manual review"
            )
        self.replace(self.original, restore=True)
        self.state["restored"] = read_xml(self.destination) == self.original
        self.persist()
        if not self.state["restored"]:
            raise RuntimeError("Original Cemu controller profile was not restored")

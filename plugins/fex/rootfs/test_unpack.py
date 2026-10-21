"""Run the real fex-unpack source against small synthetic archives."""
import io
import os
from pathlib import Path
import random
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest

HERE = Path(__file__).parent


def elf(machine):
    return b"\x7fELF" + bytes(14) + machine + bytes(64)


def write_tree(root, files):
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def tar_zst(stem, files, modes=None, extra_names=(".PKGINFO", ".MTREE")):
    """An Arch package: member modes from `modes`, else 0755 for directories
    and shared objects and 0644 for other files, as Arch packages store them."""
    modes = modes or {}
    members = files | {name: b"metadata\n" for name in extra_names}
    directories = sorted({str(parent) for name in members
                          for parent in Path(name).parents if str(parent) != "."})
    raw = stem.with_suffix(".pkg.tar")
    with tarfile.open(raw, "w", format=tarfile.GNU_FORMAT) as archive:
        for name in directories:
            info = tarfile.TarInfo(name)
            info.type = tarfile.DIRTYPE
            info.mode = modes.get(name, 0o755)
            archive.addfile(info)
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mode = modes.get(name, 0o755 if ".so" in name else 0o644)
            archive.addfile(info, io.BytesIO(content))
    archive = stem.with_suffix(".pkg.tar.zst")
    subprocess.run(["zstd", "-q", "-f", "--rm", str(raw), "-o", str(archive)], check=True)
    return archive


# The game user and group in the device's cache ACL. Numeric, because no such
# account exists where the check runs.
GAME_UID = GAME_GID = 4242
# /var/lib/korri/cache/fex/rootfs on the RG353M (getfacl, 2026-10-21). The
# default mask is empty, so a file created there gets an empty mask unless
# something sets its group bits afterwards.
DEVICE_CACHE_ACL = ",".join([
    "u::rwx", f"u:{GAME_UID}:r-x", "g::--x", f"g:{GAME_GID}:r-x", "m::r-x", "o::r-x",
    "d:u::rwx", f"d:u:{GAME_UID}:r-x", "d:g::--x", f"d:g:{GAME_GID}:r-x", "d:m::---", "d:o::---",
])


def acl_entries(path):
    """The access ACL of one path as {tag: permissions}, e.g. {"mask": "r-x"}."""
    output = subprocess.run(["getfacl", "--numeric", "--omit-header", "--no-effective", "--", str(path)],
                            check=True, capture_output=True, text=True).stdout
    entries = {}
    for line in output.splitlines():
        if line and not line.startswith(("#", "default:")):
            tag, qualifier, permissions = line.split(":")
            entries[f"{tag}:{qualifier}" if qualifier else tag] = permissions
    return entries


def effective(entries, tag):
    """Permissions a named ACL entry grants after the mask."""
    return "".join(bit if bit == mask_bit else "-"
                   for bit, mask_bit in zip(entries[tag], entries["mask"]))


def fixtures(scratch, icd_machine=b"\x3e\x00"):
    """The base image and three overlay packages, in declared order."""
    base = scratch / "base"
    write_tree(base, {
        "etc/os-release": b"NAME=Fixture\n",
        # The overlay replaces this wrong-architecture driver.
        "usr/lib/libvulkan_freedreno.so": elf(b"\xb7\x00"),
        "usr/share/locked/file": b"inside a read-only directory\n",
        "usr/share/blob": random.Random(0).randbytes(64 * 1024),
    })
    # Owner-only modes the ArchLinux image really carries (etc/shadow,
    # var/lib/private, ...), and a setuid program like its dbus helper.
    write_tree(base, {
        "etc/shadow": b"root:*::::::\n",
        "var/lib/private/state": b"private\n",
        "usr/bin/owner-only": b"#!/bin/sh\n",
        "usr/bin/setuid-helper": b"#!/bin/sh\n",
    })
    (base / "etc/shadow").chmod(0o600)
    (base / "var/lib/private/state").chmod(0o600)
    (base / "var/lib/private").chmod(0o700)
    (base / "usr/bin/owner-only").chmod(0o500)
    (base / "usr/share/locked").chmod(0o555)
    (base / "usr/lib/link").symlink_to("libvulkan_freedreno.so")
    image = scratch / "ArchLinux.sqsh"
    # The build sandbox refuses setuid and setgid modes, so the image records
    # them as pseudo-file modes.
    subprocess.run(["mksquashfs", str(base), str(image), "-noappend", "-quiet",
                    "-p", "usr/bin/setuid-helper m 4755 0 0",
                    "-p", "var/lib/private m 2700 0 0"], check=True,
                   stdout=subprocess.DEVNULL)
    subprocess.run(["chmod", "-R", "u+rwX", str(base)], check=True)
    gallium = "libgallium-26.1.2-arch1.1.so"
    return [
        image,
        tar_zst(scratch / "mesa", {
            f"usr/lib/{gallium}": b"x86_64 gallium\n",
            f"usr/lib32/{gallium}": b"i686 gallium\n",
            "usr/share/glvnd/egl_vendor.d/50_mesa.json": b"{}\n",
            # Owner-only members in a package.
            "usr/lib/libowner-only.so": b"x\n",
            "usr/share/licenses/owner-only/license.rst": b"x\n",
        }, modes={
            "usr/lib/libowner-only.so": 0o700,
            "usr/share/licenses/owner-only": 0o700,
            "usr/share/licenses/owner-only/license.rst": 0o600,
        }),
        tar_zst(scratch / "freedreno", {
            "usr/share/vulkan/icd.d/freedreno_icd.x86_64.json": b"{}\n",
            "usr/share/vulkan/icd.d/freedreno_icd.i686.json": b"{}\n",
            "usr/lib/libvulkan_freedreno.so": elf(icd_machine),
            "usr/lib32/libvulkan_freedreno.so": elf(b"\x03\x00"),
        }),
        tar_zst(scratch / "libraries", {
            "usr/lib/libdisplay-info.so.3": b"x\n",
            "usr/lib32/libdisplay-info.so.3": b"x\n",
            "usr/lib/libxcb-keysyms.so.1": b"x\n",
            "usr/lib32/libxcb-keysyms.so.1": b"x\n",
        }),
    ]


class FexUnpackTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(lambda: subprocess.run(["chmod", "-R", "u+w", temporary.name], check=False))
        self.root = Path(temporary.name)
        # korrid creates the work directory inside the contribution directory.
        self.contribution = self.root / "cache/fex/rootfs"
        self.work = self.contribution / ".tmp-fixture"
        self.work.mkdir(parents=True)
        self.files = fixtures(self.root / "fixtures")

    def run_unpack(self, *arguments):
        return subprocess.run(["bash", str(HERE / "unpack.sh"), *map(str, arguments)],
                              capture_output=True, text=True, timeout=60)

    def test_unpacks_the_squashfs_and_overlays_in_order_into_the_work_directory(self):
        result = self.run_unpack(self.work, *self.files)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual((self.work / "etc/os-release").read_text(), "NAME=Fixture\n")
        self.assertEqual((self.work / "usr/lib/libvulkan_freedreno.so").read_bytes()[18:20], b"\x3e\x00")
        self.assertEqual((self.work / "usr/lib/libgallium-26.1.2-arch1.1.so").read_text(), "x86_64 gallium\n")
        self.assertEqual((self.work / "usr/share/locked/file").read_text(), "inside a read-only directory\n")
        self.assertTrue((self.work / "usr/lib/link").is_symlink())
        for metadata in (".PKGINFO", ".MTREE"):
            self.assertFalse((self.work / metadata).exists())
        # korrid flips the tree read-only and renames it; the program leaves
        # it writable and writes nowhere else.
        self.assertTrue((self.work / "etc/os-release").stat().st_mode & 0o200)
        self.assertEqual(sorted(p.name for p in self.contribution.iterdir()), [".tmp-fixture"])

    def tree(self):
        """Every unpacked file and directory; symlinks have no modes of their own."""
        for path in [self.work, *self.work.rglob("*")]:
            if not path.is_symlink():
                yield path

    def test_owner_only_modes_become_group_readable_and_never_group_writable(self):
        # The game user reads the cache through POSIX ACL entries. A file's
        # group bits are its ACL mask, which caps those entries; the Nix
        # sandbox refuses ACLs, so this asserts the bits directly.
        result = self.run_unpack(self.work, *self.files)
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in self.tree():
            mode = path.lstat().st_mode
            with self.subTest(path=str(path.relative_to(self.work)), mode=oct(mode)):
                self.assertTrue(mode & stat.S_IRGRP)
                if stat.S_ISDIR(mode):
                    self.assertTrue(mode & stat.S_IXGRP)
                self.assertFalse(mode & stat.S_IWGRP)
                self.assertFalse(mode & (stat.S_ISUID | stat.S_ISGID))
        for executable in ("usr/bin/owner-only", "usr/bin/setuid-helper", "usr/lib/libowner-only.so"):
            self.assertTrue((self.work / executable).stat().st_mode & stat.S_IXGRP, executable)
        self.assertEqual(stat.S_IMODE((self.work / "etc/shadow").stat().st_mode), 0o640)

    def test_game_user_reads_the_tree_through_the_device_cache_acl(self):
        if shutil.which("setfacl") is None:
            self.skipTest("setfacl is not installed")
        probe = self.root / "acl-probe"
        probe.mkdir()
        if subprocess.run(["setfacl", "-m", DEVICE_CACHE_ACL, str(probe)],
                          capture_output=True).returncode != 0:
            self.skipTest("this filesystem or sandbox refuses POSIX ACLs")
        # Rebuild the work directory as korrid does on the device: the
        # contribution directory carries the cache ACL, korrid creates the
        # work directory in it and sets 0755.
        self.work.rmdir()
        subprocess.run(["setfacl", "-m", DEVICE_CACHE_ACL, str(self.contribution)], check=True)
        self.work.mkdir()
        self.work.chmod(0o755)
        result = self.run_unpack(self.work, *self.files)
        self.assertEqual(result.returncode, 0, result.stderr)
        checked = set()
        for path in self.tree():
            entries = acl_entries(path)
            needed = "r-x" if path.is_dir() else "r--"
            name = str(path.relative_to(self.work))
            checked.add(name)
            with self.subTest(path=name, acl=entries):
                for tag in (f"user:{GAME_UID}", f"group:{GAME_GID}"):
                    granted = effective(entries, tag)
                    self.assertNotIn("w", granted)
                    for bit in needed.replace("-", ""):
                        self.assertIn(bit, granted)
        # Package members with ordinary modes: the files the RG353M could not read.
        self.assertIn("usr/lib/libgallium-26.1.2-arch1.1.so", checked)
        self.assertIn("usr/share/glvnd/egl_vendor.d/50_mesa.json", checked)

    def test_wrong_freedreno_machine_type_fails(self):
        self.files = fixtures(self.root / "wrong-icd", icd_machine=b"\xb7\x00")
        result = self.run_unpack(self.work, *self.files)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Freedreno ICD is not x86_64", result.stderr)

    def test_missing_overlay_file_fails(self):
        result = self.run_unpack(self.work, *self.files[:3])
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("rootfs is missing usr/lib/libdisplay-info.so.3", result.stderr)

    def test_usage_errors_exit_1_without_stdout(self):
        for arguments in (
            [],
            [self.work],
            ["relative", *self.files],
            [self.root / "missing", *self.files],
            [self.work, self.root / "missing.sqsh", *self.files[1:]],
        ):
            with self.subTest(arguments=arguments):
                result = self.run_unpack(*arguments)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(os.listdir(self.work), [])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Tests for steam-engine-map.py with a stand-in nix; no network, no real map."""
import base64
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "steam-engine-map.py"
spec = importlib.util.spec_from_file_location("steam_engine_map", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

# A made-up map: the shape the build accepts, no real addresses.
MAP = b"format korri-steam-engine-map 1\nengine sha256 00\nstatus pass\nslot X Y 1 deadbeef\n"
MAP_X86 = b"format korri-steam-engine-map 1\nengine sha256 11\nstatus pass\nslot X Y 1 feedbeef\n"
# The secret's layout: one map per system.
MAPS = {"aarch64-linux/engine.map": MAP, "x86_64-linux/engine.map": MAP_X86}


def secret(files):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            if data is None:
                info.type = tarfile.DIRTYPE
                archive.addfile(info)
                continue
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return base64.b64encode(raw.getvalue()).decode()


class SteamEngineMapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.env_file = self.root / "github-env"
        self.path_file = self.root / "github-path"
        self.env_file.touch()
        self.path_file.touch()
        # The stand-in nix prints the arguments it got.
        self.real = self.root / "real-nix"
        self.real.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n")
        self.real.chmod(0o755)

    def run_setup(self, value):
        env = {**os.environ, "RUNNER_TEMP": str(self.root), "GITHUB_ENV": str(self.env_file),
               "GITHUB_PATH": str(self.path_file), "STEAM_ENGINE_REAL_NIX": str(self.real),
               tool.SECRET: value}
        return subprocess.run([sys.executable, str(SCRIPT), "setup"], env=env,
                              capture_output=True, text=True)

    def test_without_the_secret_nothing_changes(self):
        result = self.run_setup("")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("empty public map", result.stdout)
        self.assertEqual(self.path_file.read_text(), "")
        self.assertFalse((self.root / "steam-engine-map").exists())

    def test_the_map_is_private_and_the_shim_overrides_only_this_flake(self):
        # `tar czf` of the folder also holds the two folder entries.
        value = secret({"./": None, "./aarch64-linux/": None, "./x86_64-linux/": None,
                        **{"./" + name: data for name, data in MAPS.items()}})
        result = self.run_setup(value)
        self.assertEqual(result.returncode, 0, result.stderr)
        folder = self.root / "steam-engine-map"
        self.assertEqual(os.stat(folder).st_mode & 0o777, 0o700)
        self.assertEqual(sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()),
                         sorted(MAPS))
        for name, data in MAPS.items():
            self.assertEqual(os.stat(folder / name).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat((folder / name).parent).st_mode & 0o777, 0o700)
            self.assertEqual((folder / name).read_bytes(), data)
        # Neither the secret nor any map line reaches the job's output.
        for output in (result.stdout, result.stderr):
            self.assertNotIn(value, output)
            self.assertNotIn("deadbeef", output)
            self.assertNotIn("feedbeef", output)
            self.assertNotIn("sha256", output)
        self.assertIn(f"STEAM_ENGINE_MAP_DIR={folder}", self.env_file.read_text())
        self.assertIn(f"STEAM_ENGINE_REAL_NIX={self.real}", self.env_file.read_text())
        shim = Path(self.path_file.read_text().strip()) / "nix"
        run = lambda *args: subprocess.run([str(shim), *args], capture_output=True,
                                           text=True, check=True).stdout.splitlines()
        self.assertEqual(run("build", "--no-link", ".#packages.aarch64-linux.korri-plugin-steam"),
                         ["build", "--override-input", "steam-engine-map", f"path:{folder}",
                          "--no-link", ".#packages.aarch64-linux.korri-plugin-steam"])
        self.assertEqual(run("flake", "archive", "--json", ".")[:4],
                         ["flake", "archive", "--override-input", "steam-engine-map"])
        # Other flakes, store paths and other commands pass through.
        self.assertEqual(run("shell", "nixpkgs#jq"), ["shell", "nixpkgs#jq"])
        self.assertEqual(run("path-info", "-r", "/nix/store/x-y"), ["path-info", "-r", "/nix/store/x-y"])
        self.assertEqual(run("--version"), ["--version"])
        self.assertEqual(run("copy", "--to", "file:///c", "/nix/store/x-y"),
                         ["copy", "--to", "file:///c", "/nix/store/x-y"])

    def test_a_wrong_archive_is_refused_without_printing_it(self):
        for files in ({"other": MAP}, {**MAPS, "extra": b"x"},
                      # the one-file layout from before the x86_64 map
                      {"engine.map": MAP},
                      # one system only
                      {"aarch64-linux/engine.map": MAP},
                      {**MAPS, "riscv64-linux/engine.map": MAP},
                      {**MAPS, "x86_64-linux/engine.map": b"status refused\n"}):
            value = secret(files)
            result = self.run_setup(value)
            self.assertEqual(result.returncode, 1, files.keys())
            self.assertNotIn(value, result.stdout + result.stderr)
            self.assertFalse((self.root / "steam-engine-map").exists())
        result = self.run_setup("not base64!")
        self.assertEqual(result.returncode, 1)

    def test_the_closure_check_refuses_the_map_store_path(self):
        folder = self.root / "steam-engine-map"
        paths = self.root / "paths.txt"
        paths.write_text("/nix/store/aaa-korri-plugin\n")
        fake = self.root / "bin"
        fake.mkdir()
        for closure, expected in (("/nix/store/aaa-korri-plugin\n/nix/store/map-source\n", 1),
                                  ("/nix/store/aaa-korri-plugin\n/nix/store/bbb-korri-steam-engine-map\n", 1),
                                  ("/nix/store/aaa-korri-plugin\n", 0)):
            (fake / "nix").write_text(
                "#!/bin/sh\n"
                "case \"$1 $2\" in\n"
                "  'flake archive') echo '{\"inputs\":{\"steam-engine-map\":{\"path\":\"/nix/store/map-source\"}}}' ;;\n"
                f"  *) printf '{closure}' ;;\n"
                "esac\n")
            (fake / "nix").chmod(0o755)
            env = {**os.environ, "PATH": f"{fake}:{os.environ['PATH']}",
                   "STEAM_ENGINE_MAP_DIR": str(folder)}
            result = subprocess.run([sys.executable, str(SCRIPT), "check-closure", str(paths)],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stderr)

    def test_the_host_check_accepts_only_the_private_map_host(self):
        private = "/nix/store/" + "p" * 32 + "-korri-steam-host-0.1.0"
        public = "/nix/store/" + "e" * 32 + "-korri-steam-host-0.1.0"
        other = "/nix/store/" + "o" * 32 + "-korri-steam-host-0.1.0"
        wrapper = "/nix/store/" + "w" * 32 + "-korri-steam-host"
        plugin = "/nix/store/" + "a" * 32 + "-korri-plugin"
        paths = self.root / "paths.txt"
        paths.write_text(plugin + "\n")

        def stand_in(folder, out_path, closure):
            folder.mkdir(exist_ok=True)
            (folder / "nix").write_text(
                "#!/bin/sh\n"
                "case \"$1 $3\" in\n"
                "  *.korri-steam-host.name) echo korri-steam-host-0.1.0 ;;\n"
                f"  *.korri-steam-host.outPath) echo {out_path} ;;\n"
                f"  path-info*) printf '%s\\n' {' '.join(closure)} ;;\n"
                "  *) exit 9 ;;\n"
                "esac\n")
            (folder / "nix").chmod(0o755)

        real = self.root / "real"
        for closure, map_dir, code, said in (
                ([plugin, wrapper, private], True, 0, "is the private map's"),
                ([plugin, wrapper, public], True, 1, "the empty public map's"),
                ([plugin, wrapper, private, other], True, 1, "an unknown"),
                ([plugin, wrapper, public], False, 1, "empty public map"),
                ([plugin], True, 0, "no Steam engine host"),
                ([plugin], False, 0, "no Steam engine host")):
            shim = self.root / "shim"
            stand_in(shim, private, closure)
            stand_in(real, public, closure)
            env = {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}",
                   "STEAM_ENGINE_REAL_NIX": str(real / "nix")}
            env.pop("STEAM_ENGINE_MAP_DIR", None)
            if map_dir:
                env["STEAM_ENGINE_MAP_DIR"] = str(self.root / "steam-engine-map")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "check-host", "aarch64-linux", str(paths)],
                env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, code, (closure, map_dir, result.stderr))
            self.assertIn(said, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

"""Check publication scope against both real flake output sets, without builds."""

import importlib.util
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "publication_checks", ROOT / "nix/publication-checks.py"
)
selection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selection)


def evaluate(attribute, apply=None):
    command = ["nix", "eval", "--json", f".#{attribute}"]
    if apply:
        command += ["--apply", apply]
    return json.loads(subprocess.check_output(command, cwd=ROOT, text=True))


class PublicationChecksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mappings = {
            system: evaluate(f"ci.publicationChecks.{system}")
            for system in selection.SYSTEMS
        }

    def test_every_exported_package_has_reviewed_existing_gates(self):
        for system, mapping in self.mappings.items():
            with self.subTest(system=system):
                packages = evaluate(f"packages.{system}", "builtins.attrNames")
                checks = evaluate(f"ci.checks.{system}", "builtins.attrNames")
                self.assertEqual(set(mapping), set(packages))
                self.assertLessEqual(set(selection.SHARED), set(checks))
                for gates in mapping.values():
                    self.assertIsInstance(gates, list)
                    self.assertLessEqual(set(gates), set(checks))

    def test_netplay_batch_does_not_pull_unrelated_native_runtimes(self):
        for mapping in self.mappings.values():
            checks = selection.select_checks(
                mapping,
                [
                    "korri-plugin-snes9x",
                    "korri-plugin-snes9x2010",
                    "korri-plugin-retroarch",
                ],
            )
            self.assertIn("korri-libretro-netplay", checks)
            self.assertIn("korri-libretro-typecheck", checks)
            for unrelated in (
                "korri-pyxel-native",
                "korri-native-fantasy-runners",
                "korri-cemu-package",
            ):
                self.assertNotIn(unrelated, checks)

    def test_native_gates_still_apply_to_their_packages(self):
        for mapping in self.mappings.values():
            for package, gate in (
                ("korri-plugin-pyxel", "korri-pyxel-native"),
                ("korri-plugin-tic80", "korri-native-fantasy-runners"),
                ("korri-plugin-cemu", "korri-cemu-package"),
                ("korri-plugin-sunshine", "sunshine-korri-input-seat-patch"),
            ):
                self.assertIn(gate, selection.select_checks(mapping, [package]))

    def test_composed_packages_keep_dependency_gates(self):
        for mapping in self.mappings.values():
            steam = selection.select_checks(mapping, ["korri-plugin-steam"])
            self.assertIn("korri-fex-package", steam)
            self.assertIn("korri-proton-package", steam)
            starter = selection.select_checks(mapping, ["korri-plugin-starter-pack"])
            self.assertIn("korri-fake08-package", starter)
            self.assertIn("korri-solarus-plugin", starter)
            self.assertIn("korri-zquest-classic-plugin", starter)

    def test_empty_and_unknown_batches_fail_closed(self):
        for mapping in self.mappings.values():
            for batch in (
                [],
                ["missing"],
                ["korri-plugin-pyxel", ".#checks.x86_64-linux.other"],
            ):
                with self.assertRaises(ValueError):
                    selection.select_checks(mapping, batch)

    def test_duplicate_packages_do_not_repeat_checks(self):
        for mapping in self.mappings.values():
            self.assertEqual(
                selection.select_checks(mapping, ["korri-plugin-pyxel"]),
                selection.select_checks(
                    mapping, ["korri-plugin-pyxel", "korri-plugin-pyxel"]
                ),
            )


if __name__ == "__main__":
    unittest.main()

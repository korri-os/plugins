"""Check publication scope against both real flake output sets, without builds."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
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

    def test_melonds_batch_keeps_pane_overlay_and_netplay_gates(self):
        for mapping in self.mappings.values():
            checks = selection.select_checks(
                mapping, ["korri-plugin-melonds", "korri-plugin-retroarch"]
            )
            for gate in (
                "korri-melonds-admission",
                "korri-retroarch-core-options-overlay",
                "korri-retroarch-netplay-password",
                "korri-retroarch-netplay-host-during-play",
            ):
                self.assertIn(gate, checks)
            self.assertNotIn("korri-pyxel-native", checks)
            self.assertNotIn(
                "korri-melonds-admission",
                selection.select_checks(mapping, ["korri-plugin-retroarch"]),
            )

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


class PublicationPlatformsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mappings = {
            system: evaluate(f"ci.publicationChecks.{system}")
            for system in selection.SYSTEMS
        }
        cls.platforms = {
            system: evaluate(f"ci.publicationPlatforms.{system}")
            for system in selection.SYSTEMS
        }

    def test_existing_x86_only_cores_keep_their_ids_and_x86_outputs(self):
        packages = [
            "korri-plugin-blastem",
            "korri-plugin-pcsx2",
            "korri-plugin-parallel-n64",
            "korri-plugin-mgba",
        ]
        self.assertEqual(
            selection.select_packages(self.mappings, self.platforms, packages, "x86_64-linux"),
            packages,
        )
        self.assertEqual(
            selection.select_packages(self.mappings, self.platforms, packages, "aarch64-linux"),
            ["korri-plugin-mgba"],
        )

    def test_cli_records_the_exact_supported_package_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "packages.txt"
            result = subprocess.run(
                [sys.executable, str(ROOT / "nix/publication-checks.py"),
                 "--system", "aarch64-linux", "--packages-file", str(path),
                 "korri-plugin-blastem", "korri-plugin-mgba"],
                cwd=ROOT, text=True, capture_output=True, check=True,
            )
            self.assertEqual(path.read_text(), "korri-plugin-mgba\n")
            self.assertIn("Skipping korri-plugin-blastem on aarch64-linux", result.stderr)
            self.assertIn(".#ci.checks.aarch64-linux.korri-libretro-netplay", result.stdout)

    def test_no_package_can_be_skipped_on_both_architectures(self):
        platforms = {
            system: values | {"korri-plugin-mgba": False}
            for system, values in self.platforms.items()
        }
        for system in selection.SYSTEMS:
            with self.subTest(system=system), self.assertRaisesRegex(ValueError, "every publication architecture"):
                selection.select_packages(
                    self.mappings, platforms, ["korri-plugin-mgba"], system
                )

    def test_platform_filter_does_not_hide_unknown_packages(self):
        for system in selection.SYSTEMS:
            with self.subTest(system=system), self.assertRaisesRegex(ValueError, "No reviewed publication gates"):
                selection.select_packages(
                    self.mappings, self.platforms, ["missing"], system
                )

    def test_outputs_without_a_core_platform_restriction_are_not_skipped(self):
        packages = ["korri-plugin-pico8", "korri-plugin-pyxel", "korri-plugin-starter-pack"]
        for system in selection.SYSTEMS:
            with self.subTest(system=system):
                self.assertEqual(
                    selection.select_packages(self.mappings, self.platforms, packages, system),
                    packages,
                )


class RetroarchCheckInvocationTest(unittest.TestCase):
    def test_native_prechecks_use_one_build_job_and_keep_the_existing_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkout = root / "checkout with spaces"
            (checkout / "plugins/retroarch").mkdir(parents=True)
            commands = root / "commands"
            commands.mkdir()
            log = root / "commands.jsonl"
            recorder = commands / "record-command"
            recorder.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "command = [Path(sys.argv[0]).name, *sys.argv[1:]]\n"
                "with open(os.environ['COMMAND_LOG'], 'a') as log:\n"
                "    log.write(json.dumps(command) + '\\n')\n"
                "if command[:2] == ['nix', 'eval']:\n"
                "    print('x86_64-linux')\n"
            )
            recorder.chmod(0o755)
            for command in ("bun", "nix"):
                (commands / command).symlink_to(recorder)
            subprocess.run(
                ["bash", str(ROOT / "plugins/retroarch/check.sh")],
                check=True,
                env=os.environ | {
                    "PATH": str(commands) + os.pathsep + os.environ["PATH"],
                    "KORRI_ROOT": str(checkout),
                    "KORRI_CHECKS_ATTRIBUTE": "ci.checks",
                    "COMMAND_LOG": str(log),
                },
            )
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            builds = [call for call in calls if call[:2] == ["nix", "build"]]
            self.assertEqual(len(builds), 1)
            build = builds[0]
            self.assertIn("--max-jobs", build)
            self.assertEqual(build[build.index("--max-jobs") + 1], "1")
            self.assertIn("--print-build-logs", build)
            self.assertEqual(
                [argument for argument in build if "#ci.checks." in argument],
                [f"{checkout}#ci.checks.x86_64-linux.{name}" for name in (
                    "korri-retroarch-settings",
                    "korri-retroarch-netplay-password",
                    "korri-retroarch-netplay-host-during-play",
                )],
            )


if __name__ == "__main__":
    unittest.main()

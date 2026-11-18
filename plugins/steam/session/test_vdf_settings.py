"""Exercise the shipped CLI against Steam-shaped files, without Steam or network."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).with_name("vdf-settings.py")
FIXTURES = Path(__file__).with_name("fixtures")
# packages/default.nix substitutes the name defined once by @korri:proton.
TOOL = "proton-cachyos-11.0-20260601-slr-arm64"


class SteamSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / "config/config.vdf"
        self.config.parent.mkdir()
        self.config.write_bytes((FIXTURES / "config.vdf").read_bytes())
        program = tempfile.TemporaryDirectory()
        self.addCleanup(program.cleanup)
        self.helper = Path(program.name) / "vdf-settings.py"
        self.helper.write_text(HELPER.read_text().replace("@protonToolName@", TOOL))

    def run_helper(self, appid="401710"):
        return subprocess.run(
            [os.environ.get("PYTHON", "python3"), str(self.helper), str(self.home), appid],
            text=True, capture_output=True, check=False,
        )

    def test_preserves_existing_content_and_adds_compat_mapping(self):
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.config.read_text()
        self.assertIn('// Steam-owned comment must survive', config)
        self.assertIn('"Unrelated" "keep\\\\this\\\"value"', config)
        self.assertIn('"999" { "name" "other-proton" }', config)
        self.assertIn('"401710"', config)
        self.assertIn('"0"', config)
        self.assertEqual(config.count(f'"{TOOL}"'), 2)
        self.assertIn('"SteamController_XBoxSupport"\t\t"0"', config)
        self.assertIn('userdata seeds skipped', result.stderr)

    def test_preserves_quoted_braces_conditionals_and_crlf(self):
        content = b'"Braces" "{"\r\n"Platform" "keep" [$LINUX]\r\n'
        self.config.write_bytes(content)
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.config.read_bytes().startswith(content))
        first = self.config.read_bytes()
        self.assertEqual(self.run_helper().returncode, 0)
        self.assertEqual(self.config.read_bytes(), first)

    def test_second_run_is_byte_identical(self):
        self.assertEqual(self.run_helper().returncode, 0)
        first = self.config.read_bytes()
        self.assertEqual(self.run_helper().returncode, 0)
        self.assertEqual(first, self.config.read_bytes())

    def test_merges_localconfig_for_existing_login_only(self):
        local = self.home / "userdata/123/config/localconfig.vdf"
        local.parent.mkdir(parents=True)
        local.write_bytes((FIXTURES / "localconfig.vdf").read_bytes())
        self.assertEqual(self.run_helper().returncode, 0)
        content = local.read_text()
        self.assertIn('"PersonaName" "Keep Me"', content)
        self.assertIn('"401710_eula_2"\t\t"1"', content)
        self.assertIn('"Deck_ConfiguratorInterstitialsVersionSeen_Intro"\t\t"99"', content)
        self.assertNotIn('VersionSeen_GamepadRequired', content)
        first = local.read_bytes()
        self.assertEqual(self.run_helper().returncode, 0)
        self.assertEqual(first, local.read_bytes())
        self.assertFalse((self.home / "userdata/0").exists())

    def test_keeps_an_accepted_eula_version_steam_wrote(self):
        local = self.home / "userdata/123/config/localconfig.vdf"
        local.parent.mkdir(parents=True)
        local.write_text(
            '"UserLocalConfigStore"\n{\n\t"Software"\n\t{\n\t\t"Valve"\n\t\t{\n\t\t\t"Steam"\n\t\t\t{\n'
            '\t\t\t\t"apps"\n\t\t\t\t{\n\t\t\t\t\t"401710"\n\t\t\t\t\t{\n'
            '\t\t\t\t\t\t"401710_eula_1"\t\t"4"\n'
            '\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n')
        self.assertEqual(self.run_helper().returncode, 0)
        content = local.read_text()
        self.assertIn('"401710_eula_1"\t\t"4"', content)
        self.assertIn('"401710_eula_0"\t\t"1"', content)
        self.assertIn('"401710_eula_2"\t\t"1"', content)

    def test_rejects_malformed_vdf_without_overwriting_it(self):
        content = '"InstallConfigStore" { "incomplete"'
        self.config.write_text(content)
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_text(), content)

    def test_rejects_non_numeric_appid(self):
        before = self.config.read_bytes()
        self.assertEqual(self.run_helper("401710;false").returncode, 2)
        self.assertEqual(self.config.read_bytes(), before)

    def test_creates_config_and_preserves_private_mode(self):
        self.config.unlink()
        self.assertEqual(self.run_helper().returncode, 0)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.config.chmod(0o640)
        self.assertEqual(self.run_helper("123").returncode, 0)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o640)


    def run_library(self):
        return subprocess.run(
            [os.environ.get("PYTHON", "python3"), str(self.helper), "--library", str(self.home)],
            text=True, capture_output=True, check=False,
        )

    def test_library_points_folder_zero_at_this_home_and_keeps_other_folders(self):
        # korri #498: the account root moved; Steam's list still named the old home.
        old = '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"/var/lib/korri/users/default/steam"\n\t\t"label"\t\t""\n\t}\n\t"1"\n\t{\n\t\t"path"\t\t"/run/media/sd"\n\t}\n}\n'
        for relative in ("steamapps/libraryfolders.vdf", "config/libraryfolders.vdf"):
            path = self.home / relative
            path.parent.mkdir(exist_ok=True)
            path.write_text(old)
        result = self.run_library()
        self.assertEqual(result.returncode, 0, result.stderr)
        for relative in ("steamapps/libraryfolders.vdf", "config/libraryfolders.vdf"):
            text = (self.home / relative).read_text()
            self.assertIn(f'"path"\t\t"{self.home}"', text)
            self.assertIn('"/run/media/sd"', text)
            self.assertNotIn("/users/default/", text)
            self.assertIn('"label"\t\t""', text)
        first = (self.home / "steamapps/libraryfolders.vdf").read_bytes()
        self.assertEqual(self.run_library().returncode, 0)
        self.assertEqual((self.home / "steamapps/libraryfolders.vdf").read_bytes(), first)

    def test_library_creates_nothing_and_refuses_a_broken_file(self):
        result = self.run_library()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home / "steamapps/libraryfolders.vdf").exists())
        broken = self.home / "config/libraryfolders.vdf"
        broken.write_text('"libraryfolders" { "0" {')
        result = self.run_library()
        self.assertEqual(result.returncode, 126)
        self.assertEqual(broken.read_text(), '"libraryfolders" { "0" {')


    def test_engine_mapping_creates_or_merges_only_the_default_tool(self):
        steam = self.home / "engine"
        run = lambda: subprocess.run(
            [os.environ.get("PYTHON", "python3"), str(self.helper), "--engine", str(steam)],
            text=True, capture_output=True, check=False,
        )
        result = run()
        self.assertEqual(result.returncode, 0, result.stderr)
        config = (steam / "config/config.vdf").read_text()
        self.assertIn(f'"name"\t\t"{TOOL}"', config)
        self.assertNotIn("SteamController", config)
        self.assertEqual((steam / "config/config.vdf").stat().st_mode & 0o777, 0o600)
        engine_written = config.replace('"InstallConfigStore"\n{', '"InstallConfigStore"\n{\n\t"Other"\t\t"kept"', 1)
        (steam / "config/config.vdf").write_text(engine_written)
        self.assertEqual(run().returncode, 0)
        self.assertEqual((steam / "config/config.vdf").read_text(), engine_written)


if __name__ == "__main__":
    unittest.main()

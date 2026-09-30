#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 nix
"""Exercise both CI consumers against Nix's real effective configuration."""

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / ".github/workflows/trust-plugin-caches.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("trust_plugin_caches", HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def environment(directory):
    return os.environ | {
        "NIX_CONF_DIR": directory,
        "NIX_USER_CONF_FILES": "/dev/null",
        "NIX_CONFIG": "experimental-features = nix-command flakes\nrequire-sigs = false\n",
        "GITHUB_ENV": str(Path(directory) / "github-env"),
    }


class CacheConfigurationTest(unittest.TestCase):
    def test_effective_configuration_and_github_environment(self):
        helper = load_helper()
        for include_core in (False, True):
            with self.subTest(include_core=include_core), tempfile.TemporaryDirectory() as directory:
                env = environment(directory)
                settings = helper.cache_settings(ROOT, env, include_core=include_core)
                all_settings = helper.cache_settings(ROOT, env, include_core=True)
                env["NIX_CONFIG"] += (
                    "extra-substituters = https://retained.example.invalid/\n"
                    "extra-trusted-public-keys = " + all_settings["publicKeys"][0] + "\n"
                )
                baseline = helper.effective_config(env)
                command = ["python3", str(HELPER)] + (["--include-core"] if include_core else [])
                subprocess.run(command, cwd=ROOT, env=env, check=True)
                exported = Path(env["GITHUB_ENV"]).read_text().splitlines()
                self.assertTrue(exported[0].startswith("NIX_CONFIG<<"))
                self.assertEqual(exported[-1], exported[0].split("<<", 1)[1])
                config = "\n".join(exported[1:-1])
                effective = helper.effective_config(env | {"NIX_CONFIG": config})
                self.assertTrue(effective["require-sigs"]["value"])
                self.assertEqual(
                    set(effective["substituters"]["value"]),
                    set(baseline["substituters"]["value"]) | set(settings["substituters"]),
                )
                self.assertEqual(
                    set(effective["trusted-public-keys"]["value"]),
                    set(baseline["trusted-public-keys"]["value"]) | set(settings["publicKeys"]),
                )
                self.assertIn("https://cache.nixos.org/", effective["substituters"]["value"])
                self.assertIn("experimental-features = nix-command flakes", config)
                self.assertEqual(len(settings["substituters"]), 3 if include_core else 2)
                if not include_core:
                    self.assertEqual(len(settings["publicKeys"]), 1)

    def test_publishing_refuses_inherited_core_cache_before_exporting_config(self):
        helper = load_helper()
        with tempfile.TemporaryDirectory() as directory:
            env = environment(directory)
            publishing = helper.cache_settings(ROOT, env)
            lifecycle = helper.cache_settings(ROOT, env, include_core=True)
            core_url = next(iter(set(lifecycle["substituters"]) - set(publishing["substituters"])))
            aliases = [core_url, core_url.replace('github.com/', 'github.com:443/'),
                       core_url.replace('github.com/', 'GITHUB.COM/')]
            baseline = env["NIX_CONFIG"]
            for alias in aliases:
                with self.subTest(alias=alias):
                    env["NIX_CONFIG"] = baseline + f"extra-substituters = {alias}?priority=60\n"
                    result = subprocess.run(["python3", str(HELPER)], cwd=ROOT, env=env, text=True, capture_output=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("Publishing builds must start without the Core cache", result.stderr)
                    self.assertFalse(Path(env["GITHUB_ENV"]).exists())
            subprocess.run(["python3", str(HELPER), "--include-core"], cwd=ROOT, env=env, check=True)
            self.assertTrue(Path(env["GITHUB_ENV"]).exists())


if __name__ == "__main__":
    unittest.main()

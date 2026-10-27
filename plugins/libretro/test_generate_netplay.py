#!/usr/bin/env python3
"""Boundary tests of the build-time generator, using real native libraries."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GENERATOR = Path(__file__).with_name("generate-netplay.py")


class GenerateNetplay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.template = self.root / "template.ts"
        self.template.write_text("export const runner = {\n    // @netplay@\n}\n")
        self.info = self.root / "core.info"
        self.core = self.root / "core.so"
        self.output = self.root / "plugin.ts"

    def generate(self):
        return subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--template",
                str(self.template),
                "--core-info",
                str(self.info),
                "--core",
                str(self.core),
                "--output",
                str(self.output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_basic_serialized_missing_and_commented_flags_do_not_probe(self):
        for info in [
            None,
            "",
            '# savestate_features = "deterministic"\n',
            'savestate_features = "basic"\n',
            'savestate_features = "serialized"\n',
        ]:
            with self.subTest(info=info):
                if info is not None:
                    self.info.write_text(info)
                result = self.generate()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("netplay", self.output.read_text())
                self.assertFalse(self.core.exists())

    def test_deterministic_requires_a_loadable_core(self):
        self.info.write_text('savestate_features = "deterministic"\n')
        self.assertNotEqual(self.generate().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_duplicate_determinism_is_refused(self):
        self.info.write_text('savestate_features = "deterministic"\n' * 2)
        self.assertNotEqual(self.generate().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_metadata_is_read_from_the_library_and_json_escaped(self):
        self.info.write_text('savestate_features = "deterministic"\n')
        source = self.root / "core.c"
        source.write_text(r"""
#include <stdbool.h>
struct retro_system_info {
    const char *library_name, *library_version, *valid_extensions;
    bool need_fullpath, block_extract;
};
void retro_get_system_info(struct retro_system_info *info) {
    info->library_name = "Library with \"quotes\"";
    info->library_version = "version-from-so\\not-info";
}
""")
        subprocess.run(
            [
                os.environ.get("CC", "cc"),
                "-shared",
                "-fPIC",
                str(source),
                "-o",
                str(self.core),
            ],
            check=True,
        )
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stderr)
        line = self.output.read_text().splitlines()[1]
        self.assertEqual(
            json.loads(line.strip().removeprefix("netplay: ").removesuffix(",")),
            {
                "library": 'Library with "quotes"',
                "version": "version-from-so\\not-info",
            },
        )


if __name__ == "__main__":
    unittest.main()

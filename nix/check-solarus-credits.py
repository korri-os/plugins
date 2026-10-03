#!/usr/bin/env nix
#! nix shell nixpkgs#python3 --command python3
"""Compare delivered credits with the actual pinned first-party wiki record."""

import json
from pathlib import Path
import sys

source, notices = map(Path, sys.argv[1:])
raw = source.read_bytes()
page = json.loads(raw)
assert page["format"] == "markdown" and page["content"]
assert (notices / "credits.json").read_bytes() == raw
assert (notices / "credits.md").read_bytes() == page["content"].encode("utf-8")
print("Verified original version-pinned wiki JSON and complete Markdown credits.")

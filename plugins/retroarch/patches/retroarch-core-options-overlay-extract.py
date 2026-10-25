"""Compile native source selection, not a second implementation of its policy."""

import pathlib
import re
import sys

source = pathlib.Path(sys.argv[1]).read_text()
parts = []
for name in (
    "validate_per_core_options",
    "validate_folder_options",
    "runloop_init_core_options_path",
    "runloop_init_core_options",
    "runloop_init_core_variables",
):
    matches = re.findall(
        rf"^static [^\n]*\b{name}\([^;]*?^\{{.*?^}}$",
        source,
        re.MULTILINE | re.DOTALL,
    )
    if len(matches) != 1:
        raise SystemExit(f"expected one complete upstream function: {name}")
    parts.append(matches[0])
pathlib.Path(sys.argv[2]).write_text("\n".join(parts) + "\n")

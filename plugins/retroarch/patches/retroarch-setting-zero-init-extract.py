"""Compile the shipped setting constructors, not a second implementation."""

import pathlib
import re
import sys

source = pathlib.Path(sys.argv[1]).read_text()
output = pathlib.Path(sys.argv[2])

# Keep whole upstream function bodies. Fail closed if a constructor is added,
# removed or renamed; this extractor is deliberately specific to 1.22.2.
CONSTRUCTORS = (
    "setting_action_setting",
    "setting_group_setting",
    "setting_float_setting",
    "setting_uint_setting",
    "setting_size_setting",
    "setting_bind_setting",
    "setting_string_setting",
    "setting_subgroup_setting",
    "setting_bool_setting",
    "setting_int_setting",
)
# setting_string_setting_options fills the result of setting_string_setting.
# It has no result of its own to zero.
declared = set(re.findall(r"^static rarch_setting_t (\w+)\(", source, re.MULTILINE))
expected = {*CONSTRUCTORS, "setting_string_setting_options"}
if declared != expected:
    raise SystemExit(
        f"setting constructors changed; review the regression fixture: "
        f"{sorted(declared ^ expected)}"
    )

parts = []
for name in CONSTRUCTORS:
    matches = re.findall(
        rf"^static rarch_setting_t {name}\([^;]*?^\{{.*?^}}$",
        source,
        re.MULTILINE | re.DOTALL,
    )
    if len(matches) != 1:
        raise SystemExit(f"expected one complete upstream function: {name}")
    parts.append(matches[0])

output.write_text("\n\n".join(parts) + "\n")

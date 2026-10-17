#!/usr/bin/env bash
# Regenerate src-overlay/src/zq/commands.cpp from pristine upstream plus our hook.
set -euo pipefail
state="$(cd "$(dirname "$0")/.." && pwd)"
src="$state/zc-src/src/zq/commands.cpp"
dst="$state/src-overlay/src/zq/commands.cpp"
mkdir -p "$(dirname "$dst")"
cp "$src" "$dst"; chmod u+w "$dst"
# Call our handler first inside zeditor_handle_commands().
python3 - "$dst" <<'PY'
import sys, re
p = sys.argv[1]
s = open(p).read()
needle = "void zeditor_handle_commands()\n{\n"
assert needle in s, "hook point not found"
s = s.replace(needle, "void lh_handle_commands();\n" + needle + "\tlh_handle_commands();\n", 1)
s += '\n#include "zq/lh_recipe.inc"\n'
open(p, "w").write(s)
PY
echo "overlay ready: $dst"

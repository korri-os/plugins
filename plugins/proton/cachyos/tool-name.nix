# Steam's tool name for the pinned Proton-CachyOS artifact, read from plugin.ts
# during Nix evaluation.
#
# Packages must take a plain string here. A build step that ran Core's
# `korri-publish declaration` made Proton's and Steam's output paths depend on
# Core's host build, so every Core host change republished both. This narrow
# reader accepts only the declaration's current form: exactly one `version:` in
# the file, at the start of a line inside the `@korri:proton/cachyos` artifact,
# before any `}`. Any other form stops evaluation.
#
# Core's evaluator stays the source of truth: korri-proton-tool-name asserts
# that `korri-publish declaration` derives the same name from the same source.
{
  lib,
  source ? ../plugin.ts,
}:
let
  text = builtins.readFile source;
  # The literal newline keeps a commented-out `// version:` from matching.
  match = builtins.match (
    ''(.*[^A-Za-z0-9_$])?cachyos: [{][[:space:]]*id: "@korri:proton/cachyos",[^}]*''
    + "\n"
    + ''[ ]*version: "([A-Za-z0-9][A-Za-z0-9._+-]*)",.*''
  ) text;
  versions = (builtins.length (builtins.split "version:" text) - 1) / 2;
in
assert lib.assertMsg (
  versions == 1 && match != null
) "${toString source}: expected one cachyos artifact `version: \"...\"` for the Proton tool name";
"proton-cachyos-${builtins.elemAt match 1}"

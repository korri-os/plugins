# Steam's tool name for the pinned Proton-CachyOS artifact on one Nix system,
# read from plugin.ts during Nix evaluation.
#
# Packages must take a plain string here. A build step that ran Core's
# `korri-publish declaration` made Proton's and Steam's output paths depend on
# Core's host build, so every Core host change republished both. This narrow
# reader accepts only the declaration's current form: the
# `@korri:proton/cachyos` artifact's `platforms` entry for `system`, opened as
# `"<system>": {` and followed directly by its one `version: "..."` line.
# Each supported system must appear exactly once. Any other form stops
# evaluation.
#
# Core's evaluator stays the source of truth: korri-proton-tool-name asserts
# that `korri-publish declaration` derives the same name from the same source.
{
  lib,
  system,
  source ? ../plugin.ts,
}:
let
  text = builtins.readFile source;
  count = needle: (builtins.length (builtins.split needle text) - 1) / 2;
  # The literal newlines keep a commented-out `// version:` from matching.
  match = builtins.match (
    ''.*cachyos: [{][[:space:]]*id: "@korri:proton/cachyos",[[:space:]]*platforms: [{].*''
    + "\n"
    + ''[ ]*"${system}": [{]''
    + "\n"
    + ''[ ]*version: "([A-Za-z0-9][A-Za-z0-9._+-]*)",.*''
  ) text;
in
assert lib.assertMsg (builtins.elem system [
  "x86_64-linux"
  "aarch64-linux"
]) "Proton-CachyOS has no build for ${system}";
assert lib.assertMsg (
  count "version:" == 2
  && count ''"x86_64-linux": [{]'' == 1
  && count ''"aarch64-linux": [{]'' == 1
  && match != null
) "${toString source}: expected one cachyos `\"${system}\": {` entry with its `version: \"...\"` line";
"proton-cachyos-${builtins.elemAt match 0}"

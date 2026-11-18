{
  pkgs,
  runner ? "steam",
}:
pkgs.runCommand
  (if runner == "steam" then "steam-session-steps.sh" else "steam-${runner}-session-steps.sh") { nativeBuildInputs = [ pkgs.bun ]; } ''
  mkdir -p source/packages
  cp ${../plugin.ts} source/plugin.ts
  cp ${./session-steps.ts} source/packages/session-steps.ts
  bun source/packages/session-steps.ts ${runner} > "$out"
''

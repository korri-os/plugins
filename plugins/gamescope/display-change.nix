{ pkgs }:
pkgs.writeShellApplication {
  name = "gamescope-display-change";
  runtimeInputs = [ pkgs.xprop pkgs.xwininfo pkgs.coreutils ];
  text = builtins.readFile ./display-change.sh;
}

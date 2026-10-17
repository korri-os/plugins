{ pkgs }:
pkgs.runCommand "zquest-classic-software-midi" { } ''
  mkdir -p "$out/share/zquestclassic-audio" "$out/share/licenses/freepats"
  ${pkgs.python3}/bin/python3 ${./midi-patches.py} ${pkgs.freepats} \
    "$out/share/zquestclassic-audio/default.cfg"
  substitute ${./allegro.cfg} "$out/share/zquestclassic-audio/allegro.cfg" \
    --subst-var-by patches "$out/share/zquestclassic-audio"
  cp ${pkgs.freepats}/COPYING ${pkgs.freepats}/README "$out/share/licenses/freepats/"
''

{ pkgs, engine }:
let
  audio = import ./audio.nix { inherit pkgs; };
in
pkgs.runCommand "zquest-classic-launcher-${engine.version}" { meta = engine.meta; } ''
  mkdir -p "$out/bin"
  substitute ${./launcher.py} "$out/bin/zplayer" \
    --subst-var-by python ${pkgs.python3} \
    --subst-var-by engine ${engine} \
    --subst-var-by audio ${audio}/share/zquestclassic-audio
  chmod +x "$out/bin/zplayer"
''

{ pkgs, engine }:
let
  dependencies = engine.sourceDependencies;
  recipe = pkgs.lib.fileset.toSource {
    root = ../plugins/zquest-classic;
    fileset = pkgs.lib.fileset.unions [
      ../plugins/zquest-classic/package.nix
      ../plugins/zquest-classic/plugin.ts
      ../plugins/zquest-classic/plugin.nix
      ../plugins/zquest-classic/launcher.py
      ../plugins/zquest-classic/launcher.nix
      ../plugins/zquest-classic/audio.nix
      ../plugins/zquest-classic/allegro.cfg
      ../plugins/zquest-classic/midi-patches.py
      ../plugins/zquest-classic/FindLibuuid.cmake
      ../plugins/zquest-classic/public-assets.nix
      ../plugins/zquest-classic/public-assets.py
      ../plugins/zquest-classic/public-assets-validate.py
      ../plugins/zquest-classic/public-assets-metrics.json
      ../plugins/zquest-classic/tiny5.glyphs.txt
      ../plugins/zquest-classic/tiny5-OFL.txt
      ../plugins/zquest-classic/ASSET-LICENSES.md
      ../plugins/zquest-classic/PUBLIC-CHANGES.txt
      ../plugins/zquest-classic/public-source.nix
      ../plugins/zquest-classic/prepare-public-source.py
      ../plugins/zquest-classic/public-player.patch
      ../plugins/zquest-classic/standalone-quest-path.patch
      ../plugins/zquest-classic/sound-thread-timeout.patch
      ../plugins/zquest-classic/gamepad-input.patch
      ../plugins/zquest-classic/aarch64-disable-x86-tile-simd.patch
    ];
  };
in
pkgs.runCommand "zquest-classic-corresponding-source-${pkgs.stdenv.hostPlatform.system}"
  {
    nativeBuildInputs = [
      pkgs.python3
      pkgs.gnutar
      pkgs.xz
    ];
  }
  ''
    python3 ${./zquest-source-release.py} \
      --source ${engine.publicSource} --recipe ${recipe} \
      --lock ${../flake.lock} --system ${pkgs.stdenv.hostPlatform.system} \
      --audit-script ${./zquest-source-archive-check.py} \
      --dependency stduuid ${dependencies.stduuid} \
      --dependency allegro5 ${dependencies.allegro5} \
      --dependency gme ${dependencies.gme} \
      --dependency poolSTL ${dependencies.poolSTL} \
      --output source
    mkdir -p "$out"
    cp source/SOURCE-AUDIT.txt source/SOURCE-PRUNING.txt "$out/"
    tar --sort=name --mtime=@1 --owner=0 --group=0 --numeric-owner \
      -cJf "$out/zquest-classic-source-${pkgs.stdenv.hostPlatform.system}.tar.xz" source
    (cd "$out"; sha256sum *.tar.xz > SHA256SUMS)
  ''

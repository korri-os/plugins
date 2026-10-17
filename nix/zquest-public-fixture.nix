{ pkgs }:

# Test-only content. Do not add this derivation to the plugin/runtime closure.
pkgs.runCommand "zquest-public-runtime-fixture"
  {
    nativeBuildInputs = [ pkgs.python3 ];
  }
  ''
    mkdir -p "$out"
    for variant in room missing-tiles win; do
      python3 ${./zquest-public-fixture.py} --variant "$variant" "$out/public-$variant.qst"
      python3 ${./zquest-public-fixture.py} --variant "$variant" "repeat-$variant.qst"
      cmp "$out/public-$variant.qst" "repeat-$variant.qst"
    done
    (
      cd "$out"
      echo 'abb02a7aa1810a60892435b596f3426c192ef15182c96799e3db67bdc739cd67  public-room.qst'
      echo 'ad34840bd5efc3d4e8ecfc9a2b16d8166cb82e94e16ef2c214ba343e6eaccbbd  public-missing-tiles.qst'
      echo '088c9c9c0e31ed8cf3316ecab3b4aa4e37faffb307a8666d40438af0c606ab79  public-win.qst'
    ) > "$out/SHA256SUMS"
    (cd "$out" && sha256sum --check SHA256SUMS)
    cp ${./zquest-public-fixture.py} "$out/generate.py"
    cp ${./zquest-public-fixture.md} "$out/README.md"
    cp ${./zquest-public-fixture-LICENSE.txt} "$out/LICENSE.txt"
  ''

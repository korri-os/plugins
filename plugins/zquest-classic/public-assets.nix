# Generated resources only. `source` may be the sanitized corresponding source;
# only slot/version headers, the licensed TTF and vendored Tiny5 glyphs/notices
# are consumed.
{ pkgs, source }:
let
  python = pkgs.buildPackages.python3.withPackages (ps: [ ps.pillow ]);
in
pkgs.runCommand "zquest-classic-public-assets"
  {
    nativeBuildInputs = [ python ];
  }
  ''
    mkdir generator
    cp ${./public-assets.py} generator/public-assets.py
    cp ${./public-assets-metrics.json} generator/public-assets-metrics.json
    cp ${./tiny5.glyphs.txt} generator/tiny5.glyphs.txt
    cp ${./tiny5-OFL.txt} generator/tiny5-OFL.txt
    cp ${./public-assets-validate.py} generator/public-assets-validate.py
    cp ${./ASSET-LICENSES.md} generator/ASSET-LICENSES.md
    python3 generator/public-assets.py \
      --output "$out" \
      --source ${source} \
      --font ${source}/resources/ProggyVector-Regular.ttf
    python3 generator/public-assets-validate.py \
      --resources "$out"
  ''

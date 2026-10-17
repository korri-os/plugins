# Private authoring editor for Lantern Hollow. NOT for publication: it keeps
# upstream's stock resources (default.qst, sfx.dat, fonts) that the public
# player excludes. Same engine commit and pins as the public player.
{
  pkgs,
  extraPatches ? [ ],
}:
let
  inherit (pkgs) lib;
  personal = /home/simonwjackson/code/github/simonwjackson/korri-plugins/plugins/zquest-classic;
  stduuid = pkgs.fetchFromGitHub {
    owner = "mariusbancila";
    repo = "stduuid";
    rev = "3afe7193facd5d674de709fccc44d5055e144d7a";
    sha256 = "1y7jgf45dydq0jlac5clnanwcc22la4y8c83d5i0rp87x2zll6ij";
  };
  allegro5 = pkgs.fetchFromGitHub {
    owner = "connorjclark";
    repo = "allegro5";
    rev = "7fe12cad20d57e79273af0e51dbda897d60d8dfd";
    sha256 = "143ydhf1kig7hab3wg5li5v56x3aiy7wyf0sihbamx112rw5jivc";
  };
  gme = pkgs.fetchFromGitHub {
    owner = "libgme";
    repo = "game-music-emu";
    rev = "05a2aa29e8eae29316804fdd28ceaa96c74a1531";
    sha256 = "0hn5fvfnrcgsyg5k0ls17dcph9h7cr34q9pyjbawvw16qjl6v3sf";
  };
  poolSTL = pkgs.fetchFromGitHub {
    owner = "alugowski";
    repo = "poolSTL";
    rev = "26d95b90aea7c36732a2df50df1c6fa26c96f93e";
    sha256 = "1likzpanrhlqsvdji1dy0ya067knb7ixq4hnw5rl7m87qrj1cjr5";
  };
  upstream = pkgs.fetchFromGitHub {
    owner = "ZQuestClassic";
    repo = "ZQuestClassic";
    rev = "882c906b17e35b4105188e6305ae2929aeba30e3";
    sha256 = "02fs0fm9wih9ly23ivxcvr346cj0dkg7yxsf97q7xzyw6vk36n2y";
  };
in
pkgs.stdenv.mkDerivation {
  pname = "zquest-authoring-editor";
  version = "882c906";
  src = upstream;
  patches = extraPatches;
  nativeBuildInputs = with pkgs; [
    cmake
    ninja
    pkg-config
    flex
    bison
    python3
    perl
  ];
  buildInputs = with pkgs; [
    curl
    freetype
    gtk3
    libGL
    libGLU
    freeglut
    xorg.libX11
    xorg.libXcursor
    xorg.libXext
    xorg.libXfixes
    xorg.libXinerama
    xorg.libXrandr
    xorg.libXrender
    alsa-lib
    libpulseaudio
    openssl
    util-linux
    zlib
  ];
  postPatch = ''
    substitute ${personal}/FindLibuuid.cmake cmake/FindLibuuid.cmake \
      --subst-var-by uuidLib ${lib.getLib pkgs.util-linux} \
      --subst-var-by uuidDev ${pkgs.util-linux.dev}
    substituteInPlace CMakeLists.txt \
      --replace-fail '-Werror=format' '-Werror=format -Wno-error=format-truncation'
  '';
  cmakeGenerator = "Ninja Multi-Config";
  NIX_LDFLAGS = [
    "-L${lib.getLib pkgs.util-linux}/lib"
    "-luuid"
  ];
  cmakeFlags = [
    "-DCOPY_RESOURCES=ON"
    "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"
    "-DWANT_NFD=OFF"
    "-DWANT_ZUPDATER=OFF"
    "-DWANT_WEBSOCKETS=OFF"
    "-DWANT_GIT_HOOKS=OFF"
    "-DWANT_ZC_TESTS=OFF"
    "-DJIT_BACKEND=none"
    "-DFETCHCONTENT_SOURCE_DIR_STDUUID=${stduuid}"
    "-DFETCHCONTENT_SOURCE_DIR_ALLEGRO5=${allegro5}"
    "-DFETCHCONTENT_SOURCE_DIR_GME_EXTERNAL=${gme}"
    "-DFETCHCONTENT_SOURCE_DIR_POOLSTL=${poolSTL}"
  ];
  buildPhase = ''
    runHook preBuild
    cmake --build . --config Release --target zeditor zscript --parallel "$NIX_BUILD_CORES"
    runHook postBuild
  '';
  installPhase = ''
    runHook preInstall
    mkdir -p $out/lib/zquest
    # Keep the editor beside its resource tree; it resolves resources relative to cwd.
    cp -r Release/. $out/lib/zquest/
    mkdir -p $out/bin
    cat > $out/bin/zeditor-run <<EOF
    #!${pkgs.runtimeShell}
    # Run zeditor from a writable copy of the resource tree (it writes cfg/logs).
    set -eu
    work="\''${ZQ_WORKDIR:-\$HOME/.local/state/lantern-hollow/editor-run}"
    if [ ! -e "\$work/.stamp-$out" ]; then
      rm -rf "\$work"; mkdir -p "\$work"
      cp -r $out/lib/zquest/. "\$work/"; chmod -R u+w "\$work"; touch "\$work/.stamp-$out"
    fi
    cd "\$work"
    exec ./zeditor "\$@"
    EOF
    chmod +x $out/bin/zeditor-run
    runHook postInstall
  '';
  meta.platforms = [ "x86_64-linux" ];
}

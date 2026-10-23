{ pkgs }:
pkgs.stdenv.mkDerivation {
  pname = "bitsybox";
  version = "0.2-8.12";
  src = pkgs.fetchzip {
    url = "https://codeberg.org/adamledoux/bitsybox/archive/acd3076d302439ab66af527893a5ee5e728975f5.tar.gz";
    hash = "sha256-FvZoDDzerToqHhRe0R5jyJ1V90m27cEhQSQnscLAjV4=";
  };
  patches = [ ./single-file.patch ];
  nativeBuildInputs = [ pkgs.nodejs ];
  buildInputs = [ pkgs.SDL2 ];
  # Upstream's release target copies demos and guesses an ARM32 SDL path.
  # Use its embedding script and C sources directly for both Linux architectures.
  buildPhase = ''
    runHook preBuild
    node util/embed.js ./src/bitsy/engine ./src/bitsybox
    node util/embed.js ./src/bitsy/font ./src/bitsybox
    $CC src/bitsybox/main.c src/bitsybox/duktape/duktape.c \
      $(sdl2-config --cflags --libs) -lm -DPLATFORM_LIN -o bitsybox
    runHook postBuild
  '';
  installPhase = ''
    runHook preInstall
    install -Dm755 bitsybox "$out/bin/bitsybox"
    install -Dm644 LICENSE.txt "$out/share/licenses/bitsybox/Anti-Capitalist-1.4.txt"
    install -Dm644 res/LICENSE.txt "$out/share/licenses/bitsybox/upstream-res-LICENSE.txt"
    # Preserve the exact MIT license and author notices from the bundled source.
    sed '/^#line 1 "duk_replacements.c"/,$d' \
      src/bitsybox/duktape/duktape.c > "$out/share/licenses/bitsybox/Duktape-notices.txt"
    cp ${./licenses}/* "$out/share/licenses/bitsybox/"
    install -Dm644 ${./README.md} "$out/share/doc/bitsybox/README.md"
    runHook postInstall
  '';
  meta = {
    description = "Native single-file Bitsy player (restricted eligibility license)";
    homepage = "https://codeberg.org/adamledoux/bitsybox";
    license = {
      fullName = "Anti-Capitalist Software License v1.4";
      url = "https://codeberg.org/adamledoux/bitsybox/src/commit/acd3076d302439ab66af527893a5ee5e728975f5/LICENSE.txt";
      free = false;
      redistributable = false;
    };
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
    mainProgram = "bitsybox";
  };
}

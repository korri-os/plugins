{ pkgs }:
let
  inherit (pkgs) lib;
  cemuCommit = "29f2f1fae4631e2317977debd9eacd55cc28dd7d";
  cemuSource = pkgs.fetchFromGitHub {
    owner = "cemu-project";
    repo = "Cemu";
    rev = cemuCommit;
    fetchSubmodules = true;
    hash = "sha256-gNvSmQUWS4dYWsqA9URWNE3+8IK2101onTZ7CB+ouAI=";
  };
  # Cemu uses SDL_HINT_JOYSTICK_HIDAPI_SWITCH2, introduced in SDL 3.4.
  # The publisher lock's SDL 3.2.26 fails to compile that controller provider.
  sdl3 = pkgs.sdl3.overrideAttrs (old: {
    version = "3.4.18";
    buildInputs = old.buildInputs ++ [ pkgs.xorg.libXtst ];
    # SDL 3.4 moved the native Zenity implementation; retain nixpkgs' path fix.
    postPatch =
      builtins.replaceStrings
        [ "src/video/wayland/SDL_waylandmessagebox.c" ]
        [ "src/dialog/unix/SDL_zenitymessagebox.c" ]
        old.postPatch;
    src = pkgs.fetchFromGitHub {
      owner = "libsdl-org";
      repo = "SDL";
      tag = "release-3.4.18";
      hash = "sha256-3dP4FJ5OvZI6UPykJpE3hTH6kdW+Nn7gUSf3yiPCobo=";
    };
  });
  # The publisher lock has fmt 12.0.0; Cemu requires >= 12.1.
  fmt = pkgs.fmt.overrideAttrs (_: {
    version = "12.1.0";
    src = pkgs.fetchFromGitHub {
      owner = "fmtlib";
      repo = "fmt";
      tag = "12.1.0";
      hash = "sha256-ZmI1Dv0ZabPlxa02OpERI47jp7zFfjpeWCy1WyuPYZ0=";
    };
  });
  graphicPacksLicense = pkgs.fetchurl {
    url = "https://raw.githubusercontent.com/cemu-project/cemu_graphic_packs/975f3759d7837da5a374150347d3202360b13ca3/LICENSE.md";
    hash = "sha256-VTfU0Qt2uBtujf2LZESApLHvozL7sM22ESbFvnge97Q=";
  };
  graphicPacks = pkgs.fetchurl {
    url = "https://github.com/cemu-project/cemu_graphic_packs/releases/download/Github989/graphicPacks989.zip";
    hash = "sha256-crRwikdqgQmQo+4QJu/Cp7HBM9TkZ+uNjrwjxDagPLs=";
  };
  licenses = import ./licenses.nix {
    inherit
      pkgs
      cemuSource
      sdl3
      fmt
      ;
  };
in
# Temporary Cemu-only Turnip pin. Replace with patched 26.2.x; see README.
assert !pkgs.stdenv.hostPlatform.isAarch64 || pkgs.mesa.version == "25.3.2";
pkgs.llvmPackages.stdenv.mkDerivation {
  pname = "cemu";
  version = "0-unstable-2026-10-22-${builtins.substring 0 7 cemuCommit}";
  src = cemuSource;
  nativeBuildInputs = with pkgs; [
    cmake
    ninja
    pkg-config
    nasm
    wayland-scanner
    wxwidgets_3_3
    unzip
    llvmPackages.llvm
    # Wrapped ld.lld preserves Nix RUNPATHs; the raw lld package does not.
    llvmPackages.bintools
  ];
  buildInputs = with pkgs; [
    sdl3
    boost
    curl
    fmt
    glm
    glslang
    gtk3
    hidapi
    libpng
    libusb1
    libwebp
    libzip
    openssl
    pugixml
    rapidjson
    libsodium
    spirv-tools
    vulkan-headers
    vulkan-loader
    wayland
    wayland-protocols
    wxwidgets_3_3
    zarchive
    bluez
    libpulseaudio
    alsa-lib
    libGL
    xorg.libX11
    xorg.libXrender
    zstd
  ];
  strictDeps = true;
  # Upstream release IPO remains ON. Clang uses lld for its LLVM bitcode.
  cmakeFlags = [
    "-DENABLE_VCPKG=OFF"
    "-DENABLE_DISCORD_RPC=OFF"
    "-DENABLE_FERAL_GAMEMODE=OFF"
    "-DENABLE_WAYLAND=ON"
    "-DENABLE_OPENGL=ON"
    "-DENABLE_VULKAN=ON"
    "-DALLOW_PORTABLE=OFF"
    "-DCMAKE_BUILD_TYPE=Release"
    "-DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld"
    "-DCMAKE_CXX_COMPILER_AR=${pkgs.llvmPackages.llvm}/bin/llvm-ar"
    "-DCMAKE_CXX_COMPILER_RANLIB=${pkgs.llvmPackages.llvm}/bin/llvm-ranlib"
    "-DCMAKE_C_COMPILER_AR=${pkgs.llvmPackages.llvm}/bin/llvm-ar"
    "-DCMAKE_C_COMPILER_RANLIB=${pkgs.llvmPackages.llvm}/bin/llvm-ranlib"
    "-DCMAKE_POLICY_VERSION_MINIMUM=3.21.1"
  ];
  preConfigure = ''
    substituteInPlace CMakeLists.txt \
      --replace-fail 'find_package(cubeb)' '# Use the bundled Cubeb submodule' \
      --replace-fail 'add_definitions(-DEMULATOR_HASH=''${GIT_HASH})' \
        'add_definitions(-DEMULATOR_HASH=${builtins.substring 0 7 cemuCommit})'
  '';
  installPhase = ''
    runHook preInstall
    install -Dm755 ../bin/Cemu_release "$out/bin/Cemu"
    mkdir -p "$out/share/Cemu" "$out/nix-support/cemu-build"
    cp -R ../bin/gameProfiles ../bin/resources "$out/share/Cemu/"
    install -m644 ${./settings.xml} "$out/share/Cemu/settings.xml"
    mkdir -p "$out/share/Cemu/graphicPacks/downloadedGraphicPacks"
    unzip -q ${graphicPacks} -d "$out/share/Cemu/graphicPacks/downloadedGraphicPacks"
    # Optional native-aspect presets follow Github989's 4:3/5:4 pattern (README).
    patch --batch --fuzz=0 -p1 -d "$out/share/Cemu/graphicPacks/downloadedGraphicPacks" \
      < ${./graphic-packs-native-aspect.patch}
    printf '%s' 'graphicPacks989.zip' > "$out/share/Cemu/graphicPacks/downloadedGraphicPacks/version.txt"
    substitute ${./wrapper.sh} "$out/bin/cemu" \
      --subst-var-by shell ${pkgs.runtimeShell} \
      --subst-var-by coreutils ${pkgs.coreutils} \
      --subst-var-by turnipDriver ${lib.escapeShellArg (
        lib.optionalString pkgs.stdenv.hostPlatform.isAarch64 ''
          export VK_DRIVER_FILES="${pkgs.mesa}/share/vulkan/icd.d/freedreno_icd.aarch64.json"
          export VK_ICD_FILENAMES="$VK_DRIVER_FILES"
        ''
      )} \
      --subst-var-by libraries ${
        lib.makeLibraryPath [
          pkgs.vulkan-loader
          pkgs.libpulseaudio
          pkgs.alsa-lib
        ]
      } \
      --subst-var out
    chmod +x "$out/bin/cemu"

    # Actual object files, not just planned Ninja commands, prove both backends.
    evidence="$out/nix-support/cemu-build"
    for backend in pulse alsa; do
      object=$(find dependencies/cubeb -name "cubeb_$backend.c.o" -type f -size +0c -print -quit)
      test -n "$object" || { echo "Cubeb $backend source was not compiled" >&2; exit 1; }
      printf 'compiled=%s\n' "$object" >> "$evidence/cubeb.txt"
    done
    ${pkgs.binutils}/bin/readelf -h "$out/bin/Cemu" > "$evidence/elf-header.txt"
    ${pkgs.binutils}/bin/readelf -d "$out/bin/Cemu" > "$evidence/elf-dynamic.txt"
    if grep -q libcubeb "$evidence/elf-dynamic.txt"; then
      echo 'Cemu unexpectedly links dynamic Cubeb' >&2; exit 1
    fi
    find "$out/share/Cemu/gameProfiles/default" -name '*.ini' -type f > "$evidence/gameProfiles.txt"
    test -s "$evidence/gameProfiles.txt"
    test -s "$out/share/Cemu/resources/sharedFonts/CafeCn.ttf"
    echo 'resources/sharedFonts/CafeCn.ttf present' > "$evidence/resources.txt"
    find "$out/share/Cemu/graphicPacks" -name rules.txt -type f > "$evidence/graphicPacks.txt"
    test -s "$evidence/graphicPacks.txt"
    grep -q 'BreathOfTheWild' "$evidence/graphicPacks.txt"
    # Diagnostics must not pull compiler and development closures onto devices.
    sed -E 's@/nix/store/[a-z0-9]{32}-@/nix/store/<hash>-@g' \
      compile_commands.json > "$evidence/compile_commands.json"
    grep -E 'flto|Cemu_release.*LINKER' build.ninja | \
      sed -E 's@/nix/store/[a-z0-9]{32}-@/nix/store/<hash>-@g' > "$evidence/ipo.txt"
    test -s "$evidence/ipo.txt"
    $CXX --version | sed -n '1p' > "$evidence/compiler.txt"
    install -Dm644 ${graphicPacksLicense} "$out/share/licenses/cemu-graphic-packs/LICENSE.md"
    mkdir -p "$out/share/licenses/cemu"
    cp -R ${licenses}/. "$out/share/licenses/cemu/"
    runHook postInstall
  '';
  passthru = {
    inherit
      cemuCommit
      graphicPacks
      licenses
      fmt
      sdl3
      ;
  };
  meta = {
    description = "Cemu Wii U emulator with bundled offline graphic packs";
    homepage = "https://github.com/cemu-project/Cemu";
    license = [
      lib.licenses.mpl20
      lib.licenses.cc0
      lib.licenses.isc
      lib.licenses.mit
      lib.licenses.asl20
      lib.licenses.bsd3
      lib.licenses.zlib
      lib.licenses.ofl
    ];
    mainProgram = "cemu";
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
  };
}

{ pkgs }:
let
  inherit (pkgs) lib;
in
# Private to Cemu: no system Mesa overlay and no Gallium/OpenGL driver.
(pkgs.mesa.override {
  vulkanDrivers = [ "freedreno" ];
  galliumDrivers = [ ];
  vulkanLayers = [ ];
  withValgrind = false;
}).overrideAttrs
  (_: {
    pname = "mesa-turnip-cemu-fmadz";
    version = "26.2.5";
    src = pkgs.fetchurl {
      url = "https://archive.mesa3d.org/mesa-26.2.5.tar.xz";
      hash = "sha256-eUs9FykHXa5+vUfHKDt8oM213sZo9/EcwKXYL2E4oKU=";
    };
    patches = [ ./patches/mesa-26.2-ir3-fmadz.patch ];
    # No GL headers or OpenCL artifacts are installed by this ICD-only build.
    postPatch = "patchShebangs .";
    preConfigure = "";
    outputs = [ "out" ];
    buildInputs = with pkgs; [
      elfutils
      expat
      libdrm
      libunwind
      xorg.libX11
      xorg.libxcb
      xorg.libXrandr
      xorg.libxshmfence
      xorg.xorgproto
      wayland
      wayland-protocols
      zlib
      zstd
    ];
    mesonAutoFeatures = "disabled";
    mesonFlags = [
      "-Dplatforms=x11,wayland"
      "-Dvulkan-drivers=freedreno"
      "-Dgallium-drivers="
      "-Dvulkan-layers="
      "-Dfreedreno-kmds=msm"
      "-Dopengl=false"
      "-Dglx=disabled"
      "-Degl=disabled"
      "-Dgbm=disabled"
      "-Dglvnd=disabled"
      "-Dllvm=disabled"
      "-Dgallium-rusticl=false"
      "-Dvideo-codecs="
      "-Dtools="
      "-Dvalgrind=disabled"
      "-Dbuild-tests=false"
    ];
    doCheck = true;
    checkPhase = ''
      runHook preCheck
      meson test --no-rebuild --print-errorlogs ir3_disasm ir3_delay_test
      runHook postCheck
    '';
    postInstall = ''
      mkdir -p "$out/nix-support"
      cp ${./patches/mesa-26.2-ir3-fmadz.patch} "$out/nix-support/mesa-26.2-ir3-fmadz.patch"
    '';
    postFixup = ''
      ${lib.getExe pkgs.jdupes} --hard-links --link-soft --recurse "$out"
    '';
  })

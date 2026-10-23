{ pkgs }:
let
  inherit (pkgs) lib;
  # SDL2-compat uses an SDL3 variant, not the full desktop SDL3 package. Reuse
  # its actual dependency so discovery has Eden's ABI and adds no second SDL.
  sdl3Dependencies = builtins.filter (
    dependency: (dependency.pname or "") == "sdl3"
  ) pkgs.SDL2.buildInputs;
  sdl3 =
    assert builtins.length sdl3Dependencies == 1;
    (builtins.head sdl3Dependencies).lib;
  # The two current ARM targets use Adreno. Native x86 device policy is unchanged.
  selectVulkan = lib.optionalString pkgs.stdenv.hostPlatform.isAarch64 ''
    "${pkgs.python3}/bin/python3" "@launcher@/libexec/vulkan_device.py" "$config" \
      "${pkgs.vulkan-tools}/bin/vulkaninfo" "${pkgs.crudini}/bin/crudini"
  '';
  selectP1 = lib.optionalString pkgs.stdenv.hostPlatform.isAarch64 ''
    "${pkgs.python3}/bin/python3" "@launcher@/libexec/p1_controls.py" "$config" \
      "@launcher@/libexec/p1-controls.ini" \
      "${lib.getLib pkgs.SDL2}/lib/libSDL2-2.0.so.0" \
      "${sdl3}/lib/libSDL3.so.0" "${pkgs.crudini}/bin/crudini"
  '';
in
# Keep the upstream Eden output unchanged so Hydra's signed build is reused.
pkgs.runCommand "eden-korri-${pkgs.eden.version}"
  {
    passthru = {
      upstream = pkgs.eden;
    };
    meta = pkgs.eden.meta // {
      mainProgram = "eden";
    };
  }
  ''
    mkdir -p "$out/bin"
    ${lib.optionalString pkgs.stdenv.hostPlatform.isAarch64 ''
      mkdir -p "$out/libexec"
      cp ${./vulkan_device.py} "$out/libexec/vulkan_device.py"
      cp ${./p1_controls.py} "$out/libexec/p1_controls.py"
      cp ${./p1-controls.ini} "$out/libexec/p1-controls.ini"
    ''}
    substitute ${./wrapper.sh} "$out/bin/eden" \
      --subst-var-by selectVulkan ${lib.escapeShellArg selectVulkan} \
      --subst-var-by selectP1 ${lib.escapeShellArg selectP1} \
      --subst-var-by shell ${pkgs.runtimeShell} \
      --subst-var-by coreutils ${pkgs.coreutils} \
      --subst-var-by crudini ${pkgs.crudini} \
      --subst-var-by eden ${pkgs.eden}
    ${lib.optionalString pkgs.stdenv.hostPlatform.isAarch64 ''
      substituteInPlace "$out/bin/eden" --replace-fail '@launcher@' "$out"
    ''}
    chmod +x "$out/bin/eden"
  ''

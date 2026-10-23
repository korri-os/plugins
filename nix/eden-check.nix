{
  pkgs,
  package,
  edenPackage,
  contract,
}:
let
  upstream = edenPackage.upstream;
  # This gate deliberately rejects the older recipe that disabled ARM fastmem.
  unpatched =
    assert upstream.version == "0.2.1";
    assert (upstream.patches or [ ]) == [ ];
    true;
  buildFlags = pkgs.writeText "eden-build-flags.txt" (
    builtins.toJSON {
      version = upstream.version;
      cmakeFlags = upstream.cmakeFlags;
      patches = upstream.patches or [ ];
    }
  );
  contractSource = builtins.path {
    path = contract;
    name = "korrid.ts";
  };
in
assert unpatched;
pkgs.runCommand "korri-eden-package-check"
  {
    nativeBuildInputs = with pkgs; [
      bun
      typescript
      python3
      mypy
      ruff
      shellcheck
      binutils
      strace
      xorg.xorgserver
      xorg.xauth
    ];
  }
  ''
    mkdir -p work/plugins/eden work/contracts/generated
    cp ${package}/plugin.ts work/plugins/eden/plugin.ts
    cp ${../plugins/eden/plugin.test.ts} work/plugins/eden/plugin.test.ts
    cp ${../plugins/eden/vulkan_device.py} work/plugins/eden/vulkan_device.py
    cp ${../plugins/eden/vulkan_device_test.py} work/plugins/eden/vulkan_device_test.py
    cp ${../plugins/eden/p1_controls.py} work/plugins/eden/p1_controls.py
    cp ${../plugins/eden/p1_controls_test.py} work/plugins/eden/p1_controls_test.py
    cp ${../plugins/eden/p1-controls.ini} work/plugins/eden/p1-controls.ini
    cp ${contractSource} work/contracts/generated/korrid.ts
    mkdir -p "$out"
    cp ${buildFlags} "$out/build-flags.json"
    # The innermost Qt frontend is the real ELF, not either Nix wrapper.
    readelf -h ${upstream}/bin/..eden-wrapped-wrapped > "$out/elf-header.txt"
    nm -C ${upstream}/bin/..eden-wrapped-wrapped > symbols.txt
    ${pkgs.lib.optionalString pkgs.stdenv.hostPlatform.isAarch64 ''
      grep -F 'Core::ArmNce::RunThread' symbols.txt > "$out/nce-symbols.txt"
      grep -F 'Core::NCE::Patcher::PatchText' symbols.txt >> "$out/nce-symbols.txt"
    ''}
    cp ${upstream.src}/src/common/settings.cpp "$out/settings.cpp"
    cp ${upstream.src}/CMakeLists.txt "$out/CMakeLists.txt"
    # Native indices use Eden's own stable sort, not the Vulkan loader order.
    # Pin the entire ordering implementation file; any upstream edit needs review.
    printf '%s  %s\n' \
      '72a3a41ba23e0be7a9c98ca447f6022238029368cdba881c32e5291180a74ad6' \
      '${upstream.src}/src/video_core/vulkan_common/vulkan_wrapper.cpp' \
      > "$out/vulkan-device-order-source.sha256"
    sha256sum --check "$out/vulkan-device-order-source.sha256"
    # The native P1 record and GUID/port rules must be reviewed on SDL-driver changes.
    printf '%s  %s\n' \
      '0cfbdde1b2c816b4857c0af651a4f69ae27116930420fc23895c1c7922792601' \
      '${upstream.src}/src/input_common/drivers/sdl_driver.cpp' \
      > "$out/p1-sdl-source.sha256"
    sha256sum --check "$out/p1-sdl-source.sha256"
    cd work
    tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext \
      --moduleResolution Bundler plugins/eden/plugin.ts
    bun plugins/eden/plugin.test.ts
    python3 plugins/eden/vulkan_device_test.py ${pkgs.crudini}/bin/crudini
    python3 plugins/eden/p1_controls_test.py ${pkgs.crudini}/bin/crudini
    ruff check plugins/eden/vulkan_device.py plugins/eden/vulkan_device_test.py plugins/eden/p1_controls.py plugins/eden/p1_controls_test.py
    ruff format --check plugins/eden/vulkan_device.py plugins/eden/vulkan_device_test.py plugins/eden/p1_controls.py plugins/eden/p1_controls_test.py
    mypy --strict plugins/eden/vulkan_device.py plugins/eden/vulkan_device_test.py plugins/eden/p1_controls.py plugins/eden/p1_controls_test.py
    shellcheck ${edenPackage}/bin/eden
    ${pkgs.xvfb-run}/bin/xvfb-run -a python3 ${../plugins/eden/runtime-check.py} \
      ${edenPackage} ${edenPackage.upstream} "$out"
  ''

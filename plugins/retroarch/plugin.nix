# `base` is the frontend build a core may choose: nixpkgs' RetroArch by
# default, or a pinned fork or overrideAttrs derivation named by a catalogue
# entry. It selects the build, never whether Korri's protections apply — the
# read-only and non-interactive netplay patches run against whatever is
# chosen, and the settings evidence is derived from that exact binary.
{
  pkgs,
  base ? pkgs.retroarch-bare,
}:
let
  retroarchReadOnlyPatch = ./patches/retroarch-udev-read-only.patch;
  retroarchUdevReadOnlyCheck =
    pkgs.buildPackages.callPackage ./patches/retroarch-udev-read-only-check.nix
      {
        retroarchSource = base.src;
        readOnlyPatch = retroarchReadOnlyPatch;
      };
  retroarch = base.overrideAttrs (old: {
    patches = (old.patches or [ ]) ++ [
      retroarchReadOnlyPatch
      ./patches/retroarch-netplay-config-password.patch
      ./patches/retroarch-netplay-host-in-place.patch
    ];
    # Keep the actual packaged emulator behind the compiled source regression.
    postPatch = (old.postPatch or "") + ''
      test -e ${retroarchUdevReadOnlyCheck}
    '';
  });
  retroarchSettings = import ./settings-check.nix {
    inherit pkgs;
    program = retroarch;
  };
  retroarchInputplumberAutoconfig = pkgs.callPackage ./retroarch-inputplumber-autoconfig.nix { };
in
{
  packages = {
    inherit retroarch;
    autoconfig = retroarchInputplumberAutoconfig;
    retroarch-settings = retroarchSettings;
  };
  files = {
    retroarch = "${retroarch}/bin/retroarch";
    retroarch-settings = "${retroarchSettings}/settings.json";
    autoconfig = "${retroarchInputplumberAutoconfig}/share/libretro/autoconfig";
  };
}

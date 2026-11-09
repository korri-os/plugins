# FHS environment for the Solarus Android build. AGP downloads Google's
# prebuilt NDK and CMake, which expect a generic Linux loader and libraries.
let
  pkgs = import /nix/store/398fqjqkp383m7pyla9nxpi1is5vzywh-source {
    config = { allowUnfree = true; android_sdk.accept_license = true; };
  };
  android = pkgs.androidenv.composeAndroidPackages {
    includeEmulator = false;
    includeSystemImages = false;
    includeSources = false;
    includeNDK = false;
    platformVersions = [ ];
    buildToolsVersions = [ ];
  };
in (pkgs.buildFHSEnv {
  name = "solarus-android-fhs";
  targetPkgs = p: with p; [
    android.androidsdk jdk25 git curl unzip zip gnumake ninja python3 file which
    zlib ncurses5 stdenv.cc.cc.lib libxml2 openssl glibc
  ];
  profile = ''
    export JAVA_HOME=${pkgs.jdk25}
    export SOLA_NIX_SDK=${android.androidsdk}/libexec/android-sdk
  '';
  runScript = "bash";
})

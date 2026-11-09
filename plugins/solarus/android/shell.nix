# Solarus Android spike toolchain on aka. solarus-android pins compileSdk 37,
# build-tools 37.0.0, NDK 30.0.16248370, CMake 4.1.2 and Java 25. The pinned
# nixpkgs lacks that NDK, so AGP installs the exact SDK parts into a writable
# SDK root ($W/sdk) with nixpkgs' cmdline-tools and accepted licenses.
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
in pkgs.mkShell {
  packages = with pkgs; [ android.androidsdk jdk25 git curl unzip zip gnumake ninja python3 file which ];
  JAVA_HOME = "${pkgs.jdk25}";
  SOLA_NIX_SDK = "${android.androidsdk}/libexec/android-sdk";
}

# ZQuest Classic Android spike toolchain on aka. Versions follow the
# android-port.patch build files: NDK 27.3.13750724, CMake 3.30.5,
# compileSdk 35, AGP 8.7.3 (needs Gradle 8.x).
let
  pkgs = import /nix/store/398fqjqkp383m7pyla9nxpi1is5vzywh-source {
    config = { allowUnfree = true; android_sdk.accept_license = true; };
  };
  android = pkgs.androidenv.composeAndroidPackages {
    buildToolsVersions = [ "35.0.0" "34.0.0" ];
    platformVersions = [ "35" ];
    includeEmulator = false;
    includeSystemImages = false;
    includeSources = false;
    includeNDK = true;
    ndkVersions = [ "27.3.13750724" ];
    cmakeVersions = [ "3.30.5" ];
  };
in pkgs.mkShell {
  packages = with pkgs; [ android.androidsdk jdk17 gradle_8 git curl unzip zip gnumake ninja python3 patch file binutils which flex bison pkg-config ];
  JAVA_HOME = "${pkgs.jdk17}";
  ZQ_NIX_SDK = "${android.androidsdk}/libexec/android-sdk";
}

#!/usr/bin/env nix-shell
#!nix-shell /var/lib/zquest-android-build/shell.nix -i bash
# Builds the ZQuest Classic Android spike APK on aka. Never run on a target device.
set -euo pipefail
W=/var/lib/zquest-android-build
BASE=3e5476411344a770489cb5aa44eb80de2eac164d
PATCH_SHA=4c2bc8b69ed32e287af3475b43a7ba4475c13a0ffca0e675201497e01486e7fc

cd "$W"
echo "$PATCH_SHA  android-port.patch" | sha256sum -c -

if [[ ! -d src/.git ]]; then
  git clone https://github.com/ZQuestClassic/ZQuestClassic.git src
fi
cd src
if [[ ! -f .android-patched ]]; then
  git fetch origin "$BASE"
  git checkout --detach "$BASE"
  git apply "$W/android-port.patch"
  touch .android-patched
fi
test "$(git rev-parse HEAD)" = "$BASE"
# Korri fixes on top of the port: immersive mode, physical controllers mapped to
# the default keyboard scheme, overlay hidden while a controller is connected,
# resources installed before any quest starts, appCategory=game.
if [[ ! -f .korri-patched ]]; then
  git apply "$W/korri-fixes.patch"
  touch .korri-patched
fi

# Writable SDK root that links Nix's read-only parts, so AGP finds exact versions.
export ANDROID_HOME="$W/sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
mkdir -p "$ANDROID_HOME"/{ndk,licenses,cmake,platforms}
for p in build-tools cmdline-tools platform-tools tools; do ln -sfn "$ZQ_NIX_SDK/$p" "$ANDROID_HOME/$p"; done
for p in "$ZQ_NIX_SDK"/platforms/*; do ln -sfn "$p" "$ANDROID_HOME/platforms/$(basename "$p")"; done
for p in "$ZQ_NIX_SDK"/licenses/*; do cp -f "$p" "$ANDROID_HOME/licenses/$(basename "$p")"; done
ln -sfn "$ZQ_NIX_SDK/ndk-bundle" "$ANDROID_HOME/ndk/27.3.13750724"
ln -sfn "$ZQ_NIX_SDK/cmake/3.30.5" "$ANDROID_HOME/cmake/3.30.5"
export ANDROID_NDK_HOME="$ANDROID_HOME/ndk/27.3.13750724"
export PATH="$ANDROID_HOME/cmake/3.30.5/bin:$PATH"
export GRADLE_OPTS="-Dorg.gradle.daemon=false -Dorg.gradle.project.android.aapt2FromMavenOverride=$ZQ_NIX_SDK/build-tools/35.0.0/aapt2"

cat "$ANDROID_NDK_HOME/source.properties"
cmake --version | head -1
gradle --version | grep -E "^Gradle"

# services.gradle.org downloads 504 (GitHub release redirect). Use the mirrored
# Gradle 8.12 zip, checked against Gradle's published SHA-256.
echo "7a00d51fb93147819aab76024feece20b6b84e420694101f276be952e08bef03  $W/gradle-8.12-bin.zip" | sha256sum -c -
# Seed the wrapper cache: the directory name is base36(md5(distributionUrl)).
D="${GRADLE_USER_HOME:-$HOME/.gradle}/wrapper/dists/gradle-8.12-bin/cetblhg4pflnnks72fxwobvgv"
mkdir -p "$D"
[[ -f "$D/gradle-8.12-bin.zip" ]] || cp "$W/gradle-8.12-bin.zip" "$D/"

bash android/build.sh

APK=android/app/build/outputs/apk/debug/app-debug.apk
sha256sum "$APK"
stat -c '%n %s bytes' "$APK"

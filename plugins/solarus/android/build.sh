#!/usr/bin/env bash
# Run inside the FHS env: $(nix-build fhs.nix)/bin/solarus-android-fhs build.sh
# Builds the official Solarus Android app on aka. Never run on a target device.
set -euo pipefail
W=/var/lib/solarus-android-build
REV="${SOLA_REV:?set SOLA_REV to the solarus-android commit}"

cd "$W"
if [[ ! -d src/.git ]]; then
  git clone https://gitlab.com/solarus-games/solarus-android.git src
fi
cd src
git fetch origin "$REV"
git checkout --detach "$REV"
git submodule update --init --recursive --depth 1
test "$(git rev-parse HEAD)" = "$REV"
git submodule status

# Korri fixes on top of upstream (none yet when the file is empty).
if [[ -s "$W/korri-fixes.patch" && ! -f .korri-patched ]]; then
  git apply "$W/korri-fixes.patch"
  touch .korri-patched
fi

export ANDROID_HOME="$W/sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
mkdir -p "$ANDROID_HOME/licenses" "$ANDROID_HOME/cmdline-tools"
ln -sfn "$SOLA_NIX_SDK/cmdline-tools/"* "$ANDROID_HOME/cmdline-tools/latest" 2>/dev/null || true
[[ -e "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" ]] || ln -sfn "$(dirname "$(dirname "$(readlink -f "$(command -v sdkmanager)")")")" "$ANDROID_HOME/cmdline-tools/latest"
for p in "$SOLA_NIX_SDK"/licenses/*; do cp -f "$p" "$ANDROID_HOME/licenses/"; done
yes | "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$ANDROID_HOME" --licenses >/dev/null || true
echo "sdk.dir=$ANDROID_HOME" > local.properties

java -version 2>&1 | head -1
export GRADLE_OPTS="-Dorg.gradle.daemon=false -Dorg.gradle.welcome=never"
export MAKEFLAGS="-j$(nproc)"
./gradlew --no-daemon :cmake_build:assembleDebug :app:assembleDebug

ls -la app/build/outputs/apk/debug/
sha256sum app/build/outputs/apk/debug/*.apk

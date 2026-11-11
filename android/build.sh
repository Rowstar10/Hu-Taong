#!/usr/bin/env bash
# Builds Hu Taong's Android APK with python-for-android (the GitHub workflow runs this).
#
#   android/build.sh            a signed release APK if ANDROID_KEYSTORE_FILE and
#                               ANDROID_KEYSTORE_PASSWORD are set, otherwise a debug one
#
# Needs: python-for-android (pip install python-for-android cython), the Android SDK and NDK
# (ANDROID_SDK_ROOT, ANDROID_NDK_HOME), Java 17, and ffmpeg for the music (see stage.py).
# The APK lands in dist/, named Hu-Taong-<version>-android.apk.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
GAME="$(dirname "$HERE")"
WORK="${WORK:-$GAME/build/android}"
# The version is the newest one in the changelog ("## 1.5 — ..."), unless given
VERSION="${VERSION:-$(sed -n 's/^## \([0-9][0-9.]*\).*/\1/p' "$GAME/CHANGELOG.md" | head -1)}"
MAJOR="${VERSION%%.*}"; MINOR="${VERSION#*.}"; MINOR="${MINOR%%.*}"
# Each version is its own app, so several can be installed side by side (as on a PC)
PACKAGE="com.rowstar10.hutaong.v${VERSION//./_}"
ARCHS="${ARCHS:-arm64-v8a x86_64}"

echo "Hu Taong $VERSION for Android ($PACKAGE, $ARCHS)"
python3 "$HERE/stage.py" "$WORK/app"

args=(apk
  --private "$WORK/app"
  --dist_name "hutaong-${VERSION//./_}"
  --package "$PACKAGE"
  --name "Hu Taong $VERSION"
  --version "$VERSION"
  --numeric-version "$((MAJOR * 100 + MINOR))"
  --bootstrap sdl2
  --requirements python3,pygame,pyjnius
  --local-recipes "$HERE/recipes"
  --orientation landscape
  --icon "$WORK/icon.png"
  --presplash "$WORK/presplash.jpg"
  --presplash-color "#1a0b0b"
  --wakelock
  --permission INTERNET
  --permission ACCESS_NETWORK_STATE
  --permission ACCESS_WIFI_STATE
  --permission CHANGE_WIFI_MULTICAST_STATE
  --permission VIBRATE
  --android-api "${ANDROID_API:-35}"
  --ndk-api 24
  --sdk-dir "${ANDROID_SDK_ROOT:?set ANDROID_SDK_ROOT}"
  --ndk-dir "${ANDROID_NDK_HOME:?set ANDROID_NDK_HOME}"
  --storage-dir "${P4A_STORAGE:-$WORK/p4a}"
  --ignore-setup-py
  --copy-libs
)
for arch in $ARCHS; do args+=(--arch "$arch"); done

mkdir -p "$GAME/dist"
cd "$WORK"
rm -f ./*.apk
if [[ -n "${ANDROID_KEYSTORE_FILE:-}" && -n "${ANDROID_KEYSTORE_PASSWORD:-}" ]]; then
  # (the password goes through the environment, so it never shows in a command line)
  export P4A_RELEASE_KEYSTORE="$ANDROID_KEYSTORE_FILE"
  export P4A_RELEASE_KEYSTORE_PASSWD="$ANDROID_KEYSTORE_PASSWORD"
  export P4A_RELEASE_KEYALIAS="${ANDROID_KEY_ALIAS:-toki}"
  export P4A_RELEASE_KEYALIAS_PASSWD="$ANDROID_KEYSTORE_PASSWORD"
  p4a "${args[@]}" --release --sign
  signed="release"
else
  p4a "${args[@]}"
  signed="debug"
fi
apk="$(ls -t ./*.apk | head -1)"
cp "$apk" "$GAME/dist/Hu-Taong-$VERSION-android.apk"
echo "Built dist/Hu-Taong-$VERSION-android.apk ($signed)"

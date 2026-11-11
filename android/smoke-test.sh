#!/usr/bin/env bash
# Plays the APK on a running emulator or phone (adb): starts it, reaches the main menu, starts a
# match against the AI, steers with a finger, pauses with Back, and checks Python never failed.
# Screenshots and the log go to the folder given (default: build/android-test).
#
#   android/smoke-test.sh dist/Hu-Taong-1.5-android.apk [out folder]
set -euo pipefail

APK="$1"
OUT="${2:-build/android-test}"
mkdir -p "$OUT"
VERSION="$(basename "$APK" | sed -n 's/^Hu-Taong-\([0-9.]*\)-android\.apk$/\1/p')"
PACKAGE="com.rowstar10.hutaong.v${VERSION//./_}"

shot() { adb exec-out screencap -p > "$OUT/$1.png"; echo "screenshot: $1"; }
log() { adb logcat -d -s python:I > "$OUT/python.log" || true; }
fail() { log; echo "FAILED: $*"; tail -60 "$OUT/python.log"; exit 1; }

# Where a point of the game's own 1920 x 1080 is on this screen (the game fits it, centred)
read -r W H < <(adb shell wm size | sed -n 's/.*: \([0-9]*\)x\([0-9]*\).*/\1 \2/p' | tail -1)
if (( W < H )); then t=$W; W=$H; H=$t; fi                         # the game is landscape
at() { python3 -c "s=min($W/1920,$H/1080); print(round(($W-1920*s)/2+$1*s), round(($H-1080*s)/2+$2*s))"; }
tap() { read -r x y < <(at "$1" "$2"); adb shell input tap "$x" "$y"; sleep "${3:-2}"; }
swipe() { read -r x1 y1 < <(at "$1" "$2"); read -r x2 y2 < <(at "$3" "$4"); adb shell input swipe "$x1" "$y1" "$x2" "$y2" "$5"; }
waitfor() {   # waitfor <pattern> <seconds>
  for _ in $(seq "$2"); do
    if adb logcat -d -s python:I | grep -q "$1"; then return 0; fi
    sleep 1
  done
  return 1
}

echo "Installing $APK ($PACKAGE) on a ${W}x${H} screen"
adb install -r -g "$APK"
# Android explains full-screen mode the first time an app uses it; a player taps it away
adb shell settings put secure immersive_mode_confirmations confirmed || true
adb logcat -c
adb shell am start -n "$PACKAGE/org.kivy.android.PythonActivity"

# The first launch unpacks the game, then it loads its sprites
waitfor "\[Hu Taong\] .* FPS on main_menu" 300 || fail "the main menu never came up"
sleep 3
shot 1-main-menu

tap 146 652 3                                # Play
adb logcat -d -s python:I | grep -q "Traceback" && fail "Python failed in the menus"
shot 2-match-setup
tap 314 411 1                                # against the AI
tap 959 692 6                                # Start
shot 3-match
swipe 1500 700 1500 300 400                  # slide a finger up: the paddle follows
sleep 1
shot 4-steered
swipe 1500 300 1500 800 400
sleep 4
adb shell input keyevent 4                   # Back: pause
sleep 2
shot 5-paused
waitfor "FPS on pause" 12 || fail "Back didn't pause the match"

adb shell input keyevent 3                   # Home, then back again: the game carries on
sleep 3
adb shell am start -n "$PACKAGE/org.kivy.android.PythonActivity"
sleep 6
shot 6-resumed

log
if grep -q "Traceback" "$OUT/python.log"; then fail "Python failed: see python.log"; fi
pid="$(adb shell pidof "$PACKAGE" || true)"
[[ -n "$pid" ]] || fail "the game is no longer running"
echo "Frame rates seen:"
grep -o "\[Hu Taong\] [0-9]* FPS on [a-z_]*" "$OUT/python.log" | tail -12
echo "Smoke test passed"

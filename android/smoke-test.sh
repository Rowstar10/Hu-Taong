#!/usr/bin/env bash
# Plays the APK on a running emulator or phone (adb): starts it, reaches the main menu, starts a
# match against the AI, steers with a finger, pauses with Back, leaves and comes back, and checks
# Python never failed. Screenshots and the log go to the folder given (default: build/android-test).
#
# Where to tap comes from the game itself (android/ui_positions.py, run on the same version), so
# moving a button doesn't break the test. Each step checks the screen it should lead to (the game
# logs which screen is up every 5 s), and tries again if Android's own dialogs got in the way.
#
#   android/smoke-test.sh dist/Hu-Taong-1.7-android.apk build/positions.json [out folder]
set -euo pipefail

APK="$1"
POSITIONS="$2"
OUT="${3:-build/android-test}"
mkdir -p "$OUT"
VERSION="$(basename "$APK" | sed -n 's/^Hu-Taong-\([0-9.]*\)-android\.apk$/\1/p')"
PACKAGE="com.rowstar10.hutaong.v${VERSION//./_}"

shot() { adb exec-out screencap -p > "$OUT/$1.png"; echo "screenshot: $1"; }
log() { adb logcat -d -s python:I > "$OUT/python.log" || true; }
fail() { log; shot failed || true; echo "FAILED: $*"; tail -60 "$OUT/python.log"; exit 1; }

# Where a point of the game's own 1920 x 1080 is on this screen (the game fits it, centred)
read -r W H < <(adb shell wm size | sed -n 's/.*: \([0-9]*\)x\([0-9]*\).*/\1 \2/p' | tail -1)
if (( W < H )); then t=$W; W=$H; H=$t; fi                         # the game is landscape
at() { python3 -c "s=min($W/1920,$H/1080); print(round(($W-1920*s)/2+$1*s), round(($H-1080*s)/2+$2*s))"; }
control() { python3 -c "import json,sys; x,y=json.load(open(sys.argv[1]))[sys.argv[2]]; print(x, y)" "$POSITIONS" "$1"; }
swipe() { read -r x1 y1 < <(at "$1" "$2"); read -r x2 y2 < <(at "$3" "$4"); adb shell input swipe "$x1" "$y1" "$x2" "$y2" "$5"; }

# Android's own dialogs (on a slow emulator, "Pixel Launcher isn't responding") would catch the taps
calm() { adb shell am broadcast -a android.intent.action.CLOSE_SYSTEM_DIALOGS > /dev/null 2>&1 || true; }
# The screen the game last said it was on
on() { adb logcat -d -s python:I | grep -o "FPS on [a-z_]*" | tail -1 | grep -qx "FPS on $1"; }
waitfor() {   # waitfor <pattern> <seconds>: until the game's log says it
  for _ in $(seq "$2"); do
    if adb logcat -d -s python:I | grep -q "$1"; then return 0; fi
    sleep 1
  done
  return 1
}
tap() {       # tap <control>: no screen change to wait for
  calm
  read -r x y < <(at $(control "$1"))
  adb shell input tap "$x" "$y"
  sleep 1
}
go() {        # go <screen> <command...>: do it until the game is on that screen (3 tries)
  local screen="$1"; shift
  for try in 1 2 3; do
    calm
    "$@"
    for _ in $(seq 16); do sleep 1; on "$screen" && return 0; done
    echo "(not on $screen yet, try $try)"
  done
  return 1
}
press_control() { read -r x y < <(at $(control "$1")); adb shell input tap "$x" "$y"; }

echo "Installing $APK ($PACKAGE) on a ${W}x${H} screen"
adb install -r -g "$APK"
# Android explains full-screen mode the first time an app uses it; a player taps it away. And an
# emulator's "isn't responding" dialogs (for its own apps, not the game's) are kept out of the way.
adb shell settings put secure immersive_mode_confirmations confirmed || true
adb shell settings put global hide_error_dialogs 1 || true
adb logcat -c
calm
adb shell am start -n "$PACKAGE/org.kivy.android.PythonActivity"

# The first launch unpacks the game, then it loads its sprites
waitfor "\[Hu Taong\] .* FPS on main_menu" 300 || fail "the main menu never came up"
sleep 3
shot 1-main-menu

go match_setup press_control play || fail "Play didn't open Match Setup"
adb logcat -d -s python:I | grep -q "Traceback" && fail "Python failed in the menus"
shot 2-match-setup
tap against_ai
go game press_control start || fail "Start didn't start a match"
sleep 3
shot 3-match
swipe 1500 700 1500 300 400                  # slide a finger up: the paddle follows
sleep 1
shot 4-steered
swipe 1500 300 1500 800 400
sleep 3
go pause adb shell input keyevent 4 || fail "Back didn't pause the match"
shot 5-paused

adb shell input keyevent 3                   # Home, then back again: the game carries on
sleep 3
calm
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

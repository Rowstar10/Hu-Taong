# Hu Taong 1.6

Pong, the Wangsheng Funeral Parlor way. Version 1.6, 12 November 2026.

Power-up fixes and changes, from a review of every power-up, then a round of changes from playtesting it.

## Play it

The easiest way is **Toki Hub**, which installs any version with everything it needs.

From the source, with Python 3.12 and pygame 2.6.1:

```
pip install pygame==2.6.1
python main.py
```

## Build the .exe

```
pip install pyinstaller
pyinstaller main.spec
```

The .exe appears in `dist`.

## Android

Hu Taong also plays on Android phones and tablets, with touch controls: Toki Hub for Android
installs it, or get the APK from a `v1.5-android` style release. It plays online with the PC
version of the same number. The phone version is 1.5 for now: 1.6 has no APK yet, so a phone
can't play a PC on 1.6 online.

The APK is built by GitHub (`.github/workflows/android.yml`), with `android/build.sh`
(python-for-android). The phone's controls live in `core/touch.py`.

## Tests

```
pip install pygame==2.6.1
python -m unittest discover -s tests -t .
```

They run the game with no window or sound, and never touch your own saves.

## More

[CHANGELOG.md](CHANGELOG.md) · [CREDITS.md](CREDITS.md) · [ONLINE.md](ONLINE.md) · [SERVER.md](SERVER.md)

Every version: [Hu-Taong tags](https://github.com/Rowstar10/Hu-Taong/tags)

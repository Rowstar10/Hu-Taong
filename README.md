# Hu Taong 1.9

Pong, the Wangsheng Funeral Parlor way. Version 1.9, 21 November 2026.

Controllers and mouse steering, quick emotes online, Practice Mode against the AI or a wall, Goals on or off, achievements and talisman stats, new sounds, a Modes page beside the Talismans, and Match Setup and the settings pages laid out afresh.

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
installs it, or get the APK from the version's release (`Hu-Taong-1.9-android.apk` on `v1.9`). It
plays online with the PC version of the same number.

GitHub builds the APK (`.github/workflows/android.yml`, with `android/build.sh` and
python-for-android), plays it on an emulated phone, and publishes it on the release of every
version tag: pushing `v1.9` is all a new version needs. A version tagged before that can be
published by running the Android workflow by hand with its tag. The phone's controls live in
`core/touch.py`.

## Tests

```
pip install pygame==2.6.1
python -m unittest discover -s tests -t .
```

They run the game with no window or sound, and never touch your own saves.

## More

[CHANGELOG.md](CHANGELOG.md) · [CREDITS.md](CREDITS.md) · [ONLINE.md](ONLINE.md) · [SERVER.md](SERVER.md)

Every version: [Hu-Taong tags](https://github.com/Rowstar10/Hu-Taong/tags)

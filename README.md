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

## Releasing a version

Your friends get Hu Taong through Toki Hub, from the public
[Hu-Taong-Releases](https://github.com/Rowstar10/Hu-Taong-Releases/releases) repo: each version is a
release there with `Hu-Taong-<version>-windows.zip` (and the Android APK). To publish one, from this
folder on your Windows PC:

```
py release.py 1.10
```

It builds the version's tag (`v1.10`; it offers to tag your latest commit if there's none yet) into
a Windows folder build, zips it, has GitHub build and test the Android APK, and publishes both, with
the version's CHANGELOG.md section as the notes. `py release.py 1.10 --no-publish` only builds the zip
(in `dist`), to try it first: unzip it and run `Hu Taong.exe`.

Once, beforehand: install the GitHub CLI (https://cli.github.com) and run `gh auth login`. It publishes
as you, so no token is stored anywhere. The script sets up its own Python 3.12 build tools
(`.release-venv`, with `release/requirements.txt`). The build recipe is `release/hu_taong.spec`; the
**Windows build** workflow builds any commit on GitHub and tries the result (`release/try-build.ps1`).

## Android

Hu Taong also plays on Android phones and tablets, with touch controls: Toki Hub for Android
installs it, or get the APK from the version's release (`Hu-Taong-1.9-android.apk`). It plays online
with the PC version of the same number.

GitHub builds the APK (`.github/workflows/android.yml`, with `android/build.sh` and
python-for-android) and plays it on an emulated phone; release.py runs that workflow and publishes
the APK. It runs only when started, to save Actions minutes. The phone's controls live in
`core/touch.py`.

## Tests

```
pip install pygame==2.6.1
python -m unittest discover -s tests -t .
```

They run the game with no window or sound, and never touch your own saves.

## More

[CHANGELOG.md](CHANGELOG.md) · [CREDITS.md](CREDITS.md) · [ONLINE.md](ONLINE.md) · [SERVER.md](SERVER.md)

Every version: [Hu-Taong-Releases](https://github.com/Rowstar10/Hu-Taong-Releases/releases)

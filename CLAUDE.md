# Hu Taong

- This repo is private. Friends get builds from the public repo Rowstar10/Hu-Taong-Releases.
- Release with `py release.py <version>`: it builds the Windows folder build (release/hu_taong.spec),
  zips it as Hu-Taong-<version>-windows.zip, builds the Android APK (1.5 on) with android.yml, and
  publishes both with gh. Tags are v<version>. Each version needs a CHANGELOG.md section first.
  `--no-publish` builds without publishing.
- Never commit build output, zips or APKs (.release-work/, .release-venv/, dist/).
- Settings and saves go to %APPDATA%\HuTaong (`data_dir` in core/platform.py); never write into the
  game's own folder, because reinstalling replaces it.
- The Android signing key lives only in the repo's secrets. Never commit it.
- android.yml runs only when started by hand, to save Actions minutes.
- Tests: `python -m unittest discover -s tests -t .` (set SDL_VIDEODRIVER=dummy with no screen).

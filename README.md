# Hu Taong 1.0

Pong, the Wangsheng Funeral Parlor way. Version 1.0, 3 November 2026.

First release.

- Local two-player and vs AI (Baby, Easy, Normal, Hard, Insane), with adaptive AI
- Chaos mode, endless mode and win-by-two
- Background gallery, mood-based music, display/audio/gameplay settings and match stats

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

## More

[CHANGELOG.md](CHANGELOG.md) · [CREDITS.md](CREDITS.md)

Every version: [Hu-Taong tags](https://github.com/Rowstar10/Hu-Taong/tags)

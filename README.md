# Hu Taong 1.3

Pong, the Wangsheng Funeral Parlor way. Version 1.3, 10 November 2026.

Settings, assets, AI and power-up overhaul.

- Online play (see ONLINE.md), with an optional server of your own (SERVER.md)
- Replays, a jukebox and courts

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

[CHANGELOG.md](CHANGELOG.md) · [CREDITS.md](CREDITS.md) · [ONLINE.md](ONLINE.md) · [SERVER.md](SERVER.md)

Every version: [Hu-Taong tags](https://github.com/Rowstar10/Hu-Taong/tags)

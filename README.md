# Hu Taong 1.4

Pong, the Wangsheng Funeral Parlor way. Version 1.4, 10 November 2026.

Fixes for hits off a paddle's ends, and for a friend leaving an online match.

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

## Tests

```
pip install pygame==2.6.1
python -m unittest discover -s tests -t .
```

They run the game with no window or sound, and never touch your own saves.

## More

[CHANGELOG.md](CHANGELOG.md) · [CREDITS.md](CREDITS.md) · [ONLINE.md](ONLINE.md) · [SERVER.md](SERVER.md)

Every version: [Hu-Taong tags](https://github.com/Rowstar10/Hu-Taong/tags)

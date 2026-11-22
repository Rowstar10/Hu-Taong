# -*- mode: python ; coding: utf-8 -*-
# PyInstaller recipe for Hu Taong's Windows build: a folder ("Hu Taong", with Hu Taong.exe and
# _internal) rather than one big exe, so it starts quickly. release/build.py runs it, on any
# version's source, with these set:
#   HUTAONG_SOURCE  that version's files (a clean copy of a commit)
#   HUTAONG_ENTRY   its main script (main.py from 0.3 on)
#   HUTAONG_TK      "1" for the Tkinter versions (0.1 to 0.4), which need Tcl/Tk
import os
from pathlib import Path

SOURCE = Path(os.environ["HUTAONG_SOURCE"]).resolve()
ENTRY = os.environ.get("HUTAONG_ENTRY", "main.py")
TKINTER = os.environ.get("HUTAONG_TK") == "1"
CONSOLE = os.environ.get("HUTAONG_CONSOLE") == "1"     # a build that shows its errors (for finding a fault)

# Everything in Resources (pictures, sounds, music, fonts) goes in, keeping its folders: the game
# finds them under sys._MEIPASS. Settings and saves aren't here: the game keeps them in
# %APPDATA%\HuTaong, so they survive reinstalls and never need the install folder to be writable.
datas = []
for path in sorted((SOURCE / "Resources").rglob("*")):
    if path.is_file():
        datas.append((str(path), str(path.parent.relative_to(SOURCE))))

# The game finds its screens at run time by scanning core.states, so PyInstaller has to be told
hiddenimports = []
states = SOURCE / "core" / "states"
if states.is_dir():
    hiddenimports = ["core.states." + ".".join(p.relative_to(states).with_suffix("").parts)
                     for p in sorted(states.rglob("*.py")) if p.stem != "__init__"]

a = Analysis(
    [str(SOURCE / ENTRY)],
    pathex=[str(SOURCE)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[] if TKINTER else ["tkinter", "_tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

icon = SOURCE / "Resources" / "Images" / "icon.ico"
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Hu Taong",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=CONSOLE,
    disable_windowed_traceback=False,
    icon=[str(icon)] if icon.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Hu Taong",
)

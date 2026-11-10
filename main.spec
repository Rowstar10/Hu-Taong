# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# The game finds its screens at run time by scanning core.states, so list them for PyInstaller
hiddenimports = collect_submodules('core.states')

# Files in Resources the game never loads: left out of the .exe (they stay in the project)
UNUSED = {
    "Images/craig-cyrax-hu-tao-22.jpg",
    "Images/Hu-Tao-Ghost-Landscape.jpg",
    "Images/tst,small,507x507-pad,600x600,f8f8f8.webp",
    "Images/icon.ico",                    # only for the .exe's own icon, below
    "Sounds/you_win2.wav",
    "Sounds/Music/you_win.wav",
}
ROOT = Path(SPECPATH)
datas = []
for path in sorted((ROOT / "Resources").rglob("*")):
    rel = path.relative_to(ROOT / "Resources").as_posix()
    if path.is_file() and rel not in UNUSED:
        datas.append((str(path), str(path.parent.relative_to(ROOT))))

# Parts of Python the game doesn't use.  The file dialogs and clipboard are Windows' own (through
# ctypes), so Tcl/Tk isn't needed; nothing connects securely, so neither is OpenSSL.
EXCLUDES = ["tkinter", "_tkinter", "ssl", "_ssl", "_hashlib", "lzma", "_lzma", "bz2", "_bz2",
            "unittest", "pydoc", "doctest", "pdb", "xmlrpc", "sqlite3", "_sqlite3",
            "multiprocessing", "_multiprocessing", "asyncio", "_asyncio", "_overlapped", "_wmi"]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=2,                           # no docstrings or asserts: a little smaller and quicker
)

# pygame's libraries arrive twice (once in pygame\, once beside the .exe): keep the pygame\ ones,
# which are the ones pygame loads.  Drop the decoders for formats the game never uses (TIFF and
# WebP pictures, MOD and Opus music, MIDI).
pygame_libs = {Path(name).name.lower() for name, _, _ in a.binaries if name.lower().startswith("pygame\\")}
NEVER_USED = ("libtiff", "libwebp", "libmodplug", "libopus", "portmidi")
a.binaries = [b for b in a.binaries
              if not ("\\" not in b[0] and b[0].lower() in pygame_libs)
              and not Path(b[0]).name.lower().startswith(NEVER_USED)]
a.datas = [d for d in a.datas if not d[0].startswith(("_tcl_data", "_tk_data", "tcl8", "tk8"))]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ROOT / 'Resources' / 'Images' / 'icon.ico')],
)

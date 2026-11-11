"""Choosing a file to save to or open (for the stats), and the clipboard (for online codes).

Both use Windows itself, through ctypes: the same Save and Open dialogs every Windows program
has, and the system clipboard.  Nothing extra has to be bundled with the game for them.  If a
dialog can't be shown, files go to a Hu Taong folder in Documents instead.  On a phone, Android's
own file picker and clipboard do it (core/android.py).
"""
import os, sys
from pathlib import Path

from core.platform import ANDROID


def documents_folder():
    if ANDROID:
        from core.platform import data_dir
        return data_dir() / "Exports"          # (only if Android's picker couldn't open)
    home = Path.home()
    for name in ("Documents", "My Documents"):
        if (home / name).is_dir():
            return home / name / "Hu Taong"
    return home / "Hu Taong"


def _window():
    """The game window's handle, so a dialog sits over it."""
    try:
        import pygame
        return pygame.display.get_wm_info().get("window") or None
    except Exception:
        return None


def ask(save, title, default_name, kinds):
    """Show a Save or Open dialog; returns a path, None if it was cancelled, or False if no
    dialog could be shown.  `kinds` is [(label, "*.ext"), ...]."""
    if ANDROID:
        from core import android
        return android.ask(save, title, default_name, kinds)
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class OPENFILENAMEW(ctypes.Structure):
            _fields_ = [("lStructSize", wintypes.DWORD), ("hwndOwner", wintypes.HWND),
                        ("hInstance", wintypes.HINSTANCE), ("lpstrFilter", wintypes.LPCWSTR),
                        ("lpstrCustomFilter", wintypes.LPWSTR), ("nMaxCustFilter", wintypes.DWORD),
                        ("nFilterIndex", wintypes.DWORD), ("lpstrFile", wintypes.LPWSTR),
                        ("nMaxFile", wintypes.DWORD), ("lpstrFileTitle", wintypes.LPWSTR),
                        ("nMaxFileTitle", wintypes.DWORD), ("lpstrInitialDir", wintypes.LPCWSTR),
                        ("lpstrTitle", wintypes.LPCWSTR), ("Flags", wintypes.DWORD),
                        ("nFileOffset", wintypes.WORD), ("nFileExtension", wintypes.WORD),
                        ("lpstrDefExt", wintypes.LPCWSTR), ("lCustData", wintypes.LPARAM),
                        ("lpfnHook", ctypes.c_void_p), ("lpTemplateName", wintypes.LPCWSTR),
                        ("pvReserved", ctypes.c_void_p), ("dwReserved", wintypes.DWORD),
                        ("FlagsEx", wintypes.DWORD)]

        folder = documents_folder()
        folder.mkdir(parents = True, exist_ok = True)
        name = ctypes.create_unicode_buffer(default_name if save else "", 1024)
        filters = ctypes.create_unicode_buffer(
            "".join(f"{label} ({pattern})\0{pattern}\0" for label, pattern in kinds + [("All files", "*.*")]) + "\0")
        ofn = OPENFILENAMEW()
        ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
        ofn.hwndOwner = _window()
        ofn.lpstrFilter = ctypes.cast(filters, wintypes.LPCWSTR)
        ofn.nFilterIndex = 1
        ofn.lpstrFile = ctypes.cast(name, wintypes.LPWSTR)
        ofn.nMaxFile = 1024
        ofn.lpstrInitialDir = str(folder)
        ofn.lpstrTitle = title
        ofn.lpstrDefExt = kinds[0][1].lstrip("*.") if kinds else None
        OVERWRITE_PROMPT, NO_CHANGE_DIR, PATH_MUST_EXIST, FILE_MUST_EXIST, EXPLORER = 0x2, 0x8, 0x800, 0x1000, 0x80000
        ofn.Flags = NO_CHANGE_DIR | PATH_MUST_EXIST | EXPLORER | (OVERWRITE_PROMPT if save else FILE_MUST_EXIST)
        dialogs = ctypes.windll.comdlg32
        ok = (dialogs.GetSaveFileNameW if save else dialogs.GetOpenFileNameW)(ctypes.byref(ofn))
        if ok:
            return Path(name.value)
        return None if dialogs.CommDlgExtendedError() == 0 else False
    except Exception:
        return False


def fallback_path(default_name):
    folder = documents_folder()
    folder.mkdir(parents = True, exist_ok = True)
    return folder / default_name


def newest(pattern):
    """The most recent file in the Documents folder matching `pattern`, for when no dialog can open."""
    folder = documents_folder()
    found = sorted(folder.glob(pattern), key = os.path.getmtime) if folder.is_dir() else []
    return found[-1] if found else None


# ---------------- The clipboard ----------------

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x2


def _clipboard():
    import ctypes
    from ctypes import wintypes
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    return ctypes, user32, kernel32


def copy_text(text):
    """Put `text` on the clipboard; True if it worked."""
    if ANDROID:
        from core import android
        return android.copy_text(text)
    if sys.platform != "win32":
        return False
    try:
        ctypes, user32, kernel32 = _clipboard()
        data = (text + "\0").encode("utf-16-le")
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        target = kernel32.GlobalLock(handle)
        ctypes.memmove(target, data, len(data))
        kernel32.GlobalUnlock(handle)
        if not user32.OpenClipboard(None):
            return False
        try:
            user32.EmptyClipboard()
            return bool(user32.SetClipboardData(CF_UNICODETEXT, handle))
        finally:
            user32.CloseClipboard()
    except Exception:
        return False


def paste_text():
    """The clipboard's text, or "" if there's none."""
    if ANDROID:
        from core import android
        return android.paste_text()
    if sys.platform != "win32":
        return ""
    try:
        ctypes, user32, kernel32 = _clipboard()
        if not user32.OpenClipboard(None):
            return ""
        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            pointer = kernel32.GlobalLock(handle)
            try:
                return ctypes.wstring_at(pointer) if pointer else ""
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()
    except Exception:
        return ""

"""Which machine the game runs on.

On a PC nothing here changes anything.  On an Android phone or tablet (the APK built by
android/build.sh), the game plays on a touch screen: see core/touch.py for the controls and
core/android.py for the phone's own services (vibration, the clipboard, the file picker).

HUTAONG_ANDROID=1 makes a PC behave as a phone, for the tests (tests/android_suite.py).
"""
import os, sys
from pathlib import Path

ANDROID = (hasattr(sys, "getandroidapilevel") or "ANDROID_ARGUMENT" in os.environ
           or os.environ.get("HUTAONG_ANDROID") == "1")


def data_dir():
    """Where the save, the stats and the replays live."""
    if ANDROID and os.environ.get("ANDROID_PRIVATE"):
        return Path(os.environ["ANDROID_PRIVATE"]) / "HuTaong"      # the app's own storage
    return Path(os.environ.get("APPDATA") or (Path.home() / ".local" / "share")) / "HuTaong"


def refresh_rate():
    """The main screen's refresh rate in Hz, as Windows reports it (a 59.94 Hz screen says 59).
    None when it can't be told: another system, or a driver that only says "the default"."""
    if sys.platform != "win32" or ANDROID:
        return None
    try:
        import ctypes
        user32, gdi32 = ctypes.WinDLL("user32"), ctypes.WinDLL("gdi32")
        user32.GetDC.restype = ctypes.c_void_p
        user32.GetDC.argtypes = [ctypes.c_void_p]
        user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        gdi32.GetDeviceCaps.argtypes = [ctypes.c_void_p, ctypes.c_int]
        screen = user32.GetDC(None)
        if not screen:
            return None
        try:
            hz = gdi32.GetDeviceCaps(screen, 116)       # VREFRESH
        finally:
            user32.ReleaseDC(None, screen)
    except Exception:
        return None
    return hz if hz > 1 else None                      # 0 or 1: "the hardware's default"


def prepare():
    """Ask SDL for phone behaviour, before pygame starts."""
    if not ANDROID:
        return
    hints = {
        "SDL_ANDROID_TRAP_BACK_BUTTON": "1",     # Back is Esc, rather than closing the game
        "SDL_TOUCH_MOUSE_EVENTS": "0",           # fingers are read as fingers (core/touch.py)
        "SDL_MOUSE_TOUCH_EVENTS": "0",
        "SDL_RENDER_SCALE_QUALITY": "1",         # smooth scaling to the screen, on the GPU
        "SDL_IOS_ORIENTATIONS": "LandscapeLeft LandscapeRight",     # (SDL's name for it on phones)
    }
    for name, value in hints.items():
        os.environ.setdefault(name, value)

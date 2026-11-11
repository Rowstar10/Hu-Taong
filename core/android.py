"""The phone's own services, reached through pyjnius: vibration, the clipboard, and Android's
file picker (for exporting and importing stats).

Every call fails quietly: on a PC, or a phone without the service, it just does nothing.
"""
import os, threading, time
from pathlib import PurePosixPath

_cache = {}


def _jni():
    """(autoclass, the game's Activity), or None where there is no Android."""
    if "jni" not in _cache:
        try:
            from jnius import autoclass
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            _cache["jni"] = (autoclass, activity)
        except Exception:
            _cache["jni"] = None
    return _cache["jni"]


# ---------------- Vibration ----------------

def _vibrator():
    if "vibrator" not in _cache:
        _cache["vibrator"] = None
        jni = _jni()
        if jni:
            try:
                autoclass, activity = jni
                Context = autoclass("android.content.Context")
                vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
                if vibrator is not None and vibrator.hasVibrator():
                    _cache["vibrator"] = (vibrator, autoclass("android.os.VibrationEffect"))
            except Exception:
                pass
    return _cache["vibrator"]


def vibrate(ms, strength = 128):
    """A short buzz: `ms` long, `strength` 1-255."""
    found = _vibrator()
    if not found:
        return False
    vibrator, effect = found
    try:
        vibrator.vibrate(effect.createOneShot(int(ms), max(1, min(255, int(strength)))))
        return True
    except Exception:
        return False


# ---------------- The clipboard (SDL's, which is Android's) ----------------

def copy_text(text):
    try:
        import pygame.scrap
        pygame.scrap.put_text(text)
        return True
    except Exception:
        return False


def paste_text():
    try:
        import pygame.scrap
        return pygame.scrap.get_text() or ""
    except Exception:
        return ""


# ---------------- The start-up picture ----------------

def hide_loading_screen():
    """Take down Android's start-up picture (once the game's own loading screen is up)."""
    jni = _jni()
    if jni:
        try:
            jni[1].removeLoadingScreen()          # (it hands itself to Android's UI thread)
        except Exception:
            pass


# ---------------- The file picker ----------------

REQUEST = 0x4854          # "HT": our activity results


def _result_listener(callback):
    """An ActivityResultListener for the game's Activity, calling `callback(request, result, data)`."""
    from jnius import PythonJavaClass, java_method

    class Listener(PythonJavaClass):
        __javainterfaces__ = ["org/kivy/android/PythonActivity$ActivityResultListener"]
        __javacontext__ = "app"

        @java_method("(IILandroid/content/Intent;)V")
        def onActivityResult(self, request, result, data):
            callback(request, result, data)

    return Listener()


class PickedFile:
    """A file chosen in Android's picker.  It has no path: it is read and written through
    Android, but it offers what the stats screen uses of a Path."""

    class _Parent:
        def mkdir(self, *args, **kwargs):
            pass

    def __init__(self, uri, resolver):
        self.uri, self.resolver = uri, resolver
        self.parent = self._Parent()
        self.name = self._display_name()

    def _display_name(self):
        try:
            cursor = self.resolver.query(self.uri, None, None, None, None)
            if cursor is not None:
                try:
                    if cursor.moveToFirst():
                        column = cursor.getColumnIndex("_display_name")
                        if column >= 0:
                            return cursor.getString(column)
                finally:
                    cursor.close()
        except Exception:
            pass
        last = str(self.uri.getLastPathSegment() or "file")
        return PurePosixPath(last.split(":")[-1]).name

    def _open(self, mode):
        descriptor = self.resolver.openFileDescriptor(self.uri, mode)
        if descriptor is None:
            raise OSError("Android couldn't open the file")
        return descriptor.detachFd()

    def write_text(self, text, encoding = "utf-8"):
        with os.fdopen(self._open("wt"), "w", encoding = encoding) as f:
            f.write(text)

    def read_text(self, encoding = "utf-8"):
        with os.fdopen(self._open("r"), "r", encoding = encoding) as f:
            return f.read()


def ask(save, title, default_name, kinds):
    """Android's own Save or Open picker, as files.ask: a PickedFile, None if it was
    cancelled, or False if no picker could be shown."""
    jni = _jni()
    if not jni:
        return False
    try:
        autoclass, activity = jni
        Intent = autoclass("android.content.Intent")
        intent = Intent(Intent.ACTION_CREATE_DOCUMENT if save else Intent.ACTION_OPEN_DOCUMENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        json_only = kinds and all(pattern.endswith(".json") for _, pattern in kinds)
        intent.setType("application/json" if json_only and save else "*/*")
        if save:
            intent.putExtra(Intent.EXTRA_TITLE, default_name)

        done, picked = threading.Event(), {}

        def on_result(request, result, data):
            if request != REQUEST:
                return
            picked["uri"] = data.getData() if result == -1 and data is not None else None
            done.set()

        listener = _result_listener(on_result)
        activity.registerActivityResultListener(listener)
        try:
            activity.startActivityForResult(intent, REQUEST)
            # The game waits behind the picker.  It mustn't pump SDL's events meanwhile: paused,
            # SDL would hold on to Python there, and the picker's answer could never come in.
            deadline = time.monotonic() + 900
            while not done.is_set() and time.monotonic() < deadline:
                done.wait(0.05)
        finally:
            activity.unregisterActivityResultListener(listener)
        uri = picked.get("uri")
        if uri is None:
            return None
        return PickedFile(uri, activity.getContentResolver())
    except Exception as e:
        print(f"[android] no file picker: {e}")
        return False

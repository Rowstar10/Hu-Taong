"""Runs the game with no window or sound, for the tests.  Saves go to a temporary folder, so the
tests never touch your own settings, stats or replays.

Run every test from the game's folder with:   python -m unittest discover -s tests -t .
"""
import os
import sys
import tempfile

GAME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["APPDATA"] = tempfile.mkdtemp(prefix = "hutaong-tests-")
os.chdir(GAME)
if GAME not in sys.path:
    sys.path.insert(0, GAME)

_app = None


def app():
    """The one App for the whole test run (pygame allows a single window)."""
    global _app
    if _app is None:
        from core.app import App
        _app = App()
    return _app


def settle(app):
    """Carry out the screen changes asked for so far, as one frame of the game would."""
    app.state_manager.process_changes()


JUKEBOX = {"music_mode", "music_seek", "music_pause", "cycle_music_left", "cycle_music_right", "cycle_music_value"}


def buttons(state, app):
    """Draw a menu screen once and answer the buttons on it (not counting the jukebox's controls)."""
    state.draw(app.virtual)
    return set(state.ui_hitboxes) - JUKEBOX

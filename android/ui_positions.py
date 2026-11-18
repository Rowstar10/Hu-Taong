"""Where the controls the emulator test taps are, in the game's own 1920 x 1080, worked out by
running this copy of the game as a phone would (headless).  So the test finds them by name, and
moving a button in a new version doesn't break it.

    python android/ui_positions.py <out.json>
"""
import json, os, sys

GAME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["HUTAONG_ANDROID"] = "1"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, GAME)
os.chdir(GAME)

from tests import harness                       # noqa: E402  (keeps the player's own saves out of it)

app = harness.app()


def controls(*screens):
    """The controls on a screen, opened from the main menu through `screens`."""
    app.state_manager.set_state("main_menu", mute = True)
    for name in screens:
        app.state_manager.push_state(name, mute = True)
    for _ in range(3):
        app.state_manager.process_changes()
        app.dt = 1 / 60
        app.loop()
    return app.state_manager.current().ui_hitboxes


menu, setup = controls(), controls("match_setup")
positions = {"play": menu["play"].center,
             "against_ai": setup["opponent_ai"].center,
             "start": setup["start_match"].center}
with open(sys.argv[1], "w") as f:
    json.dump(positions, f)
print("Controls:", positions)

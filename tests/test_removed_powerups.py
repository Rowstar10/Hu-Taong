"""Gravity and Frostbite removed, 1.6 (Rowan's playtest list, 2026-11-16).

Both are gone for good: from the talismans, the Power-Ups screen, the computer player, the HUD and
the art.  A save or a replay from before still loads: tests/data holds a save and a replay made by
the released 1.6, with Gravity, Frostbite, Spirit Fire and Wind Gust in them.
"""
import os
import shutil
import unittest

from tests import harness

app = harness.app()

from core import save_data                                      # noqa: E402
from game.powerups import BY_KEY, KINDS                         # noqa: E402
from game.replay import Clip, ReplayView                        # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
GONE = ("gravity", "frost")


class Gone(unittest.TestCase):
    def test_no_longer_a_talisman(self):
        for key in GONE:
            self.assertNotIn(key, BY_KEY)
        self.assertEqual(len(KINDS), 20)

    def test_no_switch_for_them(self):
        g = app.settings.gameplay
        for key in GONE:
            self.assertFalse(hasattr(g, "pu_" + key))
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("powerups", mute = True)
        harness.settle(app)
        screen = sm.current()
        screen.draw(app.virtual)
        shown = set(screen.ui_hitboxes)
        self.assertIn("toggle_pu_fire", shown)
        for key in GONE:
            self.assertNotIn("toggle_pu_" + key, shown)
        sm.set_state("main_menu", mute = True)
        harness.settle(app)


class OldSave(unittest.TestCase):
    def tearDown(self):
        app.settings.gameplay.reset_powerups()

    def test_a_save_from_before_loads(self):
        save_data.save_path().parent.mkdir(parents = True, exist_ok = True)
        shutil.copy(os.path.join(DATA, "save_1.6.json"), save_data.save_path())
        save_data.load(app)
        g = app.settings.gameplay
        self.assertFalse(g.pu_fire, "the other switches come through")
        self.assertTrue(g.pu_wind)
        save_data.save(app)                       # and saving again leaves the old ones behind
        self.assertNotIn("pu_frost", save_data.collect(app)["gameplay"])


class OldReplay(unittest.TestCase):
    def setUp(self):
        self.clip = Clip.load(os.path.join(DATA, "replay_1.6_gravity_frost.htreplay"))

    def tearDown(self):
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_it_loads_without_them(self):
        self.assertIsNotNone(self.clip)
        view = ReplayView(self.clip, app)
        shown = set()
        for i in range(len(self.clip.frames)):
            view.show(i)
            shown.update(k for fx in view.powerups.fx for k, _, _ in fx)
            shown.update(k for k, _ in view.powerups.court)
            shown.update(p["kind"] for p in view.powerups.pickups)
        self.assertIn("fire", shown, "power-ups still in the game still show")
        self.assertIn("wind", shown)
        self.assertFalse(shown & set(GONE), shown)

    def test_it_plays_on_the_replay_screen(self):
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("replay", clip = self.clip, mode = "viewer", mute = True)
        harness.settle(app)
        for _ in range(len(self.clip.frames) + 10):     # every frame drawn, its events played
            app.state_manager.process_changes()
            app.dt = 1 / 60
            app.loop()
        self.assertEqual(sm.current().NAME, "replay")


if __name__ == "__main__":
    unittest.main()

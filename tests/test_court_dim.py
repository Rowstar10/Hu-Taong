"""Court Dim as a slider, 1.6 (Rowan's playtest list, 2026-11-16).

Court Dim was four steps (Off, Light, Medium, Strong); now it's a slider like the Dim Overlay's.
It still darkens matches on top of the Dim Overlay, and a save from before keeps its darkness.
"""
import json
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from core import save_data                                      # noqa: E402

display = app.settings.display


class CourtDimSlider(unittest.TestCase):
    def setUp(self):
        display.reset()
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("display", mute = True)
        harness.settle(app)
        self.screen = sm.current()
        self.screen.draw(app.virtual)

    def tearDown(self):
        display.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_it_is_a_slider_now(self):
        self.assertIn("court_dim_slider", self.screen.ui_hitboxes)
        self.assertIn("dim_slider", self.screen.ui_hitboxes)
        self.assertNotIn("cycle_court_dim_left", self.screen.ui_hitboxes)

    def test_dragging_it_sets_the_level(self):
        grab = self.screen.ui_hitboxes["court_dim_slider"]
        x, y = grab.left + grab.w * 0.75, grab.centery
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = (x / app.sx, y / app.sy)))
        self.assertAlmostEqual(display.court_dim_level, 0.75, delta = 0.05)
        x = grab.left + grab.w * 0.2
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos = (x / app.sx, y / app.sy),
                                                    rel = (0, 0), buttons = (1, 0, 0)))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = (x / app.sx, y / app.sy)))
        self.assertAlmostEqual(display.court_dim_level, 0.2, delta = 0.05)

    def test_the_default_is_half(self):
        """(As dark as the old Medium, 39%, until Rowan's 1.9 list: 0% or 50%.)"""
        self.assertAlmostEqual(display.court_dim_level, 0.5)


class DarkensMatches(unittest.TestCase):
    def tearDown(self):
        display.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_on_top_of_the_dim_overlay_in_a_match_only(self):
        display.dim, display.court_dim_level = 0.2, 0.5
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        harness.settle(app)
        self.assertAlmostEqual(app.background_dim(), 0.2, places = 3, msg = "menus: the Dim Overlay alone")
        sm.push_state("game", mute = True)
        harness.settle(app)
        self.assertAlmostEqual(app.background_dim(), 1 - 0.8 * 0.5, places = 3)


class OldSaves(unittest.TestCase):
    def tearDown(self):
        display.reset()

    def load_display(self, saved):
        data = save_data.collect(app)
        data["display"] = saved
        save_data.save_path().parent.mkdir(parents = True, exist_ok = True)
        save_data.save_path().write_text(json.dumps(data))
        display.reset()
        save_data.load(app)

    def test_each_old_step_keeps_its_darkness(self):
        for step, level in enumerate((0, 60, 100, 150)):
            self.load_display({"court_dim": step})
            self.assertAlmostEqual(display.court_dim_level, level / 255, msg = f"old step {step}")

    def test_the_slider_is_saved(self):
        display.court_dim_level = 0.31
        save_data.save(app)
        display.reset()
        save_data.load(app)
        self.assertAlmostEqual(display.court_dim_level, 0.31)

    def test_nonsense_is_ignored(self):
        self.load_display({"court_dim": 9})
        self.assertAlmostEqual(display.court_dim_level, 0.5)
        self.load_display({"court_dim_level": 7})
        self.assertEqual(display.court_dim_level, 1, "kept in range")


if __name__ == "__main__":
    unittest.main()

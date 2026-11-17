"""The game mode picker on Match Setup, 1.7 (Rowan's 1.7 plan, 2026-11-17).

Every mode has an on/off, any of them together; Chaos and Switch have a timing beside them, and
picking a timing turns its mode on.  A Match Settings button opens the rest of the rules.
"""
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

m = app.settings.match


class Picker(unittest.TestCase):
    def setUp(self):
        m.reset()
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("match_setup", mute = True)
        harness.settle(app)
        self.screen = sm.current()
        self.screen.draw(app.virtual)

    def tearDown(self):
        m.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def click(self, key):
        self.screen.draw(app.virtual)
        x, y = self.screen.ui_hitboxes[key].center
        pos = (x / app.sx, y / app.sy)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos))

    def test_every_mode_has_a_switch(self):
        for mode in m.MODES:
            self.assertIn(f"toggle_mode_{mode}", self.screen.ui_hitboxes)

    def test_any_of_them_together(self):
        for mode in m.MODES:
            self.click(f"toggle_mode_{mode}")
        self.assertEqual(m.modes_on(), list(m.MODES))
        self.click("toggle_mode_curveball")
        self.assertNotIn("curveball", m.modes_on())
        self.assertEqual(len(m.modes_on()), len(m.MODES) - 1)

    def test_picking_a_timing_turns_its_mode_on(self):
        self.click("cycle_chaos_timing_right")
        self.assertTrue(m.mode_chaos)
        self.assertEqual(m.CHAOS_TIMINGS[m.chaos_timing], "Constant drift")
        for name in ("Mid-rally", "Both", "Every point"):
            self.click("cycle_switch_timing_right")
            self.assertEqual(m.SWITCH_TIMINGS[m.switch_timing], name)
        self.assertTrue(m.mode_switch)
        self.click("toggle_mode_switch")
        self.assertFalse(m.mode_switch)
        self.assertEqual(m.switch_timing, 0, "it keeps its timing while off")

    def test_the_court_still_cycles(self):
        self.click("cycle_court_right")
        self.assertEqual(m.court, 1)

    def test_match_settings_opens_the_rules(self):
        self.click("open_match_settings")
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "gameplay")

    def test_everything_fits_and_nothing_overlaps(self):
        boxes = self.screen.ui_hitboxes
        panel = app.ui_layout.PANEL
        for key, rect in boxes.items():
            if key != "back":
                self.assertTrue(panel.contains(rect), f"{key} spills out of the panel")
        keys = [k for k in boxes if k != "back"]
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                self.assertFalse(boxes[a].colliderect(boxes[b]), f"{a} overlaps {b}")

    def test_each_mode_explains_itself(self):
        tips = app.renderer.MODE_TIPS
        self.assertEqual(set(tips), set(m.MODES))
        self.assertIn("Constant drift", tips["chaos"])
        self.assertIn("score stay yours", tips["switch"])

    def test_the_match_starts_with_them(self):
        m.mode_twin_ball = True
        self.click("start_match")
        harness.settle(app)
        game = app.state_manager.current().game
        self.assertEqual(len(game.powerups.balls()), 2)


if __name__ == "__main__":
    unittest.main()

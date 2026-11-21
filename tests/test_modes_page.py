"""The Talismans page's Modes view, 1.9 (Rowan, 2026-11-21).

"I want it to be integrated into the power-ups menu ... a button ... at the bottom left ... the
same vertical height as back and reset to default ... it reads switch to modes, and then clicking on
it brings you to the mode screen, which looks very similar to the power-up screen, except instead of
a list of power-ups, it has the list of modes, and then hovering over the modes gives you the
information of the mode at the bottom, where the box is.  You have an all off button, and I guess
for consistency, an all on button as well."

Match settings' Choose Modes (beside Choose Talismans) opens the page on its Modes view.  Each mode's
tile has its talisman's picture (CHAOS, which has none, a new one: a flurry of talismans).
"""
import unittest
from unittest import mock

from tests import harness

app = harness.app()

import pygame                                                               # noqa: E402

from tests.test_settings_menus import click, open_modes, open_screen        # noqa: E402
from tests.test_talismans_not_power_ups import texts                        # noqa: E402

m = app.settings.match
sm = app.state_manager


class ModesView(unittest.TestCase):
    def tearDown(self):
        m.reset()
        sm.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_choose_modes_opens_it(self):
        sm.set_state("main_menu", mute = True)
        sm.push_state("match_setup", mute = True)
        sm.push_state("match", mute = True)
        harness.settle(app)
        click(sm.current(), "open_modes")
        harness.settle(app)
        page = sm.current()
        self.assertEqual((page.NAME, page.view), ("powerups", "modes"))
        page.draw(app.virtual)
        page.handle_event(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_ESCAPE))
        harness.settle(app)
        self.assertEqual(sm.current().NAME, "match", "Esc: back to Match settings")

    def test_every_mode_has_a_tile(self):
        keys = open_modes().ui_hitboxes
        for mode in m.MODES:
            self.assertIn(f"cycle_mode_{mode}" if mode in ("chaos", "switch") else f"toggle_mode_{mode}", keys)
        for key in ("all_modes_on", "all_modes_off", "switch_view", "back", "reset_defaults"):
            self.assertIn(key, keys)
        self.assertFalse([k for k in keys if k.startswith("toggle_pu_")], "no talismans on it")

    def test_switching_back_and_forth(self):
        page = open_screen("powerups")
        self.assertEqual(page.view, "talismans")
        on = page.ui_hitboxes["all_pu_on"]
        button = page.ui_hitboxes["switch_view"]
        click(page, "switch_view")
        page.draw(app.virtual)
        self.assertEqual(page.view, "modes")
        self.assertIn("toggle_mode_twin_ball", page.ui_hitboxes)
        self.assertEqual(page.ui_hitboxes["all_modes_on"], on, "All On doesn't jump")
        self.assertEqual(page.ui_hitboxes["switch_view"], button, "nor does the switch button")
        self.assertIn("Switch to Talismans", texts(page))
        click(page, "switch_view")
        page.draw(app.virtual)
        self.assertEqual(page.view, "talismans")
        self.assertIn("toggle_pu_fire", page.ui_hitboxes)

    def test_level_with_back(self):
        boxes = open_modes().ui_hitboxes
        switch, back = boxes["switch_view"], boxes["back"]
        self.assertLess(abs(switch.centery - back.centery), 3)
        # (in the footer's middle, right of Back at the bottom left, since after 1.9's release)
        self.assertGreater(switch.left, back.right, "to its right")

    def test_all_on_all_off(self):
        page = open_modes()
        click(page, "all_modes_on")
        self.assertEqual(m.modes_on(), list(m.MODES))
        click(page, "all_modes_off")
        self.assertEqual(m.modes_on(), [])

    def test_each_switch(self):
        page = open_modes()
        click(page, "toggle_mode_black_hole")
        self.assertTrue(m.mode_black_hole)
        click(page, "cycle_mode_switch")
        click(page, "cycle_mode_switch")
        self.assertEqual((m.mode_switch, m.switch_timing), (True, 1), "Soul Swap: Mid-rally")

    def test_reset_is_the_modes_only(self):
        m.mode_curveball, m.chaos_timing, m.powerups = True, 1, False
        page = open_modes()
        click(page, "reset_defaults")
        harness.settle(app)
        self.assertEqual(sm.current().NAME, "confirm_choice")
        sm.current().action()
        self.assertEqual((m.modes_on(), m.chaos_timing), ([], 0))
        self.assertFalse(m.powerups, "the talismans left alone")

    def test_pointing_at_a_mode_describes_it(self):
        page = open_modes()
        self.assertTrue(any("Point at a mode" in t for t in texts(page)))
        tile = page.ui_hitboxes["toggle_mode_black_hole"]
        with mock.patch.object(app, "pointer", lambda: tile.center):
            page.draw(app.virtual)                  # (the tile notes it's pointed at)
            drawn = texts(page)
        self.assertIn("Black Hole", drawn)
        self.assertTrue(any("Game mode" in t for t in drawn))
        self.assertTrue(any(t.startswith("A black hole drifts") for t in drawn))

    def test_the_counts_on_match_settings(self):
        m.mode_twin_ball = True
        drawn = texts(open_screen("match"))
        self.assertIn("1 of 7 on", drawn)

    def test_chaos_has_a_picture(self):
        icon = app.art.power_icon(64, "rush", "Wild")
        self.assertEqual(icon.get_size(), (64, 64))


if __name__ == "__main__":
    unittest.main()

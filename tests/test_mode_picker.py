"""The game mode picker on Match Setup, 1.7 (Rowan's 1.7 plan, 2026-11-17).

Every mode has an on/off, any of them together; Chaos and Switch have a timing beside them, and
picking a timing turns its mode on.  A Match Settings button opens the rest of the rules.

Rowan's playtest of 1.7 (same day): Chaos and Switch are one button each, cycling Off and their
versions, instead of an on/off with the version beside it.

Rowan, 1.9: the modes leave Match Setup ("Definitely not the modes. Move that back into extra
settings"): the picker is in Match Settings, opened from Match Setup.  Then it moves behind Match
Settings' Choose Modes, onto the Talismans page's Modes view.
"""
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

m = app.settings.match


class Screen(unittest.TestCase):
    # (Match Settings, opened from Match Setup, then its Choose Modes: the Talismans page's Modes
    # view, later in 1.9)
    SCREENS = ("match_setup", "match", ("powerups", {"view": "modes"}))

    def setUp(self):
        m.reset()
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        for name in self.SCREENS:
            name, kwargs = name if isinstance(name, tuple) else (name, {})
            sm.push_state(name, mute = True, **kwargs)
        harness.settle(app)
        self.screen = sm.current()
        self.screen.draw(app.virtual)

    def tearDown(self):
        m.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def click(self, key):
        harness.show(self.screen, key)          # (the Match page scrolls)
        x, y = self.screen.ui_hitboxes[key].center
        pos = (x / app.sx, y / app.sy)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos))


class Picker(Screen):
    CYCLED = ("chaos", "switch")

    def button(self, mode):
        return f"cycle_mode_{mode}" if mode in self.CYCLED else f"toggle_mode_{mode}"

    def test_every_mode_has_a_button(self):
        boxes = harness.every_box(self.screen)
        for mode in m.MODES:
            self.assertIn(self.button(mode), boxes)
        for mode in self.CYCLED:
            self.assertNotIn(f"cycle_{mode}_timing_left", boxes, "no separate version selector")

    def test_any_of_them_together(self):
        for mode in m.MODES:
            self.click(self.button(mode))
        self.assertEqual(m.modes_on(), list(m.MODES))
        self.click("toggle_mode_curveball")
        self.assertNotIn("curveball", m.modes_on())
        self.assertEqual(len(m.modes_on()), len(m.MODES) - 1)

    def test_chaos_and_switch_cycle_off_and_their_versions(self):
        seen = []
        for _ in range(3):
            self.click("cycle_mode_chaos")
            seen.append(m.CHAOS_TIMINGS[m.chaos_timing] if m.mode_chaos else "Off")
        self.assertEqual(seen, ["Every point", "Constant drift", "Off"])
        seen = []
        for _ in range(3):
            self.click("cycle_mode_switch")
            seen.append(m.SWITCH_TIMINGS[m.switch_timing] if m.mode_switch else "Off")
        self.assertEqual(seen, ["Every point", "Mid-rally", "Off"])

    def test_each_mode_explains_itself(self):
        tips = app.renderer.MODE_TIPS
        self.assertEqual(set(tips), set(m.MODES))
        self.assertIn("Constant drift", tips["chaos"])
        self.assertIn("score stay yours", tips["switch"])


class MatchSetup(Screen):
    SCREENS = ("match_setup",)

    def test_no_modes_here(self):
        self.assertFalse([k for k in self.screen.ui_hitboxes if "_mode_" in k], "in Match Settings (1.9)")

    def test_the_court_still_cycles(self):
        self.click("cycle_court_right")
        self.assertEqual(m.court, 1)

    def test_match_settings_opens_the_rules(self):
        self.click("open_match_settings")
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "match")

    def test_everything_fits_and_nothing_overlaps(self):
        boxes = self.screen.ui_hitboxes
        panel = app.ui_layout.PANEL
        footer = ("back", "open_match_settings", "start_match")        # (the last two by Back since later in 1.9)
        for key, rect in boxes.items():
            if key not in footer:
                self.assertTrue(panel.contains(rect), f"{key} spills out of the panel")
        keys = [k for k in boxes if k != "back"]
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                self.assertFalse(boxes[a].colliderect(boxes[b]), f"{a} overlaps {b}")

    def test_the_match_starts_with_them(self):
        m.mode_twin_ball = True
        self.click("start_match")
        harness.settle(app)
        game = app.state_manager.current().game
        self.assertEqual(len(game.powerups.balls()), 2)


if __name__ == "__main__":
    unittest.main()

"""The screen for hosting an online match, brought up to 1.7 (Rowan's playtest of 1.7, 2026-11-17).

Like Match Setup: the game modes to pick, the court, and a Match Settings button (it said Gameplay
Settings, which is your keys and Auto-Pause since 1.7), with a line of the other rules.  The friend's
screen and the public list name Chaos's and Switch's versions, and past three modes count the rest,
so the line still fits with every mode on.
"""
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from core import net as netcode, rooms                          # noqa: E402
from core.net import HostSession                                # noqa: E402

netcode.STUN_SERVERS = []                    # nothing here may reach the public servers
rooms.BROKERS = [("127.0.0.1", 1)]

m = app.settings.match


class HostScreen(unittest.TestCase):
    def setUp(self):
        m.reset()
        app.net = HostSession(app, port = 0, upnp = False)
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("online", mute = True)
        harness.settle(app)
        self.screen = sm.current()
        self.screen.set_mode("host")
        self.screen.draw(app.virtual)

    def tearDown(self):
        m.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)
        app.leave_online()

    def click(self, key):
        self.screen.draw(app.virtual)
        x, y = self.screen.ui_hitboxes[key].center
        pos = (x / app.sx, y / app.sy)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos))

    def test_the_modes_as_on_match_setup(self):
        for mode in m.MODES:
            key = f"cycle_mode_{mode}" if mode in ("chaos", "switch") else f"toggle_mode_{mode}"
            self.assertIn(key, self.screen.ui_hitboxes)
        self.click("toggle_mode_twin_ball")
        self.assertTrue(m.mode_twin_ball)
        self.click("cycle_mode_switch")
        self.click("cycle_mode_switch")
        self.assertEqual((m.mode_switch, m.switch_timing), (True, 1), "Switch: Mid-rally")

    def test_the_court_still_cycles(self):
        self.click("cycle_court_right")
        self.assertEqual(m.court, 1)
        self.click("cycle_court_left")
        self.assertEqual(m.court, 0)

    def test_match_settings(self):
        from render.ui.layout import Button, _val
        from tests.test_settings_menus import laid_out
        body, _ = self.screen._laid
        button = next(n for n in laid_out(body) if isinstance(n, Button) and n.key == "online_settings")
        self.assertEqual(_val(button.text), "Match Settings")
        self.click("online_settings")
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "match")

    def test_everything_fits_and_nothing_overlaps(self):
        boxes = {k: r for k, r in self.screen.ui_hitboxes.items() if k != "back"}
        panel = app.ui_layout.PANEL
        for key, rect in boxes.items():
            self.assertTrue(panel.contains(rect), f"{key} spills out of the panel")
        keys = list(boxes)
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                self.assertFalse(boxes[a].colliderect(boxes[b]), f"{a} overlaps {b}")


class Summary(unittest.TestCase):
    def setUp(self):
        m.reset()
        self.net = HostSession(app, port = 0, upnp = False)

    def tearDown(self):
        m.reset()
        self.net.close()

    def test_versions_named(self):
        m.mode_chaos, m.chaos_timing = True, 1
        m.mode_switch, m.switch_timing = True, 1
        line = self.net.settings_summary()
        self.assertIn("Shape Shift: Constant drift", line)          # (Chaos and Switch till 1.9)
        self.assertIn("Soul Swap: Mid-rally", line)

    def test_past_three_the_rest_are_counted(self):
        for mode in m.MODES:
            setattr(m, "mode_" + mode, True)
        line = self.net.settings_summary()
        self.assertTrue(line.endswith("5 more modes"), line)
        width = app.ui_layout.fnt(0.023, 1.0).size(line + "  -  You play Blue")[0]
        self.assertLess(width, app.ui_layout.PANEL.width - 2 * app.ui_layout.PANEL_SIDE, "it fits")

    def test_the_hosts_own_line_leaves_the_modes_to_the_buttons(self):
        m.mode_curveball = True
        self.assertIn("Curveball", self.net.settings_summary())
        self.assertNotIn("Curveball", self.net.settings_summary(modes = False))


if __name__ == "__main__":
    unittest.main()

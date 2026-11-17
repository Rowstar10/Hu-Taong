"""A Reset Ball & Paddles button, 1.6 (Rowan's playtest list, 2026-11-16).

Under "Randomise Ball & Paddles": puts the ball's and paddles' sizes and speeds back to their
defaults, and nothing else.
"""
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

g = app.settings.match
FIELDS = ("ball_speed", "ball_diameter", "paddle_speed", "paddle_height", "paddle_width")


class ResetBallAndPaddles(unittest.TestCase):
    def setUp(self):
        g.reset()
        self.defaults = {name: getattr(g, name) for name in FIELDS}
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("gameplay", mute = True)
        harness.settle(app)
        self.screen = sm.current()

    def tearDown(self):
        g.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def click(self, key):
        self.screen.draw(app.virtual)
        x, y = self.screen.ui_hitboxes[key].center
        pos = (x / app.sx, y / app.sy)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos))

    def test_it_sits_right_under_randomise(self):
        self.screen.draw(app.virtual)
        rand, reset = self.screen.ui_hitboxes["randomise_all"], self.screen.ui_hitboxes["reset_ball_and_paddles"]
        self.assertGreater(reset.top, rand.centery)
        self.assertLess(reset.top - rand.bottom, 60)
        self.assertLess(abs(reset.centerx - rand.centerx), 5)

    def test_it_undoes_randomise(self):
        g.pace = 1.4
        g.middle_wall = not g.middle_wall
        wall = g.middle_wall
        for _ in range(5):                       # five goes: surely something moved
            self.click("randomise_all")
        self.assertNotEqual({name: getattr(g, name) for name in FIELDS}, self.defaults)
        self.click("reset_ball_and_paddles")
        self.assertEqual({name: getattr(g, name) for name in FIELDS}, self.defaults)
        self.assertEqual((g.pace, g.middle_wall), (1.4, wall), "nothing else is touched")


if __name__ == "__main__":
    unittest.main()

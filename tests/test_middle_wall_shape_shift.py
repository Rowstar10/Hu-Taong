"""Through the Middle Wall under Shape Shift, 1.9 (Rowan, 2026-11-20).

"There is also a bug where you can phase through the middle invisible wall when your paddle is
changing size under the Shape Shift effect."  The Middle Wall is a line the paddles' sweep stops
at; a paddle that grew while pressed against it began the next step already across the line,
the sweep saw no wall ahead, and the paddle walked on to the far side (5 runs in 6, holding right
for 8 s with Constant drift).  Physics.resolve_overlaps now puts it back on its own side.
"""
import random
import unittest

from tests import harness

app = harness.app()

from config import BASE_W                                       # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402

m = app.settings.match
MID = BASE_W / 2
DT = 1 / 120


class MiddleWall(unittest.TestCase):
    def tearDown(self):
        app.keys_down = set()
        m.reset()

    def game(self, **rules):
        m.reset()
        m.powerups = False
        for name, value in rules.items():
            setattr(m, name, value)
        g = Hu_Taong(app)
        g.start()
        g.countdown, g.paused = None, False
        g.p1.ai_enabled = g.p2.ai_enabled = False
        self.addCleanup(g.stop)
        return g

    def press_on(self, g, paddle, key, seconds):
        app.keys_down = {key}
        most = 0.0
        for _ in range(int(seconds / DT)):
            g.ball.vx = g.ball.vy = 0.0                         # (the ball out of the way)
            g.ball.x0, g.ball.x1 = 1500, 1500 + g.ball.width
            g.update(DT)
            most = max(most, paddle.x1 - MID if paddle.is_left else MID - paddle.x0)
        app.keys_down = set()
        return most

    def test_shape_shift_drift_never_takes_it_through(self):
        for seed in range(3):
            random.seed(seed)
            g = self.game(mode_chaos = True, chaos_timing = 1)  # Shape Shift's drift, all match
            with self.subTest(seed = seed, side = "Red"):
                self.assertLessEqual(self.press_on(g, g.p1, g.p1.right, 4.0), 0.5)
            with self.subTest(seed = seed, side = "Blue"):
                self.assertLessEqual(self.press_on(g, g.p2, g.p2.left, 4.0), 0.5)

    def test_grown_against_the_wall_it_goes_back(self):
        g = self.game()
        p = g.p1
        p.x0, p.x1 = MID - p.width - 0.5, MID - 0.5               # touching the wall
        Hu_Taong.resize(p, p.width * 2.5, p.height)               # (as a big drift, or Giant Paddle, would)
        self.assertGreater(p.x1, MID, "(across the line now)")
        self.assertLessEqual(self.press_on(g, p, p.right, 0.5), 0.5)

    def test_with_the_wall_down_it_still_crosses(self):
        g = self.game(middle_wall = False)
        self.assertGreater(self.press_on(g, g.p1, g.p1.right, 2.0), 200, "Middle Wall off: it may roam")


if __name__ == "__main__":
    unittest.main()

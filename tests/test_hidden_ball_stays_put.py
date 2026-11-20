"""A ball inside a black hole or portal stays put, 1.9 (Rowan's clip, 2026-11-20).

"The red ball as a snowball got sucked into a black hole that then collapsed, and as it collapsed,
it said that red won that point, but I couldn't see where the red ball exited the collapsing black
hole."  The clip (Red 47-39 Blue, Twin Ball, CHAOS) shows the Firecracker strapped to the ball
banging while the ball was inside the collapsing hole: the bang shot it off, still out of sight,
and it crossed the court unseen and went in.  A ball inside is held still and hidden until it comes
out, so the Firecracker's fuse now waits while it's inside, and Curveball's leftover spin doesn't
bend it either.
"""
import unittest

from tests import harness

app = harness.app()

from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import PowerUps                              # noqa: E402

m = app.settings.match
DT = 1 / 120


class Inside(unittest.TestCase):
    def setUp(self):
        m.reset()
        m.powerups = True
        self.game = g = Hu_Taong(app)
        g.start()
        g.countdown, g.paused = None, False
        self.pu = g.powerups
        self.pu.wait = 999.0
        g.p1.ai_enabled = g.p2.ai_enabled = False

    def tearDown(self):
        self.game.stop()
        m.reset()

    def swallow(self, collapse = True):
        pu, ball = self.pu, self.game.ball
        pu.open_hole()
        hole = pu.holes[-1]
        if collapse:
            hole["eaten"] = PowerUps.HOLE_GROWTHS              # full-grown: this one collapses
        ball.vx, ball.vy = 900.0, 200.0
        pu.swallow(ball, hole)
        self.assertTrue(ball.transit)
        return hole

    def run_for(self, seconds, until = lambda: False):
        for _ in range(int(seconds / DT)):
            self.game.update(DT)
            if until():
                return True
        return False

    def test_a_firecracker_waits_inside_a_collapsing_black_hole(self):
        ball, pu = self.game.ball, self.pu
        pu.cracker = {"fuse": 0.05, "taker": self.game.p1}
        self.swallow()
        where = (ball.x0, ball.y0)
        self.run_for(0.4, lambda: not ball.transit)
        self.assertTrue(ball.transit, "(still inside)")
        self.assertEqual((ball.x0, ball.y0), where, "held still, out of sight")
        self.assertEqual((ball.vx, ball.vy), (0.0, 0.0))
        self.assertIsNotNone(pu.cracker, "the fuse waits")
        self.assertAlmostEqual(pu.cracker["fuse"], 0.05)
        self.assertEqual((self.game.p1.score, self.game.p2.score), (0, 0))

    def test_and_bangs_once_it_is_out(self):
        ball, pu = self.game.ball, self.pu
        pu.cracker = {"fuse": 0.05, "taker": self.game.p1}
        self.swallow(collapse = False)                          # (a small hole: out again soon)
        self.assertTrue(self.run_for(3.0, lambda: not ball.transit), "it comes out")
        self.assertTrue(self.run_for(0.5, lambda: pu.cracker is None), "then the fuse burns down and it bangs")

    def test_curveball_spin_doesnt_move_it_inside(self):
        ball = self.game.ball
        ball.curve = 1800.0
        self.swallow()
        where = (ball.x0, ball.y0)
        self.run_for(0.3)
        self.assertEqual((ball.x0, ball.y0), where)

    def test_rowans_clip_still_plays(self):
        """(The clip itself, made before the fix, still loads and draws: tests/data has a copy.)"""
        import os
        from game.replay import Clip, ReplayView
        path = os.path.join(harness.GAME, "tests", "data", "clip_1.9_cracker_in_black_hole.htreplay")
        if not os.path.exists(path):
            self.skipTest("(the clip isn't in tests/data)")
        view = ReplayView(Clip.load(path), app)
        view.show(91)
        app.renderer.draw_world(app.virtual, view)


if __name__ == "__main__":
    unittest.main()

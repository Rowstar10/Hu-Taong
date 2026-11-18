"""Paddles slowing to a crawl, 1.8 (Rowan's playtest, 2026-11-18).

"For some reason the paddles slow right down sometimes... it seems kind of unpredictable... it
moves like a turtle."  With the Speed Cap on (or Classic physics), a paddle that hits the ball off
its face mustn't run on into it and knock it again (Paddle.keep_behind).  It was held back whenever
its own shot was anywhere ahead of it, right across the court: charging forward after a slow or
steep shot, it crept along at the ball's speed less 150 px/s, often near nothing.

Rowan's fourth playtest (same day) took the Speed Cap out with the rest of 1.8's physics (see
test_physics_rollback); these still check a paddle charges at full speed after its own shot.  And
Rowan found when it crawled: "when the paddles are moving in the same direction as the ball, slightly
behind it... if the ball is moving slowly to the left and the blue paddle tries to push it along with
greater speed, it won't be able to do that."  That was the Speed Cap holding a paddle behind its own
ball; now it catches the ball up and pushes it along.
"""
import unittest

from tests import harness

app = harness.app()

from game.hu_taong import Hu_Taong                              # noqa: E402
from game.physics import Physics                                # noqa: E402
from tests.test_powerup_fixes import place                      # noqa: E402

m = app.settings.match
DT = 1 / 120


class Charging(unittest.TestCase):
    def setUp(self):
        m.reset()
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.game.powerups.wait = 999.0
        self.p1, self.ball = self.game.p1, self.game.ball
        self.p1.ai_enabled = self.game.p2.ai_enabled = False
        self.game.objects.remove(self.game.p2)                  # (so only Red could touch it)

    def tearDown(self):
        app.keys_down = set()
        self.game.stop()
        m.reset()

    def after_my_hit(self, ball_x, ball_vx, ball_vy = 0.0):
        """Red has just hit the ball, which is going away at (ball_vx, ball_vy) from ball_x."""
        p1, ball = self.p1, self.ball
        place(p1, 200, 540)
        place(ball, ball_x, 540)
        ball.vx, ball.vy = ball_vx, ball_vy
        ball.last_paddle = p1
        p1.vx = p1.vy = 0.0

    def unhindered(self, seconds):
        """The fastest Red gets charging from a standstill with nothing ahead of it."""
        place(self.p1, 200, 540)
        self.p1.vx = self.p1.vy = 0.0
        self.ball.last_paddle = None
        place(self.ball, 1700, 100)
        return max(self.charge(seconds))

    def charge(self, seconds):
        app.keys_down = {self.p1.right}
        speeds = []
        for _ in range(round(seconds / DT)):
            x = self.p1.x0
            Physics.step(self.game, DT)
            speeds.append((self.p1.x0 - x) / DT)
        app.keys_down = set()
        return speeds

    def test_full_speed_after_a_slow_shot_well_ahead(self):
        free = self.unhindered(0.3)
        self.after_my_hit(ball_x = 900, ball_vx = 300.0)
        self.assertGreater(max(self.charge(0.3)), free * 0.97, "not crawling")

    def test_it_pushes_a_slow_ball_along(self):
        free = self.unhindered(0.3)
        self.after_my_hit(ball_x = 200 + self.p1.width / 2 + self.ball.width / 2 + 20, ball_vx = 150.0)
        speeds = self.charge(0.4)
        self.assertGreater(max(speeds), free * 0.97, "stuck behind the ball")
        self.assertGreater(self.ball.vx, 1000.0, "it pushed the ball along")

    def test_full_speed_after_a_steep_shot(self):
        free = self.unhindered(0.3)
        self.after_my_hit(ball_x = 600, ball_vx = 160.0, ball_vy = -1400.0)
        self.assertGreater(max(self.charge(0.3)), free * 0.97)

    def test_still_cant_catch_its_own_shot(self):
        self.after_my_hit(ball_x = 500, ball_vx = 300.0)
        hits = self.ball.rally_value
        self.charge(1.0)
        self.assertEqual(self.ball.rally_value, hits, "it never knocked it again")
        self.assertLess(self.p1.x1, self.ball.x0, "it trails it")

    def test_a_ball_coming_back_holds_nothing_back(self):
        free = self.unhindered(0.2)
        self.after_my_hit(ball_x = 900, ball_vx = 300.0)
        self.ball.vx = -500.0                                   # back off something, nobody else touching it
        self.assertGreater(max(self.charge(0.2)), free * 0.97)


if __name__ == "__main__":
    unittest.main()

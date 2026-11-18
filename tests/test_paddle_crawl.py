"""Paddles slowing to a crawl, 1.8 (Rowan's playtest, 2026-11-18).

"For some reason the paddles slow right down sometimes... it seems kind of unpredictable... it
moves like a turtle."  With the Speed Cap on (or Classic physics), a paddle that hits the ball off
its face mustn't run on into it and knock it again (Paddle.keep_behind).  It was held back whenever
its own shot was anywhere ahead of it, right across the court: charging forward after a slow or
steep shot, it crept along at the ball's speed less 150 px/s, often near nothing.  Now it's held back
only when it's about to catch the ball, and never by a ball coming back at it.

Rowan's fourth playtest (same day) found where it still crawled: "when the paddles are moving in the
same direction as the ball, slightly behind it... if the ball is moving slowly to the left and the
blue paddle tries to push it along with greater speed, it won't be able to do that."  Held back to
the ball's speed less 150 px/s, it could never catch a slow ball up.  Now a ball slower than the cap
lets a paddle catch it and knock it on (the knock capped as ever); only a ball already going at the
cap or faster holds it back, and then it isn't a crawl.  (Rowan briefly had 1.8's physics rolled back,
then asked for them again.)
"""
import unittest

from tests import harness

app = harness.app()

from game import engines                                        # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.physics import Physics                                # noqa: E402
from tests.test_powerup_fixes import place                      # noqa: E402

m = app.settings.match
DT = 1 / 120


class Charging(unittest.TestCase):
    def setUp(self):
        m.reset()
        m.physics, m.speed_cap = engines.CURRENT, True
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
        p1.give_way(ball, 1)

    def unhindered(self, seconds):
        """The fastest Red gets charging from a standstill with nothing ahead of it."""
        place(self.p1, 200, 540)
        self.p1.vx = self.p1.vy = 0.0
        self.p1.trail = None
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

    def pushing(self, ball_vx):
        """Red has just hit the ball, going away at ball_vx just ahead of it; Red charges after it.
        Answers how fast Red went, at best and over the last 0.15 s, out of its unhindered best."""
        free = self.unhindered(0.4)
        self.after_my_hit(ball_x = 200 + self.p1.width / 2 + self.ball.width / 2 + 20, ball_vx = ball_vx)
        speeds = self.charge(0.4)
        return max(speeds) / free, min(speeds[-18:]) / free

    def test_it_pushes_a_slow_ball_along(self):
        best, last = self.pushing(150.0)
        self.assertGreater(best, 0.85, "stuck behind the ball (it went at 22% before)")
        self.assertGreater(last, 0.8)
        self.assertGreater(self.ball.vx, 1000.0, "it pushed the ball along")

    def test_it_pushes_a_ball_at_serve_speed_along(self):
        serve = self.ball.speed * 2 ** 0.5
        best, last = self.pushing(serve)
        self.assertGreater(best, 0.85, "stuck behind the ball (it went at 75% before)")
        self.assertGreater(last, 0.8)
        self.assertGreater(self.ball.vx, serve * 1.3, "it pushed the ball along")

    def test_never_past_the_cap_by_pushing(self):
        from game import engines
        self.pushing(150.0)
        self.assertLess(self.ball.vx, engines.cap_drive(self.ball.speed) * 1.25)

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

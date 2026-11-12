"""The computer player and power-ups, 1.6 (batch 4 of the power-up plan, from the 1.4 reviews).

- Sticky Goo: the AI read a stuck ball as leaving on its old return, but the holding paddle's
  movement aims the sling, so any flick fooled it every time.
- Lantern Night: the AI saw perfectly in the dark, so against the computer only the person was
  handicapped.  Outside the lantern light it now misjudges the ball as it does a Ghost Ball.
"""
import math
import unittest

from tests import harness

harness.app()

from tests.test_powerup_fixes import Match, place   # noqa: E402  (after the harness has set things up)


class StickySling(Match):
    def test_ai_reads_where_the_sling_will_go(self):
        p1, p2, ball, pu = self.p1, self.p2, self.ball, self.pu
        p1.effects["sticky"] = 10.0
        place(p1, 400, 540)
        place(ball, p1.x1 + ball.width / 2 + 2, 560)
        ball.vx, ball.vy = 800.0, 300.0                 # its return would have gone down...
        pu.stick(ball, p1)
        p1.vx, p1.vy = 0.0, -p1.speed                   # ...but Red flicks the paddle up
        want = pu.sling(ball.stuck, p1, ball.speed)
        p2.ai.reset()
        _x, _y, vx, vy = p2.ai.perceive(ball, 1 / 120, 0.0)
        self.assertLess(vy, 0, "the AI expected it to go down")
        self.assertAlmostEqual(vx, want[0], delta = 1)
        self.assertAlmostEqual(vy, want[1], delta = 1)


class LanternNight(Match):
    def misread(self, night, ball_x):
        pu, ball, p2 = self.pu, self.ball, self.p2
        pu.lantern = {"age": 5.0, "lifting": None} if night else None
        place(ball, ball_x, 540)
        ball.vx, ball.vy = 900.0, 0.0                   # coming at Blue's goal
        return p2.ai.params()

    def test_misjudges_the_ball_in_the_dark(self):
        day, night = self.misread(False, 700), self.misread(True, 700)
        self.assertGreater(night["misread"], day["misread"] * 1.4)
        self.assertGreater(night["reaction"], day["reaction"])

    def test_sees_it_in_the_lantern_light(self):
        near = self.p2.x0 - 150
        day, night = self.misread(False, near), self.misread(True, near)
        self.assertEqual(night["misread"], day["misread"])
        self.assertEqual(night["reaction"], day["reaction"])


if __name__ == "__main__":
    unittest.main()

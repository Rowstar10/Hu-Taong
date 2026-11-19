"""AIs don't throw points away chasing talismans, 1.9 (Rowan, 2026-11-19).

"The AIs sometimes get messed up and lose a point because they went for a powerup at the wrong
moment."  An AI reckoned it had as long as the ball would take to reach the far wall and come
back at the same speed; but the other paddle meets it in front of the wall, and its returns are
often faster (1 in 10 twice as fast or more, AI v AI), and it kept on after a talisman until it
was far too late, so a sharp AI was caught out of place.  Now it reckons the soonest the ball could
be back, keeps time to spare, and gives up a chase it can't finish.  It still takes the talismans
it has time for.
"""
import math
import unittest

from tests import harness

app = harness.app()

from config import BASE_W                                       # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from objects.ai import PaddleAI                                 # noqa: E402

m = app.settings.match


class Timing(unittest.TestCase):
    def setUp(self):
        m.reset()
        m.powerups, m.ai_difficulty = True, 3                   # Hard
        self.g = Hu_Taong(app)
        self.g.start()
        self.g.countdown, self.g.paused = None, False
        self.ai = self.g.p1.ai
        self.ai.pickup_hope = 0.0
        self.k = self.ai.params()

    def tearDown(self):
        self.g.stop()
        m.reset()

    def away(self, speed, x = BASE_W / 2):
        """The ball just sent back by Red's AI (on the left), heading for Blue at `speed`."""
        b, r = self.g.ball, self.g.ball.width / 2
        b.x0, b.x1, b.y0, b.y1 = x - r, x + r, 540 - r, 540 + r
        b.vx, b.vy = speed, 0.0

    def offer(self, x, y):
        self.g.powerups.pickups = [{"kind": "giant", "x": x, "y": y, "age": 0.0}]

    def old_reckoning_goes(self, item):
        """Would the 1.8 AI have set off for it?"""
        p, ball = self.g.p1, self.g.ball
        px, py = (p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2
        back = (abs(BASE_W - (ball.x0 + ball.x1) / 2) + abs(BASE_W - px)) / abs(ball.vx)
        trip = 2 * math.hypot(item["x"] - px, item["y"] - py) / (p.speed * self.k["pace"])
        return trip < back * 0.6 * self.k["aim"]

    def test_no_chase_it_cant_get_back_from(self):
        self.away(1800)
        self.offer(400, 540)
        item = self.g.powerups.pickups[0]
        self.assertTrue(self.old_reckoning_goes(item), "(1.8's AI would have gone for this one)")
        self.assertIsNone(self.ai.pickup_target(self.k))

    def test_it_still_takes_one_it_has_time_for(self):
        self.away(600, x = 1100)
        p = self.g.p1
        self.offer((p.x0 + p.x1) / 2 + 160, 420)
        self.assertIsNotNone(self.ai.pickup_target(self.k))

    def test_soonest_return_is_sooner_than_far_wall_and_back(self):
        self.away(1200)
        p, ball = self.g.p1, self.g.ball
        far_wall = (BASE_W - (ball.x0 + ball.x1) / 2 + BASE_W - (p.x0 + p.x1) / 2) / ball.vx
        self.assertLess(self.ai.time_to_return(), far_wall * 0.85)

    def test_gives_up_a_chase_it_cant_finish(self):
        self.away(600, x = 1100)
        p = self.g.p1
        self.offer((p.x0 + p.x1) / 2 + 160, 420)
        self.assertIsNotNone(self.ai.committed_pickup(self.k))
        self.away(2600, x = 1500)                               # Blue sends it straight back, hard
        self.g.p2.x0, self.g.p2.x1 = 1560, 1560 + self.g.p2.width
        self.g.powerups.pickups[0]["x"] = 900                   # (and the talisman's far off)
        self.assertIsNone(self.ai.committed_pickup(self.k))
        self.assertGreater(self.ai.pickup_cooldown, 0, "and leaves talismans alone for a moment")

    def test_misjudges_less_the_sharper_it_is(self):
        from objects.ai import SKILL
        misread = SKILL["misread"]
        self.assertTrue(all(b < a for a, b in zip(misread, misread[1:])))
        self.assertLessEqual(misread[4] / 400, 0.1, "Insane: under 10% out")


if __name__ == "__main__":
    unittest.main()

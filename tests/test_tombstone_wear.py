"""Tombstones wear down, and the Snowball smashes and ploughs through them, 1.8 (Rowan's 1.8 plan,
phase 2, 2026-11-18).

A Tombstone talisman's stone: every hit wears it down, three hits break it.  Spirit Fire chips it
as before (two blazing hits).  One hit from the Snowball smashes it, and a big Snowball (1.8 times
its own size) ploughs straight through, keeping 90% of its speed, in a burst of snow and stone
that replays and the friend's screen show too.  The court's own stones are as they were.
"""
import math
import unittest

from tests import harness

app = harness.app()

from game.hu_taong import Hu_Taong                              # noqa: E402
from game.physics import Physics                                # noqa: E402
from game.powerups import PowerUps                              # noqa: E402
from game.replay import ReplayView                              # noqa: E402

m = app.settings.match


class Stones(unittest.TestCase):
    COURT = 0

    def setUp(self):
        m.reset()
        m.court = self.COURT
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.pu = self.game.powerups
        self.pu.wait = 999.0
        self.ball = self.game.ball

    def tearDown(self):
        self.game.stop()
        m.reset()

    def tombstone(self):
        self.pu.collect({"kind": "tomb", "x": 900, "y": 500}, self.game.p1)
        stone = self.pu.tombs[-1]
        stone.age, stone.armed = 1.0, True
        stone.vy = stone.speed = 0.0
        return stone

    def hit(self, stone, speed = 900.0):
        """The ball knocks into the stone's left side."""
        ball, r = self.ball, self.ball.width / 2
        cy = (stone.y0 + stone.y1) / 2
        ball.x0, ball.x1 = stone.x0 - 2 * r, stone.x0
        ball.y0, ball.y1 = cy - r, cy + r
        ball.vx, ball.vy = speed, 0.0
        Physics.resolve_collision(ball, stone, {"t": 0.0, "normal": (-1, 0)})

    def test_three_hits_break_it(self):
        stone = self.tombstone()
        self.assertTrue(stone.worn)
        for _ in range(2):
            self.hit(stone)
            self.assertFalse(stone.broken)
        self.hit(stone)
        self.assertTrue(stone.broken)

    def test_two_blazing_hits_as_ever(self):
        stone = self.tombstone()
        self.ball.blazing = True
        self.hit(stone)
        self.assertFalse(stone.broken)
        self.hit(stone)
        self.assertTrue(stone.broken)

    def test_the_snowball_smashes_it_at_once(self):
        self.pu.collect({"kind": "snowball", "x": 900, "y": 500}, self.game.p1)
        stone = self.tombstone()
        self.hit(stone)
        self.assertTrue(stone.broken)
        self.assertLess(self.ball.vx, 0, "a small Snowball still bounces off")
        self.assertEqual(self.pu.ploughs, [])

    def test_a_big_snowball_ploughs_through(self):
        self.pu.collect({"kind": "snowball", "x": 900, "y": 500}, self.game.p1)
        self.pu.snow["size"] = PowerUps.PLOUGH_SIZE
        stone = self.tombstone()
        self.hit(stone, 900.0)
        self.assertTrue(stone.broken)
        self.assertAlmostEqual(self.ball.vx, 900.0 * PowerUps.PLOUGH_KEEP, delta = 1, msg = "straight on, a little slower")
        self.assertAlmostEqual(self.ball.vy, 0.0)
        self.assertEqual(len(self.pu.ploughs), 1)

    def test_the_burst_is_in_the_replay(self):
        self.pu.collect({"kind": "snowball", "x": 900, "y": 500}, self.game.p1)
        self.pu.snow["size"] = PowerUps.PLOUGH_SIZE
        stone = self.tombstone()
        self.hit(stone)
        for _ in range(3):
            self.game.recorder.capture(1 / 60)
        view = ReplayView(self.game.recorder.clip(), app)
        view.show(len(view.clip.frames) - 1)
        self.assertEqual(len(view.powerups.ploughs), 1)
        self.assertTrue(any(s.worn for s in view.stones))
        app.renderer.draw_world(app.virtual, view)


class CourtStones(Stones):
    COURT = 2                                                     # Graveyard: four headstones of its own

    def test_a_plain_hit_leaves_the_courts_own_alone(self):
        stone = next(o for o in self.game.objects if getattr(o, "is_obstacle", False))
        self.assertFalse(stone.worn)
        for _ in range(5):
            self.hit(stone)
        self.assertFalse(stone.broken)
        self.assertEqual(stone.hp, stone.max_hp)


if __name__ == "__main__":
    unittest.main()

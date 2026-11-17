"""Sticky Goo on a big Snowball, 1.6 (Rowan's playtest, 2026-11-17).

Sticky Goo was taken while a big Snowball was in play, and when the AI's paddle caught the ball it
teleported, downward, away from where it hit.  A big ball caught on the paddle's end has its middle
out past the end, and a held ball was kept no further out than the end, so it was dragged onto the
paddle: up to 70 px in one frame (58 times in 150 computer-v-computer points).  Now it's held where
it touched, and slung from there.

(The point being lost was the Snowball's own rule: a paddle shoved back into its own goal gives it
away.  That happens as often without the goo, and isn't changed here.)
"""
import math
import unittest

from tests import harness

app = harness.app()

from tests.test_powerup_fixes import Match, centre, place      # noqa: E402

DT = 1 / 120


class BigSnowballOnGoo(Match):
    def shoot(self, size, offset, ai = False, vy = 0.0):
        """A Snowball of this size at Blue's gooey paddle, its middle offset from the paddle's: px,
        or ("end", k) for k of its radius out past the paddle's end (negative: the top end).  Every
        frame's (ball centre, paddle centre, ball speed as the frame began, stuck) until it's slung
        away or 2 s pass."""
        p2, ball, pu = self.p2, self.ball, self.pu
        p2.ai_enabled = ai
        pu.snow = {"size": size}
        self.game.apply_gameplay_settings()
        self.p1.effects["sticky"] = p2.effects["sticky"] = 10.0
        place(p2, 1500, 540)                                # well out from its goal: room to be shoved
        r = ball.diameter / 2
        if isinstance(offset, tuple):
            k = offset[1]
            offset = math.copysign(p2.height / 2 + abs(k) * r, k)
        place(ball, p2.x0 - 150 - r, 540 + offset)
        ball.vx, ball.vy = 1400.0, vy
        pu.ball_v = (ball.vx, ball.vy)
        frames = []
        held = False
        for _ in range(int(2.0 / DT)):
            speed = math.hypot(ball.vx, ball.vy)
            self.game.update(DT)
            frames.append((centre(ball), centre(p2), speed, ball.stuck is not None))
            held = held or ball.stuck is not None
            if held and ball.stuck is None and len(frames) > 2 and not frames[-2][3]:
                break                                       # a few frames after it was slung
        return frames

    def worst_jump(self, frames):
        """The furthest the ball moved in a frame beyond its own speed and its paddle's."""
        worst = 0.0
        for (b0, p0, _, _), (b1, p1, speed, _) in zip(frames, frames[1:]):
            moved = math.hypot(b1[0] - b0[0], b1[1] - b0[1])
            carried = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            worst = max(worst, moved - speed * DT - carried)
        return worst

    def test_caught_on_either_end_it_doesnt_jump(self):
        for size in (1.8, 2.4):
            for offset in (("end", -0.8), ("end", -0.3), ("end", 0.3), ("end", 0.8)):
                with self.subTest(size = size, offset = offset):
                    self.setUp()
                    try:
                        frames = self.shoot(size, offset)
                        self.assertTrue(any(f[3] for f in frames), "it never stuck")
                        self.assertLess(self.worst_jump(frames), 3.0)
                    finally:
                        self.tearDown()

    def test_held_where_it_touched(self):
        frames = self.shoot(2.4, ("end", 0.6))
        stuck = [f for f in frames if f[3]]
        self.assertTrue(stuck)
        offsets = [ball[1] - paddle[1] for ball, paddle, _, _ in stuck]
        self.assertGreater(min(offsets), self.p2.height / 2, "its middle stays out past the paddle's end")
        # ...but some of it is always beside the paddle's face
        r = self.ball.diameter / 2
        self.assertLess(max(offsets), self.p2.height / 2 + r)

    def test_slung_away_from_the_paddle(self):
        frames = self.shoot(2.4, ("end", -0.6))
        self.assertTrue(any(f[3] for f in frames))
        self.assertIsNone(self.ball.stuck, "slung within 2 s")
        self.assertLess(self.ball.vx, 0, "back towards Red")
        self.assertLess(self.ball.x1, self.p2.x0, "from in front of the paddle, not through it")

    def test_with_the_ai_holding_it(self):
        """As Rowan saw it: the AI's paddle catches it and sweeps it about before slinging it."""
        frames = self.shoot(2.4, ("end", -0.7), ai = True)
        self.assertTrue(any(f[3] for f in frames))
        self.assertLess(self.worst_jump(frames), 3.0)

    def test_a_plain_ball_still_sticks_where_it_hits(self):
        frames = self.shoot(1.0, 40)
        stuck = [f for f in frames if f[3]]
        self.assertTrue(stuck)
        ball, paddle, _, _ = stuck[0]
        self.assertAlmostEqual(ball[1] - paddle[1], 40, delta = 3)
        self.assertLess(self.worst_jump(frames), 3.0)


if __name__ == "__main__":
    unittest.main()

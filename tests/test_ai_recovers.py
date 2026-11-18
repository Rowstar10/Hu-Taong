"""AIs go back round a ball that has got past them, 1.9 (Rowan, 2026-11-18).

"Make all AIs better at moving backwards and circling around behind the ball when it's in front to
save it from hitting their goal."  Until 1.9 only some AIs tried, at random (none at Baby, about half
at Insane), and with the Middle Wall up the rest stepped aside and let it in: given a ball behind it
with 0.7-1.5 s to spare, Normal saved 22 in 150 with the wall up.  Now every AI goes back round it,
keeping out of its row so it doesn't knock it in, hurrying, and heading for where it'll meet it.

And "make the hard and insane AIs a little harder": they read the ball better, react quicker and
lapse less, with shots no harder than before.
"""
import math
import random
import unittest

from tests import harness

app = harness.app()

from game.hu_taong import Hu_Taong                              # noqa: E402
from objects import ai as ai_mod                                # noqa: E402

m = app.settings.match


def scenario(level, wall, trial):
    """Red's AI pushed up the court with the ball behind it, heading for its goal with time to save
    it.  Answers "saved" or "goal"."""
    random.seed(1000 * level + trial)
    m.reset()
    m.powerups, m.middle_wall, m.ai_difficulty = False, wall, level
    g = Hu_Taong(app)
    g.start()
    g.countdown, g.paused = None, False
    p, ball = g.p1, g.ball
    p.ai_enabled, g.p2.ai_enabled = True, False
    g.objects.remove(g.p2)
    try:
        r = ball.width / 2
        px, py = random.uniform(380, 820), random.uniform(200, 880)
        p.x0, p.x1, p.y0, p.y1 = px - p.width / 2, px + p.width / 2, py - p.height / 2, py + p.height / 2
        bx, by = px - random.uniform(80, 250), py + random.uniform(-120, 120)
        speed, ang = bx / random.uniform(0.7, 1.5), random.uniform(-0.5, 0.5)
        ball.x0, ball.x1, ball.y0, ball.y1 = bx - r, bx + r, by - r, by + r
        ball.vx, ball.vy = -speed * math.cos(ang), speed * math.sin(ang)
        ball.last_paddle = g.p2
        p.ai.reset()
        for _ in range(int(2.5 * 120)):
            g.update(1 / 120)
            if g.p2.score:
                return "goal"
            if ball.last_paddle is p and ball.vx > 0:
                return "saved"
        return "goal"
    finally:
        g.stop()
        m.reset()


class GoesBackRound(unittest.TestCase):
    TRIALS = 16

    def saves(self, level, wall):
        return sum(scenario(level, wall, t) == "saved" for t in range(self.TRIALS))

    def test_with_the_wall_up(self):
        for level in (1, 2, 4):
            with self.subTest(level = m.ai_difficulties[level]):
                self.assertGreaterEqual(self.saves(level, True), self.TRIALS * 0.55)

    def test_with_the_wall_down(self):
        for level in (1, 2, 4):
            with self.subTest(level = m.ai_difficulties[level]):
                self.assertGreaterEqual(self.saves(level, False), self.TRIALS * 0.55)

    def test_every_ai_tries_now(self):
        self.assertNotIn("chase", ai_mod.SKILL)


class Levels(unittest.TestCase):
    def test_each_level_sharper_than_the_one_below(self):
        for name, falls in (("reaction", True), ("misread", True), ("wobble", True), ("lapse", True),
                            ("pace", False), ("aim", False)):
            row = ai_mod.SKILL[name]
            for a, b in zip(row, row[1:]):
                self.assertTrue(b < a if falls else b > a, (name, row))

    def test_hard_and_insane_sharper_than_in_1_8(self):
        was = {"reaction": (0.115, 0.075), "misread": (82, 42), "lapse": (0.04, 0.015), "pace": (0.87, 0.95)}
        for name, (hard, insane) in was.items():
            row = ai_mod.SKILL[name]
            better = (lambda new, old: new < old) if name != "pace" else (lambda new, old: new > old)
            self.assertTrue(better(row[3], hard) and better(row[4], insane), name)
        self.assertEqual(ai_mod.SKILL["strike"][3:], (0.45, 0.52), "their shots are no harder")


if __name__ == "__main__":
    unittest.main()

"""The Speed Cap, 1.8 (Rowan's 1.8 plan, 2026-11-17).

Too many shots couldn't be returned: a player would tap the ball softly, run after it and hit it
again at full speed by the Middle Wall, and it reached the other end in half a second at over
2,000 px/s.  With the Speed Cap on (a Match setting, under Ball & Paddles), a paddle knocks the
ball as if moving no faster than engines.CAP_DRIVE times the serve's speed, and gives way rather
than catching its own ball again.  Classic physics never hands on a paddle's speed at all.

tests/charge_shot.py plays the shot every way (where it meets the paddle, how the soft ball was
going, the attacker running straight or up or down too), and asks whether a defender in the
middle of their goal, reacting 0.2 s late, could get to it.
"""
import math
import unittest

from tests import harness

app = harness.app()

from game import engines                                        # noqa: E402
from tests import charge_shot                                   # noqa: E402
from tests.test_physics_engines import Court, face              # noqa: E402

m = app.settings.match


def worst(physics, cap):
    m.reset()
    m.physics, m.speed_cap = physics, cap
    try:
        return charge_shot.worst(app)
    finally:
        m.reset()


class ChargeShot(unittest.TestCase):
    def test_out_of_reach_without_the_cap(self):
        """The problem, as Rowan found it (so the check below would see it).  (Since 1.9's slower ball,
        v0.9's worst charge shot is just within reach without the cap; Current's still isn't.)"""
        for physics in (engines.CURRENT,):
            short, seconds, speed, shot = worst(physics, False)
            with self.subTest(physics = m.PHYSICS[physics]):
                self.assertGreater(short, 0, f"reachable after all: {seconds:.2f} s, {speed:.0f} px/s, {shot}")

    def test_within_reach_with_the_cap(self):
        for physics in (engines.CURRENT, engines.V09):
            short, seconds, speed, shot = worst(physics, True)
            with self.subTest(physics = m.PHYSICS[physics]):
                self.assertLess(short, -150, f"{seconds:.2f} s, {speed:.0f} px/s, {shot}")

    def test_within_reach_with_classic_physics(self):
        short, seconds, speed, shot = worst(engines.CLASSIC, False)
        self.assertLess(short, -150, f"{seconds:.2f} s, {speed:.0f} px/s, {shot}")


class Knocks(unittest.TestCase):
    def tearDown(self):
        self.court.close()

    def drive(self, physics, cap, paddle_speed):
        self.court = Court(physics, cap)
        p1 = self.court.game.p1
        rect, normal = face(p1, 0.0)
        return math.hypot(*self.court.hit(p1, rect, normal, (-700.0, 0.0), (paddle_speed, 0.0)))

    def test_a_drive_counts_only_up_to_the_cap(self):
        limit = engines.cap_drive(500)
        capped = self.drive(engines.CURRENT, True, 2000.0)
        self.court.close()
        at_limit = self.drive(engines.CURRENT, False, limit / engines.push_pace(False))   # (uncapped, a push counts at the ball's pace: 1.9)
        self.assertAlmostEqual(capped, at_limit, delta = 1)
        self.court.close()
        self.assertGreater(self.drive(engines.CURRENT, False, 2000.0), capped + 300, "and without it, harder")

    def test_slower_drives_are_untouched(self):
        under = engines.cap_drive(500) * 0.8
        capped = self.drive(engines.V09, True, under)
        self.court.close()
        # (1.9: without the cap a push counts at the ball's pace, engines.push_pace; under it, in full)
        self.assertAlmostEqual(capped, self.drive(engines.V09, False, under / engines.push_pace(False)), delta = 0.01)

    def test_no_difference_to_classic(self):
        capped = self.drive(engines.CLASSIC, True, 1500.0)
        self.court.close()
        self.assertAlmostEqual(capped, self.drive(engines.CLASSIC, False, 1500.0), delta = 0.01)

    def test_the_paddle_gives_way(self):
        """Capped, a paddle charging on after its hit doesn't catch the ball and knock it again."""
        from game.physics import Physics
        for physics in (engines.CURRENT, engines.V09):
            with self.subTest(physics = m.PHYSICS[physics]):
                self.court = Court(physics, True)
                game, p1 = self.court.game, self.court.game.p1
                game.objects.remove(game.p2)                # (so only p1 could touch it)
                rect, normal = face(p1, 0.5)
                self.court.hit(p1, rect, normal, (-200.0, 0.0), (1500.0, 0.0))
                hits = game.ball.rally_value
                app.keys_down = {p1.right}
                try:
                    for _ in range(60):
                        Physics.step(game, 1 / 60)
                finally:
                    app.keys_down = set()
                self.assertEqual(game.ball.rally_value, hits)
                self.assertIs(game.ball.last_paddle, p1)
                self.assertLess(p1.x1, game.ball.x0)
                self.court.close()
        self.court = Court(engines.CURRENT)


if __name__ == "__main__":
    unittest.main()

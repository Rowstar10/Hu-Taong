"""Power-up balance changes in 1.6 (batch 2 of the power-up plan, from the 1.4 power-up reviews).

- Safety Teleport: an unused charge ends with the point (it could be saved up all match).
- Swift Step: the paddle moves 1.5x as fast, but its drives hit no harder than a normal paddle's
  (a faster paddle hit much harder, which was most of its edge: the taker won 74% at Hard).
- Spirit Fire: blazing shots go at most 10% past the usual top speed (they reached about 4,450 px/s).
- Frostbite: one-way.  Your next hit frosts the ball; whoever hits it back is frozen at half speed
  for 5 s, whatever they hit; it never comes back to you, and the ball keeps its speed.
- Ghost Ball: always in sight in the last 300 px before the paddle it's heading for.
- Blink Ball: no hops within 350 px of the paddle it's heading for.
- Twin Balls: never split slower than half a serve.
- Wind Gust: gusts up to 500 px/s^2 (360 was too gentle to notice).
- Firecracker: the bang shoots away from whoever lit it, never back at them.
"""
import math
import unittest

from tests import harness

app = harness.app()

from config import MAX_BALL_SPEEDUP           # noqa: E402  (after the harness has set things up)
from game.physics import Physics               # noqa: E402
from game.powerups import BY_KEY, PowerUps     # noqa: E402
from tests.test_powerup_fixes import Match, place, centre   # noqa: E402


class Teleport(Match):
    def test_unused_charge_ends_with_the_point(self):
        self.p1.charges["teleport"] = 1
        self.pu.on_point()
        self.assertNotIn("teleport", self.p1.charges)

    def test_tooltip_says_so(self):
        self.assertIn("point ends", BY_KEY["teleport"].about)


class Hits(Match):
    def hit(self, paddle, drive, bvx, effects = ()):
        """The right-hand paddle driving into a ball coming at bvx, at `drive` times its own top
        speed: the ball's speed after."""
        game, ball = self.game, self.ball
        paddle.effects = {key: 10.0 for key in effects}
        game.apply_gameplay_settings()
        place(paddle, 1500, 540)
        place(ball, paddle.x0 - ball.width / 2, 540)
        ball.vx, ball.vy, paddle.vx, paddle.vy = bvx, 0.0, -paddle.speed * drive, 0.0
        Physics.resolve_collision(paddle, ball, {"t": 0.0, "normal": (1, 0)})
        return math.hypot(ball.vx, ball.vy)

    def test_swift_drives_no_harder(self):
        normal = self.hit(self.p2, 1.0, 800.0)
        swift = self.hit(self.p2, 1.0, 800.0, ("swift",))        # driving at 1.5x the speed
        # it must still leave faster than the paddle chasing it, but no harder than that needs
        self.assertLessEqual(swift, max(normal, self.p2.speed + 150) * 1.02,
                             f"normal {normal:.0f}, swift {swift:.0f}")

    def test_swift_at_normal_speed_hits_as_usual(self):
        normal = self.hit(self.p2, 0.8, 800.0)
        swift = self.hit(self.p2, 0.8 / PowerUps.SWIFT, 800.0, ("swift",))
        self.assertAlmostEqual(swift, normal, delta = 1)

    def test_swift_still_moves_half_as_fast_again(self):
        self.p2.effects = {}
        self.game.apply_gameplay_settings()
        base = self.p2.speed
        self.p2.effects = {"swift": 10.0}
        self.game.apply_gameplay_settings()
        self.assertAlmostEqual(self.p2.speed, base * PowerUps.SWIFT)

    def test_fire_capped_just_past_the_top_speed(self):
        cap = MAX_BALL_SPEEDUP * self.ball.speed * math.sqrt(2)
        fast = self.hit(self.p2, 1.0, 3200.0, ("fire",))         # a smash into a fast ball
        self.assertLessEqual(fast, cap * PowerUps.FIRE_TOP + 1)
        self.assertGreater(fast, cap)                                # still past the usual top speed

    def test_fire_still_speeds_up_an_ordinary_shot(self):
        plain = self.hit(self.p2, 0.0, 900.0)
        fire = self.hit(self.p2, 0.0, 900.0, ("fire",))
        self.assertAlmostEqual(fire / plain, PowerUps.FIRE, delta = 0.01)


class Frostbite(Match):
    def setUp(self):
        super().setUp()
        self.pu.collect({"kind": "frost", "x": 900, "y": 500}, self.p1)
        self.ball.vx, self.ball.vy = 900.0, 300.0

    def test_one_way(self):
        pu, p1, p2, ball = self.pu, self.p1, self.p2, self.ball
        pu.on_hit(ball, p1, (1, 0))                      # Red's hit frosts the ball...
        self.assertTrue(pu.ball_frosted())
        self.assertEqual((ball.vx, ball.vy), (900.0, 300.0), "the frosted ball slowed")
        pu.on_hit(ball, p2, (-1, 0))                     # ...Blue hits it back and is frozen
        self.assertTrue(pu.frozen(p2))
        self.assertAlmostEqual(pu.frost["left"], PowerUps.FROST_TIME)
        pu.on_hit(ball, p2, (-1, 0))                     # Blue hitting again doesn't pass it on
        self.assertTrue(pu.frozen(p2))
        pu.on_hit(ball, p1, (1, 0))
        self.assertFalse(pu.frozen(p1), "the frost came back to Red")
        self.assertTrue(pu.frozen(p2))

    def test_frozen_for_five_seconds(self):
        pu, p1, p2, ball = self.pu, self.p1, self.p2, self.ball
        pu.on_hit(ball, p1, (1, 0))
        pu.on_hit(ball, p2, (-1, 0))
        for _ in range(int(4.9 * 120)):
            pu.update(1 / 120)
        self.assertTrue(pu.frozen(p2))
        for _ in range(int(0.2 * 120)):
            pu.update(1 / 120)
        self.assertFalse(pu.frozen(p2))

    def test_tooltip(self):
        about = BY_KEY["frost"].about
        self.assertIn("5 s", about)
        self.assertIn("never comes back to you", about)


class GhostNearPaddle(Match):
    def hidden_ghost_at(self, gap):
        pu, ball, p2 = self.pu, self.ball, self.p2
        pu.ghost = {"left": 10.0, "hidden": True, "alpha": 0.0, "next": 5.0}
        place(ball, p2.x0 - gap - ball.width / 2, 540)
        ball.vx, ball.vy = 1000.0, 0.0
        for _ in range(int(0.2 * 120)):               # (it fades back in over 0.15 s)
            pu.update_ghost(1 / 120)
        return pu.ghost["alpha"]

    def test_in_sight_close_to_the_paddle_its_heading_for(self):
        self.assertEqual(self.hidden_ghost_at(250), 1.0)

    def test_still_hides_mid_court(self):
        self.assertEqual(self.hidden_ghost_at(900), 0.0)


class BlinkNearPaddle(Match):
    def hops_from(self, gap):
        pu, ball, p2 = self.pu, self.ball, self.p2
        pu.blink = {"left": 10.0, "next": 5.0}
        landed = []
        for _ in range(60):
            place(ball, p2.x0 - gap - ball.width / 2, 540)
            ball.vx, ball.vy = 1000.0, 0.0
            before = centre(ball)
            pu.hop()
            if centre(ball) != before:
                landed.append(p2.x0 - ball.x1)
        return landed

    def test_no_hop_close_to_the_paddle(self):
        self.assertEqual(self.hops_from(250), [])

    def test_hops_never_land_close_to_the_paddle(self):
        landed = self.hops_from(420)
        self.assertTrue(all(gap >= PowerUps.BLINK_CLEAR for gap in landed), landed)

    def test_still_hops_mid_court(self):
        self.assertTrue(self.hops_from(900))


class TwinSplit(Match):
    def test_never_slower_than_half_a_serve(self):
        ball = self.ball
        place(ball, 960, 540)
        ball.vx, ball.vy = 200.0, 100.0
        self.pu.split_ball()
        half_serve = ball.speed * math.sqrt(2) / 2
        for b in self.pu.balls():
            self.assertGreaterEqual(math.hypot(b.vx, b.vy), half_serve - 1)


class Wind(Match):
    def test_gust_strength(self):
        self.pu.wind = {"left": 5.0, "dir": 1, "t": math.pi / 2 / 2.3}    # the height of a gust
        self.assertAlmostEqual(self.pu.wind_force(), 500.0, delta = 1)


class Firecracker(Match):
    def bang_ways(self, lighter):
        pu, ball = self.pu, self.ball
        ways = set()
        for _ in range(40):
            place(ball, 960, 540)
            pu.cracker = {"hits": 1, "fuse": None}
            pu.on_hit(ball, lighter, (1, 0) if lighter.is_left else (-1, 0))
            ball.vx, ball.vy = (-900.0 if lighter.is_left else 900.0), 0.0    # coming back at the lighter
            pu.update_cracker(1.0)
            ways.add(1 if ball.vx > 0 else -1)
        return ways

    def test_bangs_away_from_whoever_lit_it(self):
        self.assertEqual(self.bang_ways(self.p1), {1})
        self.assertEqual(self.bang_ways(self.p2), {-1})

    def test_tooltip(self):
        self.assertNotIn("either way", BY_KEY["cracker"].about)


class Tooltips(unittest.TestCase):
    def test_ghost_and_blink_mention_the_paddle_rule(self):
        self.assertIn("nears a paddle", BY_KEY["ghost"].about)
        self.assertIn("close to a paddle", BY_KEY["blink"].about)


if __name__ == "__main__":
    unittest.main()

"""The flagged talismans' balance review, 1.8 (Rowan's 1.8 plan, phase 2, 2026-11-18).

Rowan's choices from the options offered:
- Spirit Fire: blazing shots are 20% faster (40% until now) and never go past the usual top speed
  (they could go 10% past it).  A blazing shot is never slower than the same hit without it.
- Shrink Curse: the opponent's paddle shrinks by a fifth (a third until now).
- Sticky Goo: the aim locks half a second before the ball is slung, so carrying it to the middle
  and faking at the last moment no longer changes where it goes.  The arrow holds steady once it's
  locked, and the lock reaches replays and the friend's screen online (the same rows).
"""
import math
import unittest

from tests import harness

app = harness.app()

from config import MAX_BALL_SPEEDUP                         # noqa: E402  (after the harness has set things up)
from game.physics import Physics                            # noqa: E402
from game.powerups import BY_KEY, PowerUps                  # noqa: E402
from game.replay import ReplayView                          # noqa: E402
from tests.test_powerup_fixes import Match, place           # noqa: E402

DT = 1 / 60


class SpiritFire(Match):
    def hit(self, bvx, effects = (), drive = 1.0):
        """Blue's paddle driving into a ball coming at bvx: the ball's speed after."""
        game, ball, paddle = self.game, self.ball, self.p2
        paddle.effects = {key: 10.0 for key in effects}
        game.apply_gameplay_settings()
        place(paddle, 1500, 540)
        place(ball, paddle.x0 - ball.width / 2, 540)
        ball.vx, ball.vy, paddle.vx, paddle.vy = bvx, 0.0, -paddle.speed * drive, 0.0
        Physics.resolve_collision(paddle, ball, {"t": 0.0, "normal": (1, 0)})
        return math.hypot(ball.vx, ball.vy)

    def top(self):
        return MAX_BALL_SPEEDUP * self.ball.speed * math.sqrt(2)

    def test_a_fifth_faster(self):
        self.assertEqual(PowerUps.FIRE, 1.2)
        plain, fire = self.hit(900.0, drive = 0.0), self.hit(900.0, ("fire",), drive = 0.0)
        self.assertAlmostEqual(fire / plain, 1.2, delta = 0.01)

    def test_never_past_the_usual_top_speed(self):
        self.assertLessEqual(self.hit(3200.0, ("fire",)), self.top() + 1)

    def test_never_slower_than_without_it(self):
        for coming in (900.0, 3200.0, 5000.0):
            self.assertGreaterEqual(self.hit(coming, ("fire",)), self.hit(coming) - 1)

    def test_says_so(self):
        self.assertIn("20% faster", BY_KEY["fire"].blurb)
        self.assertIn("up to the usual top speed", BY_KEY["fire"].about)


class ShrinkCurse(Match):
    def test_a_fifth_smaller(self):
        normal = self.p2.height
        self.pu.collect({"kind": "shrink", "x": 900, "y": 500}, self.p1)
        self.game.apply_gameplay_settings()
        self.assertAlmostEqual(self.p2.height, normal * 0.8, delta = 1)
        self.assertIn("by a fifth", BY_KEY["shrink"].blurb)


class StickyGoo(Match):
    def catch(self, hold = 1.0):
        """Red catches the ball on its gooey paddle, to be held for `hold` seconds."""
        p1, ball, pu = self.p1, self.ball, self.pu
        p1.effects["sticky"] = 10.0
        place(p1, 400, 540)
        place(ball, p1.x1 + ball.width / 2 + 2, 540)
        ball.vx, ball.vy = 800.0, 0.0
        pu.stick(ball, p1)
        ball.stuck["left"] = ball.stuck["total"] = hold
        return ball.stuck

    def hold(self, seconds, vy):
        """Red's paddle moving at vy while it holds the ball, for `seconds`."""
        self.p1.vx, self.p1.vy = 0.0, vy
        for _ in range(round(seconds / DT)):
            if not self.ball.stuck:
                break
            self.pu.update_sticky(DT)

    def test_the_aim_follows_the_paddle_until_half_a_second_before(self):
        stuck = self.catch(1.0)
        up, down = -self.p1.speed, self.p1.speed
        self.hold(0.3, down)                                    # aiming down at first...
        self.assertNotIn("aim", stuck)
        self.hold(0.15, up)                                     # ...then up, before it locks
        self.assertNotIn("aim", stuck)
        self.hold(0.1, up)
        self.assertIn("aim", stuck, "locked half a second before it goes")
        self.assertLess(stuck["aim"], 0)
        self.hold(0.6, down)                                    # the last-moment fake
        self.assertIsNone(self.ball.stuck)
        self.assertLess(self.ball.vy, 0, "it still went up")

    def test_knocked_loose_early_it_goes_where_it_was_aimed(self):
        stuck = self.catch(1.0)
        self.hold(0.1, -self.p1.speed)
        stuck["left"] = 0.0                                     # (carried into a stone, say)
        self.pu.update_sticky(DT)
        self.assertLess(self.ball.vy, 0)

    def test_the_ai_reads_the_locked_aim(self):
        stuck = self.catch(1.0)
        self.hold(0.55, -self.p1.speed)                         # locked going up
        self.p1.vx, self.p1.vy = 0.0, self.p1.speed             # then a fake down
        self.p2.ai.reset()
        _x, _y, _vx, vy = self.p2.ai.perceive(self.ball, 1 / 120, 0.0)
        self.assertLess(vy, 0, "not fooled")
        self.assertIn("aim", stuck)

    def test_the_lock_shows_in_replays_and_online(self):
        stuck = self.catch(1.0)
        rec = self.game.recorder
        self.hold(0.2, -self.p1.speed)
        rec.capture(DT)                                         # not locked yet
        self.hold(0.35, -self.p1.speed)
        rec.capture(DT)                                         # locked
        view = ReplayView(rec.clip(), app)
        view.show(len(view.clip.frames) - 2)
        self.assertNotIn("aim", view.ball.stuck)
        view.show(len(view.clip.frames) - 1)
        self.assertAlmostEqual(view.ball.stuck["aim"], stuck["aim"], places = 4)
        self.p1.vy = self.p1.speed                              # (the arrow follows the lock, not the paddle)
        self.assertAlmostEqual(PowerUps.sling_angle(view.p1, view.ball.stuck), stuck["aim"], places = 4)
        app.dt = DT
        app.renderer.draw_world(app.virtual, view)
        app.renderer.draw_world(app.virtual, self.game)

    def test_says_so(self):
        self.assertIn("locks half a second before", BY_KEY["sticky"].about)


if __name__ == "__main__":
    unittest.main()

"""Three physics options, 1.8 (Rowan's 1.8 plan, 2026-11-17).

Match settings > Ball & Paddles > Physics says how a ball comes off a paddle:
- Current, 1.7's engine, unchanged (the rest of the tests hold it to that).
- Classic: the angle comes from where the ball meets the paddle, every hit of a rally is a step
  faster up to the usual top speed, and the paddle's movement adds nothing.
- v0.9: Hu Taong 0.9's, which Rowan likes the feel of.  Checked against what 0.9's own code did
  with 2,448 hits (tests/data/v09_hits.json, made by tests/data/make_v09_hits.py), apart from what
  was added so a point can't freeze: a floor on its speed, and never quite straight up or down.
"""
import json
import math
import os
import random
import unittest

from tests import harness

app = harness.app()

from game import engines                                        # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.physics import Physics                                # noqa: E402
from game.powerups import PowerUps                              # noqa: E402

m = app.settings.match
SERVE = 500


def recorded():
    with open(os.path.join(harness.GAME, "tests", "data", "v09_hits.json"), encoding = "utf-8") as f:
        return json.load(f)


class Court:
    """A match to play single hits in, the ball and paddles laid out as a hit needs."""

    def __init__(self, physics, speed_cap = False):
        m.reset()
        m.physics, m.speed_cap = physics, speed_cap
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.game.powerups.wait = 999.0

    def place(self, obj, x0, y0, x1, y1):
        obj.x0, obj.y0, obj.x1, obj.y1 = x0, y0, x1, y1
        obj.width, obj.height = x1 - x0, y1 - y0

    def hit(self, paddle, ball_rect, normal, ball_v, paddle_v, paddle_rect = None):
        """One knock of the paddle into the ball (the paddle first, as the game plays them)."""
        ball = self.game.ball
        if paddle_rect:
            self.place(paddle, *paddle_rect)
        self.place(ball, *ball_rect)
        ball.diameter = ball.width
        ball.speed = SERVE
        ball.vx, ball.vy = ball_v
        paddle.vx, paddle.vy = paddle_v
        ball.press, ball.stuck = None, None
        paddle.held = paddle.trail = None
        Physics.resolve_collision(paddle, ball, {"t": 0.0, "normal": normal})
        return ball.vx, ball.vy

    def close(self):
        self.game.stop()
        m.reset()


def face(paddle, at, ball = 60):
    """A ball touching the paddle's face at `at` half-heights from its middle, and the normal."""
    cy = (paddle.y0 + paddle.y1) / 2 + at * paddle.height / 2
    if paddle.is_left:
        return (paddle.x1, cy - ball / 2, paddle.x1 + ball, cy + ball / 2), (-1, 0)
    return (paddle.x0 - ball, cy - ball / 2, paddle.x0, cy + ball / 2), (1, 0)


class V09(unittest.TestCase):
    def setUp(self):
        self.court = Court(engines.V09)

    def tearDown(self):
        self.court.close()

    def test_as_0_9_played_them(self):
        data = recorded()
        pw, ph = data["paddle"]
        size, cy = data["ball"], data["cy"]
        floor = engines.v09_floor(SERVE)
        checked = guarded = 0
        for side, kind, at, bvx, bvy, pvx, pvy, ovx, ovy in data["hits"]:
            paddle = (self.court.game.p1, self.court.game.p2)[side]
            cx = data["centres"][side]
            prect = (cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2)
            if kind == "face":
                by = cy + at * ph / 2
                bx0 = prect[2] if side == 0 else prect[0] - size
                brect, normal = (bx0, by - size / 2, bx0 + size, by + size / 2), ((-1, 0) if side == 0 else (1, 0))
            else:
                bx = cx + at * pw / 2
                by0 = prect[1] - size if kind == "above" else prect[3]
                brect, normal = (bx - size / 2, by0, bx + size / 2, by0 + size), ((0, 1) if kind == "above" else (0, -1))
            # (1.9: a paddle's push counts at the ball's pace, engines.push_pace: 0.9's paddle at (pvx, pvy)
            # is one going 1 / BALL_PACE as fast now)
            k = engines.push_pace(False)
            vx, vy = self.court.hit(paddle, brect, normal, (bvx, bvy), (pvx / k, pvy / k), prect)
            speed, want = math.hypot(vx, vy), math.hypot(ovx, ovy)
            with self.subTest(hit = [side, kind, at, bvx, bvy, pvx, pvy]):
                self.assertAlmostEqual(speed, max(want, floor), delta = 0.5, msg = "its speed")
                if kind != "face" and abs(ovx) < engines.V09_UPRIGHT * want:
                    # 0.9 sent it (nearly) straight up or down: now it keeps a little sideways
                    guarded += 1
                    self.assertAlmostEqual(abs(vx), engines.V09_UPRIGHT * speed, delta = 0.5)
                    self.assertEqual(math.copysign(1, vy), math.copysign(1, ovy) if ovy else -normal[1])
                    continue
                checked += 1
                self.assertAlmostEqual(math.atan2(vy, vx), math.atan2(ovy, ovx), delta = 1e-3, msg = "its way out")
        self.assertGreater(checked, 2000)
        self.assertLess(guarded, 300)

    def test_a_still_paddle_slows_it_and_a_drive_speeds_it_up(self):
        p1 = self.court.game.p1
        rect, normal = face(p1, 0.0)
        still = math.hypot(*self.court.hit(p1, rect, normal, (-800.0, 0.0), (0.0, 0.0)))
        drive = math.hypot(*self.court.hit(p1, rect, normal, (-800.0, 0.0), (1500.0, 0.0)))
        self.assertLess(still, 800 * 0.5)
        self.assertGreater(drive, 2400 * engines.push_pace(False))      # (the push at the ball's pace: 1.9)

    def test_no_top_speed(self):
        p1 = self.court.game.p1
        rect, normal = face(p1, 0.0)
        speed = math.hypot(*self.court.hit(p1, rect, normal, (-3000.0, 0.0), (2000.0, 0.0)))
        self.assertGreater(speed, MAX_TOP() * 1.1)


def MAX_TOP():
    from config import MAX_BALL_SPEEDUP
    return MAX_BALL_SPEEDUP * engines.serve_speed(SERVE)


class Classic(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.court = Court(engines.CLASSIC)
        self.p1, self.p2 = self.court.game.p1, self.court.game.p2

    def tearDown(self):
        self.court.close()

    def rally(self, hits, paddle_v = (0.0, 0.0)):
        """Hit the ball back and forth `hits` times; the speed after each."""
        speeds = []
        for i in range(hits):
            paddle = (self.p1, self.p2)[i % 2]
            rect, normal = face(paddle, 0.3)
            pv = (paddle_v[0] * (1 if paddle.is_left else -1), paddle_v[1])
            speeds.append(math.hypot(*self.court.hit(paddle, rect, normal, (normal[0] * 900.0, 0.0), pv)))
        return speeds

    def test_a_step_faster_every_hit_up_to_the_top_speed(self):
        start = engines.serve_speed(SERVE)
        speeds = self.rally(80)
        for n, speed in enumerate(speeds[:5], 1):
            self.assertAlmostEqual(speed, start * (1 + engines.CLASSIC_STEP * n), delta = 0.01)
        self.assertAlmostEqual(speeds[-1], MAX_TOP(), delta = 0.01)
        self.assertTrue(all(b >= a for a, b in zip(speeds, speeds[1:])))

    def test_the_paddles_movement_adds_nothing(self):
        still = self.rally(4)
        self.court.game.ball.rally_value, self.court.game.ball.last_paddle = 0, None
        driving = self.rally(4, paddle_v = (1500.0, 1500.0))
        for a, b in zip(still, driving):
            self.assertAlmostEqual(a, b, delta = 0.01)

    def test_the_angle_from_where_it_met_the_paddle(self):
        angles = []
        for at in (-1.0, -0.5, 0.5, 1.0):
            rect, normal = face(self.p1, at)
            vx, vy = self.court.hit(self.p1, rect, normal, (-900.0, 0.0), (0.0, 0.0))
            angles.append(math.degrees(math.atan2(vy, vx)))
        for got, want in zip(angles, (-60, -30, 30, 60)):
            self.assertAlmostEqual(got, want, delta = 0.01)

    def test_a_charging_paddle_cant_catch_its_own_ball(self):
        """It gives way: running on after the hit, it never catches up and knocks the ball again."""
        game = self.court.game
        rect, normal = face(self.p1, 0.0)
        self.court.hit(self.p1, rect, normal, (-200.0, 0.0), (1500.0, 0.0))
        game.ball.last_paddle = self.p1
        speed = math.hypot(game.ball.vx, game.ball.vy)
        app.keys_down = {self.p1.right}
        try:
            for _ in range(60):
                Physics.step(game, 1 / 60)
                self.assertLess(self.p1.x1, game.ball.x0, "the paddle caught it")
        finally:
            app.keys_down = set()
        self.assertLessEqual(math.hypot(game.ball.vx, game.ball.vy), speed, "and it wasn't knocked again")

    def test_spirit_fire_doesnt_stack(self):
        """A fired hit is faster (20% since 1.8's review); the next hit is back to the rally's speed."""
        self.p1.effects["fire"] = 30.0
        speeds = self.rally(3)
        start = engines.serve_speed(SERVE)
        self.assertAlmostEqual(speeds[0], start * (1 + engines.CLASSIC_STEP) * PowerUps.FIRE, delta = 1)
        self.assertAlmostEqual(speeds[1], start * (1 + 2 * engines.CLASSIC_STEP), delta = 1)


class Settings(unittest.TestCase):
    def tearDown(self):
        m.reset()

    def test_current_and_no_cap_by_default(self):
        m.reset()
        self.assertEqual((m.physics, m.speed_cap), (engines.CURRENT, False))
        self.assertEqual(m.PHYSICS, ("Current", "Classic", "v0.9"))

    def test_saved(self):
        from core import save_data
        m.physics, m.speed_cap = engines.V09, True
        save_data.save(app)
        m.reset()
        save_data.load(app)
        self.assertEqual((m.physics, m.speed_cap), (engines.V09, True))

    def test_a_1_7_save_plays_as_before(self):
        from core import save_data
        data = save_data.collect(app)
        for name in ("physics", "speed_cap"):
            del data["gameplay"][name]
        save_data.save_path().parent.mkdir(parents = True, exist_ok = True)
        save_data.save_path().write_text(json.dumps(data))
        m.physics, m.speed_cap = engines.CLASSIC, True
        m.reset()
        save_data.load(app)
        self.assertEqual((m.physics, m.speed_cap), (engines.CURRENT, False))

    def test_from_the_next_serve(self):
        court = Court(engines.CURRENT)
        try:
            m.physics = engines.CLASSIC
            self.assertEqual(court.game.settings.physics, engines.CURRENT, "not mid-rally")
            court.game.reset_round()
            self.assertEqual(court.game.settings.physics, engines.CLASSIC)
        finally:
            court.close()


if __name__ == "__main__":
    unittest.main()

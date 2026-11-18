"""Black Hole, a new talisman, 1.8 (Rowan's 1.8 plan, phase 2, 2026-11-18).

A black hole opens mid-court until the point ends.  It pulls the balls (never the paddles), harder
the closer they come and the faster they go, bending their paths but keeping their speed.  A ball
that touches its black heart falls in: it's held there, out of sight, while an arrow flares the way
it will come out, then it's flung out that way as fast as it went in (never slower than a serve,
never steeper than a portal sends a ball).  A ball circling in its pull too long is drawn in.  At
the point's end it implodes.  The AI judges its pull, the friend's screen online flies the ball
through it as the host's game does, and replays show it.
"""
import math
import random
import unittest
from types import SimpleNamespace

from tests import harness

app = harness.app()

from config import BASE_W, BASE_H                               # noqa: E402
from core.states.guest_state import GuestMatchState             # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import BY_KEY, PowerUps                      # noqa: E402
from game.replay import ReplayView                              # noqa: E402
from render.hud import SHORT                                    # noqa: E402
from tests.test_warm_art import Counting                        # noqa: E402

m = app.settings.match
DT = 1 / 120


class Match(unittest.TestCase):
    COURT = 0

    def setUp(self):
        random.seed(5)
        m.reset()
        m.court = self.COURT
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.pu = self.game.powerups
        self.pu.wait = 999.0
        self.ball = self.game.ball
        self.game.p1.ai_enabled = self.game.p2.ai_enabled = False

    def tearDown(self):
        self.game.stop()
        m.reset()

    def hole_at(self, x = 960.0, y = 540.0):
        """A black hole, wide open, at (x, y)."""
        hole = {"x": x, "y": y, "kind": PowerUps.HOLE_TALISMAN, "age": 5.0, "power": 1.0, "spin": 1,
                "way": None, "flash": 0.0, "dying": None}
        self.pu.holes = [hole]
        return hole

    def place(self, x, y, vx, vy, ball = None):
        ball = ball or self.ball
        r = ball.width / 2
        ball.x0, ball.y0, ball.x1, ball.y1 = x - r, y - r, x + r, y + r
        ball.vx, ball.vy = vx, vy

    def fly(self, seconds, ball = None, dt = DT):
        """The ball flown on under the holes' pull (as Physics.step would move it)."""
        ball = ball or self.ball
        seen = []
        for _ in range(round(seconds / dt)):
            self.pu.update_portals(dt)
            self.pu.update_holes(dt)
            if not ball.transit:
                ball.x0 += ball.vx * dt
                ball.x1 += ball.vx * dt
                ball.y0 += ball.vy * dt
                ball.y1 += ball.vy * dt
            seen.append((bool(ball.transit), math.hypot(ball.vx, ball.vy), self.pu.ball_alpha(ball)))
        return seen

    def centre(self, ball = None):
        ball = ball or self.ball
        return (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2


class Opening(Match):
    COURT = 2                                                   # Graveyard: four stones

    def test_opens_mid_court_clear_of_the_stones_and_the_ball(self):
        stones = [o for o in self.game.objects if getattr(o, "is_obstacle", False)]
        self.assertTrue(stones)
        for i in range(30):
            self.pu.holes = []
            self.place(random.uniform(200, BASE_W - 200), random.uniform(100, BASE_H - 100), 0.0, 0.0)
            self.pu.collect({"kind": "hole", "x": 900, "y": 500}, self.game.p1)
            hole = self.pu.holes[0]
            with self.subTest(i = i):
                self.assertTrue(BASE_W * 0.32 <= hole["x"] <= BASE_W * 0.68)
                bx, by = self.centre()
                self.assertGreater(math.hypot(hole["x"] - bx, hole["y"] - by), 300)
                for o in stones:
                    gap = math.hypot(hole["x"] - min(max(hole["x"], o.x0), o.x1), hole["y"] - min(max(hole["y"], o.y0), o.y1))
                    self.assertGreater(gap, 100)

    def test_one_at_a_time_counted_and_listed(self):
        self.pu.collect({"kind": "hole", "x": 900, "y": 500}, self.game.p1)
        self.assertFalse(self.pu.spawnable(BY_KEY["hole"]))
        self.assertEqual(self.pu.in_play(), 1)
        self.assertIn("hole", [key for key, _, _ in self.pu.court_list()])

    def test_opens_over_a_moment(self):
        self.pu.collect({"kind": "hole", "x": 900, "y": 500}, self.game.p1)
        hole = self.pu.holes[0]
        self.assertEqual(hole["power"], 0.0)
        self.fly(PowerUps.HOLE_OPEN / 2)
        self.assertTrue(0.3 < hole["power"] < 0.7)
        self.fly(PowerUps.HOLE_OPEN)
        self.assertEqual(hole["power"], 1.0)

    def test_portals_keep_clear_of_it(self):
        self.pu.open_portals(PowerUps.PORTAL_START_TALISMAN)
        door = self.pu.portals[0]
        hole = self.hole_at(door["x"] + 260, door["y"])
        door["vx"], door["vy"] = 50.0, 0.0                      # drifting straight at it
        for _ in range(60):
            self.pu.drift_portals(1 / 60)
        self.assertLess(door["vx"], 0, "turned away")


class Pull(Match):
    def test_bends_the_path_and_keeps_the_speed(self):
        self.hole_at(960, 540)
        self.place(560, 700, 900.0, 0.0)                         # passing below it
        seen = self.fly(0.5)
        self.assertLess(self.ball.vy, -50, "pulled up towards it")
        self.assertTrue(all(abs(speed - 900) < 1 for inside, speed, _ in seen if not inside))

    def test_harder_closer_in_and_on_faster_balls(self):
        hole = self.hole_at(960, 540)
        near = math.hypot(*PowerUps.hole_pull(hole, 960, 540 + 100))
        far = math.hypot(*PowerUps.hole_pull(hole, 960, 540 + 300))
        self.assertGreater(near, far * 4)
        fast = math.hypot(*PowerUps.hole_pull(hole, 960, 540 + 100, pace = 2.0))
        self.assertAlmostEqual(fast, near * 2)
        self.assertEqual(PowerUps.hole_pull(hole, 960, 540 + PowerUps.HOLE_REACH + 1), (0.0, 0.0), "nothing past its reach")

    def test_paddles_feel_nothing(self):
        self.hole_at(960, 540)
        p1 = self.game.p1
        p1.x0, p1.x1 = 900, 900 + p1.width
        p1.vx = p1.vy = 0.0
        self.place(200, 100, 0.0, 0.0)
        self.pu.update_holes(DT)
        self.assertEqual((p1.vx, p1.vy), (0.0, 0.0))

    def test_both_twin_balls(self):
        self.hole_at(960, 540)
        self.pu.split_ball()
        blue = self.pu.twin["ball"]
        self.place(560, 700, 900.0, 0.0)
        self.place(560, 380, 900.0, 0.0, blue)
        for _ in range(30):
            self.pu.update_holes(DT)
        self.assertLess(self.ball.vy, 0)
        self.assertGreater(blue.vy, 0)


class Swallowed(Match):
    def test_falls_in_and_is_flung_out_the_way_the_arrow_flares(self):
        hole = self.hole_at(960, 540)
        self.place(600, 540, 1200.0, 0.0)
        seen = self.fly(0.25)
        self.assertTrue(self.ball.transit, "fell in")
        self.assertEqual(self.pu.ball_alpha(), 0.0, "out of sight inside")
        self.assertEqual(hole["flash"] > 0.5, True)
        way = hole["way"]
        self.assertGreaterEqual(abs(math.cos(way)), PowerUps.PORTAL_STEEPEST - 1e-6, "never straight up or down")
        self.assertFalse(self.ball.can_collide_with(self.game.p1))
        inside = 0
        while self.ball.transit:
            self.fly(DT)
            inside += 1
        self.assertAlmostEqual(inside * DT, PowerUps.HOLE_HOLD, delta = 2 * DT)
        self.assertAlmostEqual(math.hypot(self.ball.vx, self.ball.vy), 1200.0, delta = 1, msg = "as fast as it went in")
        self.assertAlmostEqual(math.atan2(self.ball.vy, self.ball.vx), way, places = 4)
        # flung clear: not pulled straight back
        heading = math.atan2(self.ball.vy, self.ball.vx)
        self.fly(PowerUps.HOLE_COOL * 0.9)
        self.assertAlmostEqual(math.atan2(self.ball.vy, self.ball.vx), heading, places = 4)

    def test_never_flung_slower_than_a_serve(self):
        self.hole_at(960, 540)
        self.place(900, 540, 150.0, 0.0)
        self.fly(1.0)
        self.assertGreaterEqual(math.hypot(self.ball.vx, self.ball.vy), self.ball.speed * math.sqrt(2) - 1)

    def test_a_fast_ball_cant_skip_across_its_heart(self):
        self.hole_at(960, 540)
        self.place(930, 540 + PowerUps.HOLE_CORE + 5, 4000.0, 0.0)  # (a frame takes it right across)
        self.pu.update_holes(1 / 30)
        self.assertTrue(self.ball.transit)

    def test_circling_too_long_its_drawn_in(self):
        self.hole_at(960, 540)
        self.place(960, 540 + 250, 700.0, 0.0)
        self.ball.hole_time = PowerUps.HOLE_TRAP
        self.pu.update_holes(DT)
        self.assertTrue(self.ball.transit)


class PointsEnd(Match):
    def test_implodes_at_the_points_end(self):
        hole = self.hole_at()
        self.pu.on_point()
        self.assertIsNotNone(hole["dying"])
        self.assertEqual(self.pu.pulling(), [])
        self.assertNotIn("hole", [key for key, _, _ in self.pu.court_list()])
        self.place(700, 560, 900.0, 0.0)
        self.pu.update_holes(DT)
        self.assertEqual(self.ball.vy, 0.0, "no pull as it implodes")
        for _ in range(round(PowerUps.HOLE_IMPLODE / DT) + 2):
            self.pu.update_popups(DT)                           # (it plays out while the point is announced)
        self.assertEqual(self.pu.holes, [])

    def test_none_at_the_serve(self):
        self.hole_at()
        self.pu.serve_portals()
        self.assertEqual(self.pu.holes, [])


class TheAI(Match):
    def target(self, ball_y, vy = 0.0):
        p2 = self.game.p2
        ai = p2.ai
        ai.reset()
        ai.noise, ai.aim = 0.0, 0.0
        k = ai.params()
        r = self.ball.width / 2
        return ai.meet(700.0, ball_y, 1000.0, vy, r, k)

    def test_reads_the_bent_path(self):
        hole = self.hole_at(1100, 540)
        straight_y = 540 + 170
        _line, y = self.target(straight_y)
        ai = self.game.p2.ai
        contact_x = _line - (self.game.p2.width / 2 + self.ball.width / 2)
        path = self.pu.hole_path(700.0, straight_y, 1000.0, 0.0, self.ball.width / 2, contact_x)
        self.assertIsNotNone(path)
        self.assertLess(abs(y - path[1]), abs(y - straight_y), "nearer the bent path than the straight one")
        self.assertLess(path[1], straight_y - 30)

    def test_waits_in_the_middle_when_it_will_fall_in(self):
        self.hole_at(1100, 540)
        _line, y = self.target(540)
        self.assertEqual(y, BASE_H / 2)

    def test_reads_a_swallowed_ball_from_the_flare(self):
        self.hole_at(960, 540)
        self.place(600, 540, 1200.0, 0.0)
        self.fly(0.35)
        self.assertTrue(self.ball.transit)
        want = self.pu.transit_exit(self.ball)
        ai = self.game.p2.ai
        ai.reset()
        x, y, vx, vy = ai.perceive(self.ball, 1 / 120, 0.0)
        self.assertAlmostEqual(vx, want[2], delta = 1)
        self.assertAlmostEqual(vy, want[3], delta = 1)


class FriendsScreen(Match):
    def guest(self, holes):
        guest = GuestMatchState.__new__(GuestMatchState)
        guest.serve_speed = self.ball.speed
        guest.view = SimpleNamespace(
            stones = [], settings = SimpleNamespace(pace = 1.0), ball = SimpleNamespace(curve = 0.0),
            powerups = SimpleNamespace(alpha = 1.0, ghostly = lambda: False, wind = 0.0, portals = [], holes = holes))
        return guest

    def test_flies_it_through_the_pull_as_the_host_does(self):
        hole = self.hole_at(960, 540)
        self.place(560, 700, 900.0, 0.0)
        r = self.ball.width / 2
        x, y, vx, vy = self.guest([dict(hole)]).fly(560.0, 700.0, 900.0, 0.0, r, 0.4)
        self.fly(0.4)
        hx, hy = self.centre()
        self.assertLess(math.hypot(x - hx, y - hy), 6)
        self.assertLess(math.hypot(vx - self.ball.vx, vy - self.ball.vy), 20)

    def test_holds_a_swallowed_ball_at_the_heart(self):
        hole = self.hole_at(960, 540)
        x, y, vx, vy = self.guest([dict(hole)]).fly(700.0, 540.0, 1200.0, 0.0, self.ball.width / 2, 0.4)
        self.assertEqual((x, y, vx, vy), (960, 540, 0.0, 0.0), "where it comes out is the host's call")

    def test_no_pull_just_after_a_fling(self):
        hole = self.hole_at(960, 540)
        hole["flash"] = 0.5
        x, y, vx, vy = self.guest([dict(hole)]).fly(1000.0, 540.0 + 80, 900.0, 0.0, self.ball.width / 2, 0.2)
        self.assertEqual(vy, 0.0)


class Replays(Match):
    def test_rows_carry_it_through_opening_flaring_and_imploding(self):
        rec = self.game.recorder
        self.pu.collect({"kind": "hole", "x": 900, "y": 500}, self.game.p1)
        hole = self.pu.holes[0]
        self.fly(0.3)
        rec.capture(1 / 60)                                         # opening
        hole["age"], hole["power"] = 5.0, 1.0
        hole["way"], hole["flash"] = 0.4, 0.8
        rec.capture(1 / 60)                                         # flaring
        self.pu.on_point()
        rec.capture(1 / 60)                                         # imploding
        view = ReplayView(rec.clip(), app)
        frames = len(view.clip.frames)
        app.dt = DT
        for i, check in ((frames - 3, lambda h: 0 < h["power"] < 1),
                         (frames - 2, lambda h: abs(h["way"] - 0.4) < 1e-4 and abs(h["flash"] - 0.8) < 1e-4),
                         (frames - 1, lambda h: h["dying"] is not None)):
            view.show(i)
            self.assertEqual(len(view.powerups.holes), 1)
            seen = view.powerups.holes[0]
            self.assertAlmostEqual(seen["x"], hole["x"], places = 2)
            self.assertEqual(seen["kind"], PowerUps.HOLE_TALISMAN)
            self.assertTrue(check(seen), i)
            app.renderer.draw_world(app.virtual, view)


class Described(unittest.TestCase):
    def test_the_full_set_of_words(self):
        kind = BY_KEY["hole"]
        self.assertEqual((kind.name, kind.family, kind.seconds), ("Black Hole", "Wild", 0))
        self.assertIn("pulls the ball", kind.blurb)
        self.assertIn("flung out", kind.about)
        self.assertIn("hole", SHORT)

    def test_its_art_is_built_ahead(self):
        powerups = SimpleNamespace(holes = [
            {"x": 960, "y": 540, "kind": PowerUps.HOLE_TALISMAN, "age": age, "power": 1.0, "spin": 1,
             "way": 0.3, "flash": flash, "dying": dying}
            for age in (0.1, 0.3, 0.5, 5.0) for flash in (0.0, 0.3, 1.0) for dying in (None, 0.6, 0.4, 0.1)])
        app.dt = DT
        with Counting() as c:
            app.renderer.draw_holes(app.virtual, powerups, 0, 0)
        self.assertEqual(c.built, [])


if __name__ == "__main__":
    unittest.main()

"""Portal Pair's collapse, 1.8 (Rowan's 1.8 plan, phase 2, 2026-11-18).

For the talisman and the game mode alike: once the portals are full size, the next ball through
comes out as usual, and then they collapse.  Over 2.5 s they flare, spiral in round each other and
merge into a black hole between them, its pull growing as they do.  It keeps two arrows, red and
blue, the ways the portals pointed, slowly circling.  It stays until it swallows a ball or the point
is won.  A lone ball it swallows comes out as Twin Balls (Twin Balls' rules), red along the red
arrow and blue along the blue; with two balls in play already, the ball comes out alone along its
own.  Then the hole implodes, and mini black holes come and go until the point is won: a new one
every 1.5-3 s, up to three, each 3-5 s with fades, standing still, weaker and smaller, and each a
portal too, shooting a ball out along its own circling arrow.  In a Portal Pair match, small portals
open again at the next serve.

Rowan's playtest (same day): "All black holes, I want to have a gravitational pull": Portal Pair's
and the mini ones pull as the Black Hole does (see test_black_hole), the minis more weakly.
"""
import math
import random
import unittest
from types import SimpleNamespace

from tests import harness

app = harness.app()

from config import BASE_W                                       # noqa: E402
from core.states.guest_state import GuestMatchState             # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import BY_KEY, PowerUps                      # noqa: E402
from game.replay import ReplayView                              # noqa: E402
from tests.test_warm_art import Counting                        # noqa: E402

m = app.settings.match
DT = 1 / 120
P = PowerUps


class Match(unittest.TestCase):
    MODE = False

    def setUp(self):
        random.seed(11)
        m.reset()
        m.mode_portal_pair = self.MODE
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.pu = self.game.powerups
        self.pu.wait = 999.0
        self.ball = self.game.ball
        self.game.p1.ai_enabled = self.game.p2.ai_enabled = False
        if not self.MODE:
            self.place(100, 540, 0.0, 0.0)
            self.pu.open_portals(P.PORTAL_START_TALISMAN)

    def tearDown(self):
        self.game.stop()
        m.reset()

    def place(self, x, y, vx, vy, ball = None):
        ball = ball or self.ball
        r = ball.width / 2
        ball.x0, ball.y0, ball.x1, ball.y1 = x - r, y - r, x + r, y + r
        ball.vx, ball.vy = vx, vy

    def centre(self, ball = None):
        ball = ball or self.ball
        return (ball.x0 + ball.x1) / 2, (ball.y0 + ball.y1) / 2

    def through(self, door = 0):
        """The ball sent through a portal, and out of the other."""
        d = self.pu.portals[door]
        self.place(d["x"], d["y"], 700.0, 0.0)
        self.ball.portal_cool = 0.0
        self.pu.portal_trips = 0
        self.pu.update_portals(DT)
        while self.ball.transit:
            self.pu.update_portals(DT)

    def full_size(self):
        for p in self.pu.portals:
            p["r"] = float(P.PORTAL_R)

    def play(self, seconds, dt = DT, balls = None):
        for _ in range(round(seconds / dt)):
            self.pu.update_portals(dt)
            self.pu.update_holes(dt)
            self.pu.update_minis(dt)
            for b in balls or self.pu.balls():
                if not b.transit:
                    b.x0 += b.vx * dt
                    b.x1 += b.vx * dt
                    b.y0 += b.vy * dt
                    b.y1 += b.vy * dt

    def collapse(self):
        """Full-size portals, the next ball through, and the collapse over: the black hole."""
        self.full_size()
        a, b = (dict(p) for p in self.pu.portals)
        self.through()
        hole = self.pu.holes[0]
        hole["age"] = P.COLLAPSE_TIME
        hole["power"] = 1.0
        return hole, a, b

    def collapse_hole(self):
        return next(h for h in self.pu.holes if h["kind"] == P.HOLE_COLLAPSE)


class Collapsing(Match):
    def test_not_before_full_size(self):
        self.through()
        self.assertEqual(len(self.pu.portals), 2)
        self.assertEqual(self.pu.holes, [])

    def test_at_full_size_the_next_ball_through_comes_out_then_they_collapse(self):
        self.full_size()
        a, b = (dict(p) for p in self.pu.portals)
        self.through()
        x, y = self.centre()
        self.assertLess(math.hypot(x - b["x"], y - b["y"]), b["r"] + self.ball.width, "out as usual")
        self.assertEqual(self.pu.portals, [])
        self.assertEqual(len(self.pu.holes), 1)
        hole = self.pu.holes[0]
        self.assertEqual(hole["kind"], P.HOLE_COLLAPSE)
        self.assertAlmostEqual(hole["x"], (a["x"] + b["x"]) / 2, delta = 20)    # (they drift a little meanwhile)
        self.assertEqual(len(hole["arrows"]), 2)
        for angle, door in zip(hole["arrows"], (a, b)):
            dx, dy = P.portal_exit(door["angle"])
            self.assertAlmostEqual(angle, math.atan2(dy, dx), delta = 0.1, msg = "the ways the portals pointed")

    def test_its_pull_grows_as_it_collapses_and_it_swallows_nothing_till_formed(self):
        self.full_size()
        self.through()
        hole = self.pu.holes[0]
        self.place(hole["x"] - 300, hole["y"], 0.0, 0.0)
        self.play(P.COLLAPSE_TIME * 0.4, balls = [])
        self.assertTrue(0.3 < hole["power"] < 0.5)
        arrows = list(hole["arrows"])
        self.place(hole["x"] - 100, hole["y"], 900.0, 0.0)          # straight through its heart
        self.play(0.25)
        self.assertIsNone(self.ball.transit)
        self.assertEqual(hole["arrows"], arrows, "they don't circle yet")
        self.play(P.COLLAPSE_TIME, balls = [])
        self.assertEqual(hole["power"], 1.0)
        self.assertNotEqual(hole["arrows"], arrows, "now they slowly circle")

    def test_stays_until_it_swallows_a_ball(self):
        hole, _, _ = self.collapse()
        self.place(200, 200, 0.0, 0.0)
        self.play(6.0, balls = [])
        self.assertIn(hole, self.pu.holes)
        self.assertIsNone(hole["dying"])

    def test_a_lone_ball_comes_out_as_twin_balls_along_the_arrows(self):
        hole, _, _ = self.collapse()
        hole["turns"] = [0.0, 0.0]
        red_way, blue_way = (math.atan2(*reversed(P.portal_exit(a))) for a in hole["arrows"])
        speed = 1400.0
        self.place(hole["x"] - 200, hole["y"], speed, 0.0)
        self.play(0.3, balls = [self.ball])
        self.assertTrue(self.ball.transit, "swallowed")
        self.play(P.HOLE_HOLD + 0.05, balls = [])
        self.assertIsNotNone(self.pu.twin, "Twin Balls")
        blue = self.pu.twin["ball"]
        self.assertEqual((self.ball.side, blue.side), ("red", "blue"))
        self.assertIn(blue, self.game.objects)
        self.assertAlmostEqual(math.atan2(self.ball.vy, self.ball.vx), red_way, places = 4)
        self.assertAlmostEqual(math.atan2(blue.vy, blue.vx), blue_way, places = 4)
        half = max(speed * 0.5, self.ball.speed * math.sqrt(2) * 0.5)
        for b in (self.ball, blue):
            self.assertAlmostEqual(math.hypot(b.vx, b.vy), half, delta = 1, msg = "as Twin Balls split")
        self.assertIsNotNone(hole["dying"], "then it implodes")
        self.assertTrue(self.pu.minis)

    def test_with_two_balls_in_play_the_ball_comes_out_alone(self):
        hole, _, _ = self.collapse()
        hole["turns"] = [0.0, 0.0]
        self.pu.split_ball()
        blue = self.pu.twin["ball"]
        self.place(200, 150, 0.0, 0.0)
        self.place(hole["x"] - 200, hole["y"], 1000.0, 0.0, blue)
        self.play(0.3, balls = [blue])
        self.assertTrue(blue.transit)
        self.play(P.HOLE_HOLD + 0.05, balls = [])
        self.assertEqual(len([o for o in self.game.objects if o.is_ball]), 2, "no third ball")
        blue_way = math.atan2(*reversed(P.portal_exit(hole["arrows"][1])))
        self.assertAlmostEqual(math.atan2(blue.vy, blue.vx), blue_way, places = 4, msg = "along the blue arrow")
        self.assertAlmostEqual(math.hypot(blue.vx, blue.vy), 1000.0, delta = 1)

    def test_the_points_end(self):
        hole, _, _ = self.collapse()
        self.pu.minis = {"next": 1.0}
        self.pu.on_point()
        self.assertIsNotNone(hole["dying"])
        self.assertIsNone(self.pu.minis)
        self.pu.serve_portals()
        self.assertEqual(self.pu.holes, [])
        self.assertEqual(self.pu.portals, [], "the talisman's are gone")

    def test_counted_once_and_listed(self):
        self.collapse()
        self.assertEqual(self.pu.in_play(), 1)
        self.assertFalse(self.pu.spawnable(BY_KEY["portal"]))
        self.assertIn("portal", [key for key, _, _ in self.pu.court_list()])

    def test_its_black_hole_has_gravity(self):
        hole, _, _ = self.collapse()
        serve = self.ball.speed * math.sqrt(2)
        self.place(hole["x"] - 400, hole["y"] + 150, serve, 0.0)
        fell = False
        for _ in range(240):
            self.play(DT, balls = [self.ball])
            fell = fell or bool(self.ball.transit)
        self.assertTrue(fell, "drawn in from 150 px off")

    def test_said_so(self):
        self.assertIn("collapsing into a black hole", BY_KEY["portal"].about)
        self.assertIn("mini black holes", BY_KEY["portal"].about)


class InAPortalPairMatch(Match):
    MODE = True

    def test_small_portals_open_again_at_the_next_serve(self):
        self.assertEqual(len(self.pu.portals), 2)
        self.place(100, 540, 0.0, 0.0)
        self.collapse()
        self.assertEqual(self.pu.portals, [])
        self.pu.on_point()
        self.pu.serve_portals()
        self.assertEqual([p["r"] for p in self.pu.portals], [float(P.PORTAL_START)] * 2)
        self.assertEqual(self.pu.in_play(), 0, "a game mode doesn't count")


class MiniHoles(Match):
    def start(self):
        hole, _, _ = self.collapse()
        self.pu.holes.remove(hole)
        self.pu.minis = {"next": 0.0}
        self.place(150, 150, 0.0, 0.0)

    def minis(self):
        return [h for h in self.pu.holes if h["kind"] == P.HOLE_MINI]

    def test_come_and_go_up_to_three_until_the_point_ends(self):
        self.start()
        opened, most = [], 0
        real = self.pu.open_mini
        self.pu.open_mini = lambda: (opened.append(1), real())
        for _ in range(40):
            self.play(0.5, balls = [])
            live = self.minis()
            most = max(most, len(live))
            for h in live:
                self.assertTrue(P.MINI_GOAL_GAP <= h["x"] <= BASE_W - P.MINI_GOAL_GAP)
        self.assertLessEqual(most, P.MINI_MOST)
        self.assertGreater(len(opened), 5, "new ones keep coming")
        self.pu.on_point()
        self.assertIsNone(self.pu.minis)

    def test_each_fades_in_lasts_three_to_five_seconds_and_fades_out(self):
        self.start()
        self.play(DT, balls = [])
        h = self.minis()[0]
        self.pu.minis["next"] = 999.0
        self.assertTrue(P.MINI_LIFE[0] - DT <= h["left"] <= P.MINI_LIFE[1])
        x, y = h["x"], h["y"]
        powers = []
        while h in self.pu.holes:
            self.play(1 / 30, balls = [])
            powers.append(h["power"])
        self.assertEqual((h["x"], h["y"]), (x, y), "standing still")
        self.assertTrue(any(0.2 < p < 0.8 for p in powers[:20]), "fading in")
        self.assertTrue(any(0.2 < p < 0.8 for p in powers[-20:]), "fading out")

    def test_they_have_gravity_too(self):
        self.start()
        self.play(DT, balls = [])
        h = self.minis()[0]
        self.pu.minis["next"] = 999.0
        h["age"], h["left"], h["power"] = 2.0, 4.0, 1.0
        serve = self.ball.speed * math.sqrt(2)
        self.place(h["x"] - 240, h["y"] + 70, serve, 0.0)
        fell = False
        for _ in range(180):
            self.play(DT, balls = [self.ball])
            fell = fell or bool(self.ball.transit)
        self.assertTrue(fell, "drawn in from 70 px off")

    def test_weaker_and_smaller(self):
        self.assertLess(P.MINI_PULL, P.HOLE_PULL / 2)
        self.assertLess(P.MINI_REACH, P.HOLE_REACH / 1.5)
        self.assertLess(P.MINI_CORE, P.HOLE_CORE)

    def test_a_mini_portal_out_along_its_arrow_a_little_slower(self):
        self.start()
        self.play(DT, balls = [])
        h = self.minis()[0]
        self.pu.minis["next"] = 999.0
        h["age"], h["left"], h["power"] = 2.0, 3.0, 1.0
        h["turn"] = 0.4
        speed = 1500.0
        self.place(h["x"] - 150, h["y"], speed, 0.0)
        for _ in range(60):
            self.play(DT, balls = [self.ball])
            if self.ball.transit:
                break
        self.assertTrue(self.ball.transit, "in")
        arrow = h["arrows"][0]
        self.assertGreater(h["flash"], 0.5, "its arrow flashes")
        self.play(P.MINI_HOLD * 0.5, balls = [])
        self.assertEqual(h["arrows"][0], arrow, "and holds still while the ball's inside")
        self.play(P.MINI_HOLD, balls = [])
        self.assertIsNone(self.ball.transit)
        dx, dy = P.portal_exit(arrow)
        self.assertAlmostEqual(math.atan2(self.ball.vy, self.ball.vx), math.atan2(dy, dx), places = 4)
        self.assertAlmostEqual(math.hypot(self.ball.vx, self.ball.vy), speed * (1 - P.PORTAL_SLOW), delta = 1)


class FriendsScreenAndReplays(Match):
    def guest(self, holes):
        guest = GuestMatchState.__new__(GuestMatchState)
        guest.serve_speed = self.ball.speed
        guest.view = SimpleNamespace(
            stones = [], settings = SimpleNamespace(pace = 1.0), ball = SimpleNamespace(curve = 0.0),
            powerups = SimpleNamespace(alpha = 1.0, ghostly = lambda: False, wind = 0.0, portals = [], holes = holes))
        return guest

    def test_the_friends_screen_lets_it_through_the_heart_till_its_formed(self):
        self.full_size()
        self.through()
        hole = dict(self.pu.holes[0], age = 1.0, power = 0.4)
        x, y, vx, vy = self.guest([hole]).fly(hole["x"] - 200, hole["y"], 1000.0, 0.0, self.ball.width / 2, 0.4)
        self.assertGreater(x, hole["x"] + 100)
        hole.update(age = 3.0, power = 1.0)
        x, y, vx, vy = self.guest([hole]).fly(hole["x"] - 200, hole["y"], 1000.0, 0.0, self.ball.width / 2, 0.4)
        self.assertEqual((x, y, vx, vy), (hole["x"], hole["y"], 0.0, 0.0))

    def test_replays_show_the_collapse_the_twin_arrows_and_the_minis(self):
        rec = self.game.recorder
        self.full_size()
        self.through()
        hole = self.pu.holes[0]
        app.dt = DT
        stages = []
        for age in (0.3, 1.2, 2.2, 3.0):
            hole["age"] = age
            rec.capture(1 / 60)
            stages.append(age)
        self.pu.minis = {"next": 0.0}
        self.place(150, 150, 0.0, 0.0)
        self.pu.update_minis(DT)
        rec.capture(1 / 60)
        view = ReplayView(rec.clip(), app)
        n = len(view.clip.frames)
        for i, age in enumerate(stages):
            view.show(n - 5 + i)
            seen = view.powerups.holes[0]
            self.assertAlmostEqual(seen["age"], age, places = 4)
            self.assertEqual(len(seen["arrows"]), 2)
            for (dx, dy), door in zip(seen["doors"], hole["doors"]):
                self.assertAlmostEqual(dx, door[0], places = 2)
            app.renderer.draw_world(app.virtual, view)
        view.show(n - 1)
        self.assertIn(P.HOLE_MINI, [h["kind"] for h in view.powerups.holes])
        app.renderer.draw_world(app.virtual, view)

    def test_its_art_is_built_ahead(self):
        doors = [(-260.0, -60.0), (260.0, 60.0)]
        holes = [{"x": 960, "y": 540, "kind": P.HOLE_COLLAPSE, "age": age, "power": 1.0, "spin": 1, "way": None,
                  "flash": flash, "dying": None, "arrows": [0.3, 2.6], "doors": doors}
                 for age in [i * 0.05 for i in range(70)] for flash in (0.0, 0.5, 0.95)]
        holes += [{"x": 700, "y": 400, "kind": P.HOLE_MINI, "age": 1.0, "power": power, "spin": 1, "way": None,
                   "flash": flash, "dying": dying, "arrows": [1.0]}
                  for power in (0.1, 0.4, 0.7, 1.0) for flash in (0.0, 0.6) for dying in (None, 0.5, 0.1)]
        holes += [dict(holes[0], dying = d) for d in (0.6, 0.3, 0.05)]
        app.dt = DT
        with Counting() as c:
            app.renderer.draw_holes(app.virtual, SimpleNamespace(holes = holes), 0, 0)
        self.assertEqual(c.built, [])


class TheAI(Match):
    def test_reads_a_ball_inside_a_mini_from_its_arrow(self):
        hole, _, _ = self.collapse()
        self.pu.holes.remove(hole)
        self.pu.minis = {"next": 0.0}
        self.place(150, 150, 0.0, 0.0)
        self.pu.update_minis(DT)
        h = self.pu.holes[0]
        self.pu.minis["next"] = 999.0
        h["age"], h["power"] = 2.0, 1.0
        self.place(h["x"] - 120, h["y"], 1500.0, 0.0)
        self.play(0.15, balls = [self.ball])
        self.assertTrue(self.ball.transit)
        want = self.pu.transit_exit(self.ball)
        ai = self.game.p2.ai
        ai.reset()
        _x, _y, vx, vy = ai.perceive(self.ball, 1 / 120, 0.0)
        self.assertAlmostEqual(vx, want[2], delta = 1)
        self.assertAlmostEqual(vy, want[3], delta = 1)

    def test_a_forming_holes_heart_doesnt_stop_its_reckoning(self):
        self.full_size()
        self.through()
        hole = self.pu.holes[0]
        hole["age"], hole["power"] = 1.0, 0.4
        path = self.pu.hole_path(hole["x"] - 300, hole["y"], 1200.0, 0.0, self.ball.width / 2, hole["x"] + 500)
        self.assertIsNotNone(path)
        self.assertFalse(path[2], "it can't swallow yet")


if __name__ == "__main__":
    unittest.main()

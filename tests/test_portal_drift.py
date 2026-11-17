"""Portal Pair reworked, 1.7 (Rowan's 1.7 plan, 2026-11-17).

The two portals now drift slowly about mid-court (clear of the paddles' ends and of any stone, and
apart from each other), their arrows slowly turn, and they open small and grow a little each time
a ball goes through, up to a full size.  A ball never leaves steeper than before, even as the
arrows turn through straight up or down.  Replays and the friend's screen show the same, and the
friend's screen flies the ball through them by the same rule.

Rowan's playtest (same day): a Portal Pair game mode too, its portals open all match and growing
all match (never shrinking back between points); and the talisman's, which only last the point,
open bigger (but not too big).

Found in the full test run (same day): on a court with stones, the talisman sometimes opened no
portals at all (about one time in eight on the Graveyard with the ball by a goal), because the first
portal's spot was picked before the second's and could leave nowhere far enough from it.
"""
import math
import random
import unittest
from types import SimpleNamespace

from tests import harness

app = harness.app()

from config import BASE_H, BASE_W                               # noqa: E402
from core.states.guest_state import GuestMatchState             # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import BY_KEY, PowerUps                      # noqa: E402
from game.replay import ReplayView                              # noqa: E402

m = app.settings.match
DT = 1 / 60


class Portals(unittest.TestCase):
    COURT = 2                                                     # Graveyard: four stones

    def setUp(self):
        random.seed(17)
        m.reset()
        m.court = self.COURT
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.pu = self.game.powerups
        self.pu.wait = 999.0
        ball = self.game.ball
        ball.x0, ball.x1 = 100, 100 + ball.width                  # (well away from where they open)
        self.pu.open_portals(PowerUps.PORTAL_START_TALISMAN)
        self.assertEqual(len(self.pu.portals), 2)

    def tearDown(self):
        self.game.stop()
        m.reset()

    def drift(self, seconds):
        seen = []
        for _ in range(int(seconds / DT)):
            self.pu.drift_portals(DT)
            seen.append([dict(p) for p in self.pu.portals])
        return seen

    def test_the_talismans_open_not_so_small(self):
        self.pu.portals = []
        self.pu.collect({"kind": "portal", "x": 900, "y": 500}, self.game.p1)
        for door in self.pu.portals:
            self.assertEqual(door["r"], PowerUps.PORTAL_START_TALISMAN)
        self.assertLess(PowerUps.PORTAL_START, PowerUps.PORTAL_START_TALISMAN)
        self.assertLess(PowerUps.PORTAL_START_TALISMAN, PowerUps.PORTAL_R, "but not full size")

    def test_the_talismans_close_with_the_point(self):
        self.pu.on_point()
        self.assertEqual(self.pu.portals, [])

    def test_they_drift_and_turn(self):
        """How far each goes, not where it ends up: one can bounce off an edge and come back."""
        frames = [[dict(p) for p in self.pu.portals]] + self.drift(5.0)
        for i in range(2):
            path = sum(math.hypot(b[i]["x"] - a[i]["x"], b[i]["y"] - a[i]["y"]) for a, b in zip(frames, frames[1:]))
            self.assertGreater(path, PowerUps.PORTAL_DRIFT[0] * 5 * 0.9, "it didn't drift (or stuck)")
            turned = abs((frames[-1][i]["angle"] - frames[0][i]["angle"] + math.pi) % math.tau - math.pi)
            self.assertGreater(turned, 0.8, "its arrows didn't turn")

    def test_slowly(self):
        frames = self.drift(2.0)
        for before, after in zip(frames, frames[1:]):
            for a, b in zip(before, after):
                self.assertLessEqual(math.hypot(b["x"] - a["x"], b["y"] - a["y"]), PowerUps.PORTAL_DRIFT[1] * DT + 1e-6)
                turned = abs((b["angle"] - a["angle"] + math.pi) % math.tau - math.pi)
                self.assertLessEqual(turned, PowerUps.PORTAL_TURN[1] * DT + 1e-6)

    def test_they_keep_to_mid_court_clear_of_stones_and_apart(self):
        lo, hi, edge = PowerUps.PORTAL_AREA
        stones = [o for o in self.game.objects if getattr(o, "is_obstacle", False)]
        self.assertTrue(stones)
        closest = math.inf
        for frame in self.drift(60.0):
            for door in frame:
                self.assertTrue(BASE_W * lo - 1 <= door["x"] <= BASE_W * hi + 1)
                self.assertTrue(edge - 1 <= door["y"] <= BASE_H - edge + 1)
                for o in stones:
                    inside = o.x0 - door["r"] < door["x"] < o.x1 + door["r"] and o.y0 - door["r"] < door["y"] < o.y1 + door["r"]
                    self.assertFalse(inside, "a portal drifted onto a stone")
            a, b = frame
            closest = min(closest, math.hypot(b["x"] - a["x"], b["y"] - a["y"]))
        self.assertGreater(closest, 300, "the two drifted into each other")

    def go_through(self, door):
        ball = self.game.ball
        ball.x0, ball.y0 = door["x"] - ball.width / 2, door["y"] - ball.height / 2
        ball.x1, ball.y1 = ball.x0 + ball.width, ball.y0 + ball.height
        ball.vx, ball.vy, ball.portal_cool = 600.0, 0.0, 0.0
        self.pu.portal_trips = 0
        self.pu.update_portals(DT)

    def test_each_ball_through_grows_both_to_their_full_size(self):
        sizes = []
        for _ in range(10):
            self.go_through(self.pu.portals[0])
            sizes.append([p["r"] for p in self.pu.portals])
        self.assertEqual(sizes[0], [PowerUps.PORTAL_START_TALISMAN + PowerUps.PORTAL_GROW] * 2)
        self.assertEqual(sizes[-1], [PowerUps.PORTAL_R] * 2)
        self.assertTrue(all(b >= a for (a, _), (b, _) in zip(sizes, sizes[1:])))

    def test_never_out_steeper_than_before(self):
        self.pu.portals[1]["angle"] = math.pi / 2                 # its arrows point straight down just now
        self.pu.portals[1]["spin"] = 0.0
        self.go_through(self.pu.portals[0])
        ball = self.game.ball
        speed = math.hypot(ball.vx, ball.vy)
        self.assertAlmostEqual(speed, 600, delta = 1)
        self.assertGreaterEqual(abs(ball.vx) / speed, PowerUps.PORTAL_STEEPEST - 1e-6)
        self.assertGreater(ball.vy, 0, "still down, as far as it may")

    def test_says_so(self):
        about = BY_KEY["portal"].about
        self.assertIn("drifting", about)
        self.assertIn("grow", about)
        self.assertIn("turn", about)

    def test_replays_and_the_friends_screen_show_them(self):
        self.go_through(self.pu.portals[0])
        self.drift(1.0)
        for _ in range(3):
            self.game.recorder.capture(1 / 60)
        view = ReplayView(self.game.recorder.clip(), app)
        view.show(len(view.clip.frames) - 1)
        self.assertEqual(len(view.powerups.portals), 2)
        for shown, real in zip(view.powerups.portals, self.pu.portals):
            for key in ("x", "y", "angle", "r"):
                self.assertAlmostEqual(shown[key], real[key], delta = 0.01)

    def test_1_6_replays_had_no_size(self):
        view = ReplayView(SimpleNamespace(info = {}, frames = [], events = [], moments = []), app)
        self.assertEqual(view.portal_fields, 3)
        for _ in range(2):
            self.game.recorder.capture(1 / 60)
        self.assertEqual(ReplayView(self.game.recorder.clip(), app).portal_fields, 4)


class PortalPairMode(unittest.TestCase):
    """The mode: the talisman's portals, open all match, growing all match."""

    def setUp(self):
        random.seed(23)
        m.reset()
        m.mode_portal_pair = True
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.pu = self.game.powerups
        self.pu.wait = 999.0

    def tearDown(self):
        self.game.stop()
        m.reset()

    def next_point(self):
        g = self.game
        g.on_score(g.ball, {"normal": (1, 0)})
        g.message_timer = 0.001
        g.update(0.01)

    def grow(self, times):
        ball = self.game.ball
        for _ in range(times):
            door = self.pu.portals[0]
            ball.x0, ball.y0 = door["x"] - ball.width / 2, door["y"] - ball.height / 2
            ball.x1, ball.y1 = ball.x0 + ball.width, ball.y0 + ball.height
            ball.vx, ball.vy, ball.portal_cool = 600.0, 0.0, 0.0
            self.pu.portal_trips = 0
            self.pu.update_portals(1 / 60)

    def test_open_from_the_first_serve_small(self):
        self.assertEqual(len(self.pu.portals), 2)
        self.assertEqual([p["r"] for p in self.pu.portals], [PowerUps.PORTAL_START] * 2)

    def test_they_last_the_match_and_keep_their_size(self):
        self.grow(2)
        size = self.pu.portals[0]["r"]
        self.assertGreater(size, PowerUps.PORTAL_START)
        for _ in range(3):
            self.next_point()
            self.assertEqual(len(self.pu.portals), 2, "closed at the end of a point")
            self.assertEqual(self.pu.portals[0]["r"], size, "shrank back between points")

    def test_still_no_bigger_than_full_size(self):
        self.grow(4)
        self.next_point()
        self.grow(10)
        self.assertEqual([p["r"] for p in self.pu.portals], [PowerUps.PORTAL_R] * 2)

    def test_a_loop_shuts_them_till_the_next_serve_as_big_as_they_were(self):
        self.grow(3)
        size = self.pu.portals[0]["r"]
        self.pu.close_portals()
        self.assertEqual(self.pu.portals, [])
        self.next_point()
        self.assertEqual([p["r"] for p in self.pu.portals], [size] * 2)

    def test_no_portal_pair_talisman(self):
        self.assertFalse(self.pu.spawnable(BY_KEY["portal"]))
        self.assertIn("in a Portal Pair match", BY_KEY["portal"].about)

    def test_switched_off_mid_match_they_go_at_the_next_serve(self):
        m.mode_portal_pair = False
        self.next_point()
        self.assertEqual(self.pu.portals, [])

    def test_saved_and_on_match_setup(self):
        from core import save_data
        self.assertIn("mode_portal_pair", save_data.collect(app)["gameplay"])
        self.assertIn("portal_pair", app.renderer.MODE_TIPS)


class FriendsScreen(unittest.TestCase):
    """The friend's screen flies the ball through the portals as the host's game does: by each
    one's size, and out no steeper than the host lets it."""

    def flown(self, at_y, r = 48.0, out_angle = 0.0):
        guest = GuestMatchState.__new__(GuestMatchState)
        guest.view = SimpleNamespace(
            stones = [], settings = SimpleNamespace(pace = 1.0), ball = SimpleNamespace(curve = 0.0),
            powerups = SimpleNamespace(alpha = 1.0, ghostly = lambda: False, wind = 0.0,
                                       portals = [{"x": 700.0, "y": 540.0, "angle": 0.0, "r": r},
                                                  {"x": 1300.0, "y": 300.0, "angle": out_angle, "r": r}]))
        return guest.fly(500.0, at_y, 1000.0, 0.0, 20.0, 0.4)

    def test_a_small_portal_is_missed_wide_of_it(self):
        x, y, vx, vy = self.flown(at_y = 540 + 0.6 * 48 + 8)      # inside a full-size portal, outside this one
        self.assertAlmostEqual(vy, 0.0)
        self.assertGreater(x, 800)

    def test_through_the_middle_and_out_the_other(self):
        x, y, vx, vy = self.flown(at_y = 540, out_angle = math.pi / 2)
        speed = math.hypot(vx, vy)
        self.assertGreaterEqual(abs(vx) / speed, PowerUps.PORTAL_STEEPEST - 1e-6)
        self.assertGreater(y, 300)


class AlwaysOpen(unittest.TestCase):
    """Every court, every size they open at, the ball anywhere along the middle: two portals, well
    apart, clear of the stones and the ball."""

    def test_two_every_time(self):
        for court in range(5):
            random.seed(court)
            m.reset()
            m.court = court
            game = Hu_Taong(app)
            game.start()
            pu, ball = game.powerups, game.ball
            stones = [o for o in game.objects if getattr(o, "is_obstacle", False)]
            try:
                for start in (PowerUps.PORTAL_START, PowerUps.PORTAL_START_TALISMAN, PowerUps.PORTAL_R):
                    room = pu.portal_room(start)
                    for i in range(150):
                        x = (100, 960, 1800)[i % 3]
                        ball.x0, ball.x1 = x, x + ball.width
                        pu.portals = []
                        pu.open_portals(start)
                        with self.subTest(court = court, start = start, try_ = i):
                            self.assertEqual(len(pu.portals), 2, "no portals opened")
                            a, b = pu.portals
                            self.assertGreaterEqual(math.hypot(a["x"] - b["x"], a["y"] - b["y"]), 520)
                            for door in pu.portals:
                                for o in stones:
                                    self.assertFalse(o.x0 - room < door["x"] < o.x1 + room
                                                     and o.y0 - room < door["y"] < o.y1 + room, "on a stone")
            finally:
                game.stop()
                m.reset()


class BuiltAhead(unittest.TestCase):
    def test_every_size_they_grow_through(self):
        for job in app.renderer.prewarm_jobs():
            job()
        for R in range(PowerUps.PORTAL_START, PowerUps.PORTAL_R + 1, PowerUps.PORTAL_GROW):
            self.assertIn(("portal_ring", R), app.art.cache)


if __name__ == "__main__":
    unittest.main()

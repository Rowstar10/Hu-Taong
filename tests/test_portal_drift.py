"""Portal Pair reworked, 1.7 (Rowan's 1.7 plan, 2026-11-17).

The two portals now drift slowly about mid-court (clear of the paddles' ends and of any stone, and
apart from each other), their arrows slowly turn, and they open small and grow a little each time
a ball goes through, up to a full size.  A ball never leaves steeper than before, even as the
arrows turn through straight up or down.  Replays and the friend's screen show the same, and the
friend's screen flies the ball through them by the same rule.
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
        self.pu.open_portals()
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

    def test_they_open_small(self):
        for door in self.pu.portals:
            self.assertEqual(door["r"], PowerUps.PORTAL_START)

    def test_they_drift_and_turn(self):
        start = [dict(p) for p in self.pu.portals]
        after = self.drift(5.0)[-1]
        for a, b in zip(start, after):
            self.assertGreater(math.hypot(b["x"] - a["x"], b["y"] - a["y"]), 50, "it didn't drift")
            turned = abs((b["angle"] - a["angle"] + math.pi) % math.tau - math.pi)
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
        self.assertEqual(sizes[0], [PowerUps.PORTAL_START + PowerUps.PORTAL_GROW] * 2)
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


class BuiltAhead(unittest.TestCase):
    def test_every_size_they_grow_through(self):
        for job in app.renderer.prewarm_jobs():
            job()
        for R in range(PowerUps.PORTAL_START, PowerUps.PORTAL_R + 1, PowerUps.PORTAL_GROW):
            self.assertIn(("portal_ring", R), app.art.cache)


if __name__ == "__main__":
    unittest.main()

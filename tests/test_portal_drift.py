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

Rowan's 1.8 plan (2026-11-18): they grow bigger (to 120, from 96); a ball spends a moment inside
(0.2 s, out of sight) while the way out flashes, and comes out 8% slower each trip, never slower
than a serve nor faster than it went in.

Rowan's second 1.8 playtest (same day): "I want the portal pairs to just be like the size that they
are in the talisman power-up, and they don't grow in size, but they still drift across the court."
They're 72 and stay it (the collapse went to the Black Hole, and the Portal Pair game mode became
the Black Hole mode: see test_black_hole_grows).  "I don't like their dual-colouring as the way to
determine the direction... change it to a dotted path line": dots along the way a ball comes out,
faint, bright as one is about to.  And "the portals seemed to flip every now and then, not just
rotate": a portal turned right round, and as its way out passed too steep it jumped from steeply up
to steeply down.  Now one faces each way, and each sweeps up and down on its own side, turning back
before it would send a ball out too steeply.
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

    def test_the_talismans_size_and_they_never_grow(self):
        self.pu.portals = []
        self.pu.collect({"kind": "portal", "x": 900, "y": 500}, self.game.p1)
        self.assertEqual([door["r"] for door in self.pu.portals], [72.0, 72.0])
        for _ in range(8):
            self.go_through(self.pu.portals[0])
        self.assertEqual([door["r"] for door in self.pu.portals], [72.0, 72.0])
        self.assertEqual(self.pu.holes, [], "nor collapse")

    def test_the_talismans_close_with_the_point(self):
        self.pu.on_point()
        self.assertEqual(self.pu.portals, [])

    def test_they_drift_and_turn(self):
        """How far each goes, not where it ends up: one can bounce off an edge and come back."""
        frames = [[dict(p) for p in self.pu.portals]] + self.drift(5.0)
        for i in range(2):
            path = sum(math.hypot(b[i]["x"] - a[i]["x"], b[i]["y"] - a[i]["y"]) for a, b in zip(frames, frames[1:]))
            self.assertGreater(path, PowerUps.PORTAL_DRIFT[0] * 5 * 0.9, "it didn't drift (or stuck)")
            turned = sum(abs((b[i]["angle"] - a[i]["angle"] + math.pi) % math.tau - math.pi)
                         for a, b in zip(frames, frames[1:]))
            self.assertGreater(turned, 0.25, "it didn't turn")

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

    def go_through(self, door, speed = 600.0):
        ball = self.game.ball
        ball.x0, ball.y0 = door["x"] - ball.width / 2, door["y"] - ball.height / 2
        ball.x1, ball.y1 = ball.x0 + ball.width, ball.y0 + ball.height
        ball.vx, ball.vy, ball.portal_cool = speed, 0.0, 0.0
        self.pu.portal_trips = 0
        self.pu.update_portals(DT)
        for _ in range(60):                                       # (a moment inside: 1.8)
            if not ball.transit:
                break
            self.pu.update_portals(DT)

    def test_one_faces_each_way_and_sweeps_up_and_down_without_flipping(self):
        """However it sweeps, a portal faces its own side, never too steeply (so the way it's drawn
        facing is the way a ball comes out), and turns smoothly: no jump from steeply up to steeply
        down.  It sweeps right up to as steep as a ball may leave, and back."""
        sides = sorted(math.copysign(1, math.cos(door["angle"])) for door in self.pu.portals)
        self.assertEqual(sides, [-1, 1])
        frames = [[dict(p) for p in self.pu.portals]] + self.drift(40.0)
        for i in range(2):
            side = math.copysign(1, math.cos(frames[0][i]["angle"]))
            for a, b in zip(frames, frames[1:]):
                angle = b[i]["angle"]
                dx, dy = PowerUps.portal_exit(angle)
                self.assertAlmostEqual(dx, math.cos(angle), places = 9, msg = "steeper than a ball may leave")
                self.assertAlmostEqual(dy, math.sin(angle), places = 9)
                self.assertGreater(dx * side, 0, "it turned right round")
                jump = abs((angle - a[i]["angle"] + math.pi) % math.tau - math.pi)
                self.assertLessEqual(jump, PowerUps.PORTAL_TURN[1] * DT + 1e-6, "it flipped")
            steepest = min(abs(math.cos(f[i]["angle"])) for f in frames)
            self.assertLess(steepest, PowerUps.PORTAL_STEEPEST + 0.03, "it sweeps as steep as it may")
            ups = [math.sin(f[i]["angle"]) for f in frames]
            self.assertTrue(min(ups) < -0.5 and max(ups) > 0.5, "up and down")

    def test_the_ball_comes_out_the_way_it_faces(self):
        for _ in range(20):
            self.drift(0.7)
            self.go_through(self.pu.portals[0])
            ball, out = self.game.ball, self.pu.portals[1]
            self.assertAlmostEqual(math.atan2(ball.vy, ball.vx), app.renderer.portal_facing(out), places = 6)

    def test_says_so(self):
        about = BY_KEY["portal"].about
        self.assertIn("drifting", about)
        self.assertIn("one facing each way", about)
        self.assertIn("dotted line", about)
        self.assertIn("sweeps up and down", about)
        self.assertNotIn("grow", about)

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
        self.assertEqual(ReplayView(SimpleNamespace(info = {"rows": 2}, frames = [], events = [], moments = []),
                                    app).portal_fields, 4, "1.7's: a size, no flash")
        for _ in range(2):
            self.game.recorder.capture(1 / 60)
        self.assertEqual(ReplayView(self.game.recorder.clip(), app).portal_fields, 5)

    def test_a_moment_inside_while_the_way_out_flashes(self):
        ball, door, out = self.game.ball, self.pu.portals[0], self.pu.portals[1]
        ball.x0, ball.y0 = door["x"] - ball.width / 2, door["y"] - ball.height / 2
        ball.x1, ball.y1 = ball.x0 + ball.width, ball.y0 + ball.height
        ball.vx, ball.vy, ball.portal_cool = 900.0, 0.0, 0.0
        self.pu.update_portals(DT)
        self.assertIsNotNone(ball.transit)
        self.assertEqual(self.pu.ball_alpha(), 0.0, "out of sight inside")
        self.assertGreater(out["flash"], 0.9, "the way out flashes")
        self.assertFalse(ball.can_collide_with(self.game.p1))
        inside = 0
        while ball.transit:
            self.pu.update_portals(DT)
            inside += 1
        self.assertAlmostEqual(inside * DT, PowerUps.PORTAL_TRANSIT, delta = 2 * DT)
        self.assertLess(math.hypot((ball.x0 + ball.x1) / 2 - out["x"], (ball.y0 + ball.y1) / 2 - out["y"]),
                        out["r"] + ball.width, "out of the other")
        self.assertEqual(self.pu.ball_alpha(), 1.0)

    def test_a_little_slower_each_trip_but_never_below_a_serve(self):
        ball = self.game.ball
        serve = ball.speed * math.sqrt(2)
        self.go_through(self.pu.portals[0], 1500.0)
        self.assertAlmostEqual(math.hypot(ball.vx, ball.vy), 1500.0 * (1 - PowerUps.PORTAL_SLOW), delta = 1)
        self.go_through(self.pu.portals[0], serve + 20)
        self.assertAlmostEqual(math.hypot(ball.vx, ball.vy), serve, delta = 1, msg = "no slower than a serve")
        self.go_through(self.pu.portals[0], 400.0)
        self.assertAlmostEqual(math.hypot(ball.vx, ball.vy), 400.0, delta = 1, msg = "nor faster than it went in")

    def test_the_talismans_size(self):
        self.assertEqual(PowerUps.PORTAL_R, 72)


class NoPortalPairMode(unittest.TestCase):
    """Rowan's second 1.8 playtest: the Portal Pair game mode became the Black Hole mode (see
    test_black_hole_grows), and the Portal Pair talisman turns up in a Black Hole match."""

    def test_gone(self):
        self.assertNotIn("portal_pair", m.MODES)
        self.assertFalse(hasattr(m, "mode_portal_pair"))
        self.assertNotIn("Portal Pair match", BY_KEY["portal"].about)
        self.assertNotIn("portal_pair", app.renderer.MODE_TIPS)

    def test_the_talisman_turns_up_in_a_black_hole_match(self):
        random.seed(23)
        m.reset()
        m.mode_black_hole = True
        game = Hu_Taong(app)
        game.start()
        try:
            self.assertEqual(game.powerups.portals, [])
            self.assertTrue(game.powerups.spawnable(BY_KEY["portal"]))
        finally:
            game.stop()
            m.reset()


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

    def test_a_moment_inside_on_the_friends_screen_too(self):
        """(1.8) The friend's screen holds the ball inside for as long as the host's game does."""
        guest = GuestMatchState.__new__(GuestMatchState)
        guest.view = SimpleNamespace(
            stones = [], settings = SimpleNamespace(pace = 1.0), ball = SimpleNamespace(curve = 0.0),
            powerups = SimpleNamespace(alpha = 1.0, ghostly = lambda: False, wind = 0.0,
                                       portals = [{"x": 700.0, "y": 540.0, "angle": 0.0, "r": 48.0},
                                                  {"x": 1300.0, "y": 300.0, "angle": 0.0, "r": 48.0}]))
        x, y, vx, vy = guest.fly(650.0, 540.0, 1000.0, 0.0, 20.0, 0.1)
        self.assertEqual((vx, vy), (0.0, 0.0), "still inside")
        x, y, vx, vy = guest.fly(650.0, 540.0, 1000.0, 0.0, 20.0, 0.4)
        self.assertGreater(x, 1300, "out of the other")
        self.assertAlmostEqual(vx, 1000.0 * (1 - PowerUps.PORTAL_SLOW), delta = 1)

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
                for start in (PowerUps.PORTAL_R,):
                    room = pu.portal_room(start)
                    for i in range(150):
                        x = (100, 960, 1800)[i % 3]
                        ball.x0, ball.x1 = x, x + ball.width
                        pu.portals = []
                        pu.open_portals()
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
    def test_open_flashing_and_every_size_they_shut_through(self):
        from tests.test_warm_art import Counting
        app.dt = 1 / 60
        portals = [{"x": 700, "y": 400, "angle": a, "r": float(PowerUps.PORTAL_R), "flash": f}
                   for a in (0.0, 0.6, -1.1, 3.0, 2.3) for f in (0.0, 0.25, 0.5, 0.75, 1.0)]
        closing = [{"x": 1200, "y": 600, "angle": 0.4, "r": float(PowerUps.PORTAL_R), "flash": 0.0, "shut": s / 20}
                   for s in range(1, 21)]
        with Counting() as c:
            app.renderer.draw_portals(app.virtual, SimpleNamespace(portals = portals, closing = closing), 0, 0)
        self.assertEqual(c.built, [])


class Ovals(unittest.TestCase):
    """Rowan's playtest (2026-11-18): keeping track of the turning arrows was hard ("what about
    having them slightly ellipse shaped, so the ball will fly out the widest side").  A portal is an
    oval, wide across its face and shallow along its way out, and no arrows are drawn.  (Its front
    was rimmed bright, until the second playtest: see DottedWay.)"""

    def test_wide_across_and_shallow_along_the_way_out(self):
        r = app.renderer
        for angle in (0.0, 0.7, 2.6, -0.9):
            facing = r.portal_facing({"angle": angle})
            fx, fy = r.portal_point(0, 0, 100, facing, 0.0)
            sx, sy = r.portal_point(0, 0, 100, facing, math.pi / 2)
            self.assertAlmostEqual(math.hypot(fx, fy), 100 * r.PORTAL_SQUASH, places = 6)
            self.assertAlmostEqual(math.hypot(sx, sy), 100, places = 6)
            dx, dy = PowerUps.portal_exit(angle)
            self.assertAlmostEqual(fx / math.hypot(fx, fy), dx, places = 6, msg = "its front faces the way out")

    def test_no_arrows(self):
        from tests.test_black_hole import straight_lines
        app.dt = 1 / 60
        portals = [{"x": 700, "y": 400, "angle": 0.5, "r": 120.0, "flash": 0.0},
                   {"x": 1200, "y": 700, "angle": 2.0, "r": 120.0, "flash": 1.0}]
        self.assertEqual(straight_lines(lambda: app.renderer.draw_portals(
            app.virtual, SimpleNamespace(portals = portals, closing = []), 0, 0)), 0)


class DottedWay(unittest.TestCase):
    """Rowan's second playtest: dots from each portal's front along the way a ball comes out of it,
    faint, and brighter and bigger as a ball is about to come out; bouncing off the top and bottom
    as a ball would, and stopping at a stone.  None as a portal shuts."""
    EDGE = (14, 18, 38)                                           # (each dot's dark edge)

    def dots(self, door, stones = (), closing = False):
        import pygame
        seen, real = [], pygame.draw.circle

        def circle(surface, colour, centre, radius, *a, **k):
            seen.append((centre, radius, tuple(colour)[:3]))
            return real(surface, colour, centre, radius, *a, **k)
        pygame.draw.circle = circle
        try:
            app.dt = 1 / 60
            app.renderer.draw_portals(app.virtual, SimpleNamespace(
                portals = [] if closing else [door], closing = [door] if closing else [],
                game = SimpleNamespace(objects = list(stones))), 0, 0)
        finally:
            pygame.draw.circle = real
        R = app.renderer.portal_size(door)
        return [(c, r, col) for c, r, col in seen
                if col != self.EDGE and math.hypot(c[0] - door["x"], c[1] - door["y"]) > R]

    def door(self, x = 700.0, y = 540.0, angle = 0.3, flash = 0.0):
        return {"x": x, "y": y, "angle": angle, "r": float(PowerUps.PORTAL_R), "flash": flash}

    def test_along_the_way_out(self):
        door = self.door()
        dots = self.dots(door)
        self.assertGreaterEqual(len(dots), 12)
        ux, uy = math.cos(0.3), math.sin(0.3)
        for (x, y), _, _ in dots:
            ahead = (x - door["x"]) * ux + (y - door["y"]) * uy
            off = abs((x - door["x"]) * uy - (y - door["y"]) * ux)
            self.assertGreater(ahead, 0)
            self.assertLess(off, 1.5)

    def test_brighter_and_bigger_as_a_ball_is_about_to_come_out(self):
        faint, bright = self.dots(self.door()), self.dots(self.door(flash = 1.0))
        self.assertGreater(sum(r for _, r, _ in bright), sum(r for _, r, _ in faint) * 1.25)
        self.assertGreater(sum(sum(col) for _, _, col in bright) / len(bright),
                           sum(sum(col) for _, _, col in faint) / len(faint) + 60)

    def test_bouncing_off_the_bottom_as_a_ball_would(self):
        dots = self.dots(self.door(x = 900.0, y = 950.0, angle = 1.0))
        ys = [y for (_, y), _, _ in dots]
        self.assertLessEqual(max(ys), BASE_H - 15)
        self.assertLess(ys[-1], max(ys) - 50, "back up after the bounce")

    def test_stopping_at_a_stone(self):
        stone = SimpleNamespace(is_obstacle = True, x0 = 950, y0 = 0, x1 = 1010, y1 = BASE_H)
        dots = self.dots(self.door(angle = 0.0), [stone])
        self.assertTrue(dots)
        self.assertLess(max(x for (x, _), _, _ in dots), 950)

    def test_none_as_it_shuts(self):
        door = dict(self.door(), shut = 0.5)
        self.assertEqual(self.dots(door, closing = True), [])


if __name__ == "__main__":
    unittest.main()

"""The Black Hole grows and collapses, 1.8 (Rowan's second 1.8 playtest, 2026-11-18).

"I don't want the portal pairs to have the collapse thingy... the black holes, first of all, they
need more suction initially... with every ball that it sucks in, it gets bigger.  And I also want
the black holes to drift as well... once it gets big enough, collapse in on itself and then start
spawning the mini black holes until the point is won... And also change the game mode from portal
pair to Black hole."

So the Black Hole pulls harder from the start (a quick shot 150 px off-centre got away before), and
drifts slowly about mid-court, keeping clear of where the ball is served from.  Each ball it
swallows makes it bigger (its reach, pull and heart), twice; then the next ball it swallows makes it
collapse in on itself, holding the ball for COLLAPSE_TIME, standing still and pulling nothing.  Then
it bursts: a lone ball comes out as Twin Balls heading for the goals they can score in, or with two
balls in play already the ball comes out alone, heading for its own; and mini black holes come and
go, drifting too, until the point is won.  The Black Hole game mode (it was Portal Pair) keeps one
all match, as big as it has grown point after point (still while a point is announced); after a
collapse a new one opens at the next serve.  A 1.7 save with Portal Pair on has the Black Hole mode
on.  The AI reckons with its size and its drift, the friend's screen with its size, and replays show
it all, and still load 1.8's earlier rows.

(The collapse came first to Portal Pair, earlier the same day: its portals grew, then collapsed into a
black hole.  The mini black holes' rules, and no arrows on any black hole, are as they were then.)

Rowan's third playtest (same day): "Make the black holes be able to grow bigger, and also make them
drift across the court more, and make them collapse after more balls... more like 5 or even more."
So it grows five times (to twice its size, its reach half as much again), and the sixth ball makes
it collapse; it drifts faster.  And "black holes [shouldn't] spawn or drift too close to the goals,
something like the middle third of the court": the Black Hole and the mini ones keep to the middle
third (a Black Hole match's still clear of the serve; the talisman's no longer needs to be).

Rowan's fourth playtest (same day): "I also want the mini black holes to spawn more frequently, and
last for a bit longer.  Maybe one spawns randomly every 0.5 - 1.5 seconds, and they last randomly for
5-10 seconds."  Up to six at once now (three would have held most of them back), 220 px apart.
And "I would like to be able to see what it'd be like to play the game where black holes collapsing
didn't spew out twin balls, but instead just one ball still": Black Hole Twins, a Match setting, on
by default; off, the ball bursts out alone, heading for the goal it can score in.  In 1.9 Rowan
settled it: one ball, always, and the switch is gone.
"""
import json
import math
import random
import unittest
from array import array
from types import SimpleNamespace

from tests import harness

app = harness.app()

from config import BASE_W, BASE_H                               # noqa: E402
from core import save_data                                      # noqa: E402
from core.states.guest_state import GuestMatchState             # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import BY_KEY, PowerUps                      # noqa: E402
from game.replay import HOLE_FIELDS, NO_AIM, ReplayView         # noqa: E402
from tests.test_black_hole import straight_lines               # noqa: E402
from tests.test_warm_art import Counting                        # noqa: E402

m = app.settings.match
DT = 1 / 120
P = PowerUps
FULL = 1 + P.HOLE_GROW * P.HOLE_GROWTHS                         # its size, full-grown


class Match(unittest.TestCase):
    MODE = False

    def setUp(self):
        random.seed(11)
        m.reset()
        m.mode_black_hole = self.MODE
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.pu = self.game.powerups
        self.pu.wait = 999.0
        self.ball = self.game.ball
        self.game.p1.ai_enabled = self.game.p2.ai_enabled = False
        if not self.MODE:
            self.place(100, 540, 0.0, 0.0)
            self.pu.open_hole()
        self.hole = self.pu.big_hole()
        self.hole["age"], self.hole["power"] = 5.0, 1.0           # (wide open)

    def tearDown(self):
        self.game.stop()
        m.reset()

    def place(self, x, y, vx, vy, ball = None):
        ball = ball or self.ball
        r = ball.width / 2
        ball.x0, ball.y0, ball.x1, ball.y1 = x - r, y - r, x + r, y + r
        ball.vx, ball.vy = vx, vy

    def park(self, ball = None):
        """A ball out of the way, and out of every pull."""
        ball = ball or self.ball
        ball.transit = None
        self.place(40, 40, 0.0, 0.0, ball)
        ball.hole_cool = 999.0

    def play(self, seconds, dt = DT, balls = None):
        for _ in range(round(seconds / dt)):
            self.pu.update_portals(dt)
            self.pu.update_holes(dt)
            self.pu.update_minis(dt)
            for b in self.pu.balls() if balls is None else balls:
                if not b.transit:
                    b.x0 += b.vx * dt
                    b.x1 += b.vx * dt
                    b.y0 += b.vy * dt
                    b.y1 += b.vy * dt

    def feed(self, speed = 1000.0, ball = None):
        """A ball sent straight at the Black Hole's heart, till it's inside."""
        ball = ball or self.ball
        h = self.hole
        ball.transit, ball.hole_cool, ball.hole_speed, ball.hole_time = None, 0.0, None, 0.0
        self.place(h["x"] - 150, h["y"], speed, 0.0, ball)
        for _ in range(120):
            self.play(DT, balls = [ball])
            if ball.transit:
                return
        self.fail("not swallowed")

    def out(self, ball = None):
        """Wait for it to come out, then put it out of the way."""
        ball = ball or self.ball
        while ball.transit:
            self.play(DT, balls = [])
        self.park(ball)

    def grown(self):
        h = self.hole
        h["eaten"], h["size"] = P.HOLE_GROWTHS, FULL
        return h


class Growing(Match):
    def test_pulls_harder_from_the_start(self):
        self.assertGreaterEqual(P.HOLE_PULL, 9000)
        h = self.hole
        h["vx"] = h["vy"] = 0.0
        self.place(h["x"] - 440, h["y"] + 150, 1200.0, 0.0)      # a quick shot, 150 px off-centre
        fell = False
        for _ in range(180):
            self.play(DT, balls = [self.ball])
            fell = fell or bool(self.ball.transit)
        self.assertTrue(fell, "drawn in")

    def test_each_ball_it_swallows_makes_it_bigger_twice(self):
        h = self.hole
        styles = [P.hole_style(h)]
        for n in range(1, P.HOLE_GROWTHS + 1):
            self.feed()
            self.assertEqual(h["eaten"], n)
            self.play(P.HOLE_GROW_TIME / 2, balls = [])
            self.assertTrue(1 + P.HOLE_GROW * (n - 1) < h["size"] < 1 + P.HOLE_GROW * n, "growing")
            self.out()
            self.play(P.HOLE_GROW_TIME / 2 + 0.05, balls = [])
            self.assertAlmostEqual(h["size"], 1 + P.HOLE_GROW * n)
            styles.append(P.hole_style(h))
        for before, after in zip(styles, styles[1:]):
            for a, b in zip(before, after):
                self.assertGreater(b, a, "its reach, pull and heart all grow")
        self.assertIsNone(h["collapse"])
        self.assertIsNone(h["dying"])

    def test_bigger_it_pulls_from_further(self):
        h = self.hole
        h.update(x = 960.0, y = 400.0, vx = 0.0, vy = 0.0)
        serve = self.ball.speed * math.sqrt(2)

        def caught(size):
            h["size"], h["eaten"] = size, round((size - 1) / P.HOLE_GROW)
            self.ball.transit, self.ball.hole_speed, self.ball.hole_time, self.ball.hole_cool = None, None, 0.0, 0.0
            self.place(h["x"] - P.hole_style(h)[0] - 10, h["y"] + 380, serve, 0.0)
            for _ in range(480):
                self.play(DT, balls = [self.ball])
                if self.ball.transit:
                    return True
            return False
        self.assertFalse(caught(1.0), "a serve 380 px off gets past it as it opens")
        self.assertTrue(caught(FULL), "but not once it's full-grown")

    def test_it_drifts_slowly_about_mid_court_clear_of_the_serve(self):
        h = self.hole
        self.park()
        seen = []
        for _ in range(60 * 40):
            self.play(1 / 60, dt = 1 / 60, balls = [])
            seen.append((h["x"], h["y"]))
        path = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(seen, seen[1:]))
        self.assertGreater(path, P.HOLE_DRIFT[0] * 40 * 0.9, "it drifts")
        self.assertGreaterEqual(P.HOLE_DRIFT[0], 45, "drifting more (Rowan's third playtest)")
        for a, b in zip(seen, seen[1:]):
            self.assertLessEqual(math.hypot(b[0] - a[0], b[1] - a[1]), P.HOLE_DRIFT[1] / 60 + 1e-6)
        for x, y in seen:
            self.assertTrue(BASE_W / 3 - 1 <= x <= BASE_W * 2 / 3 + 1, "in the middle third")
            self.assertTrue(P.HOLE_AREA[2] - 1 <= y <= BASE_H - P.HOLE_AREA[2] + 1)

    def test_it_opens_in_the_middle_third(self):
        for _ in range(40):
            self.pu.holes = []
            self.place(random.uniform(100, BASE_W - 100), random.uniform(100, BASE_H - 100), 0.0, 0.0)
            self.pu.open_hole()
            x = self.pu.holes[0]["x"]
            self.assertTrue(BASE_W / 3 <= x <= BASE_W * 2 / 3)

    def test_the_sixth_ball_it_swallows_makes_it_collapse(self):
        h = self.hole
        for n in range(1, 6):
            self.feed()
            self.out()
            self.assertIsNone(h["collapse"], f"collapsed at ball {n}")
        self.feed()
        self.assertIsNotNone(h["collapse"], "not at the sixth")

    def test_it_grows_to_twice_its_size(self):
        self.assertAlmostEqual(FULL, 2.0)
        h = dict(self.hole, size = FULL)
        reach, pull, core = P.hole_style(h)
        self.assertAlmostEqual(core, P.HOLE_CORE * 2)
        self.assertAlmostEqual(pull, P.HOLE_PULL * 2)
        self.assertAlmostEqual(reach, P.HOLE_REACH * 1.5, msg = "its reach half as much again, off the goals")


class Collapsing(Match):
    def test_full_grown_the_next_ball_it_swallows_makes_it_collapse(self):
        h = self.grown()
        self.feed()
        self.assertEqual(h["collapse"], 0.0)
        self.assertEqual(self.ball.transit["left"], P.COLLAPSE_TIME, "the ball held all through it")
        self.assertNotIn(h, self.pu.pulling(), "pulling nothing")
        self.assertFalse(P.swallows(h))
        x, y = h["x"], h["y"]
        self.play(P.COLLAPSE_TIME / 2, balls = [])
        self.assertEqual((h["x"], h["y"]), (x, y), "standing still")
        self.assertTrue(self.ball.transit)
        self.assertAlmostEqual(h["collapse"], P.COLLAPSE_TIME / 2, delta = DT)

    def test_then_the_ball_bursts_out_alone_heading_for_where_it_scores(self):
        """Rowan, 1.9: "Make Black Hole Collapse shoot out just one ball, not twin balls.  And remove
        the setting to toggle between the two."  (1.8 burst it out as Twin Balls, unless the Black
        Hole Twins switch in Match settings was off.)"""
        h = self.grown()
        self.feed(1400.0)
        self.play(P.COLLAPSE_TIME + 0.05, balls = [])
        self.assertIsNone(self.pu.twin, "no Twin Balls")
        self.assertEqual(len([o for o in self.game.objects if o.is_ball]), 1)
        self.assertGreater(self.ball.vx, 0, "heading for Blue's goal, where it scores")
        self.assertGreaterEqual(abs(self.ball.vx) / math.hypot(self.ball.vx, self.ball.vy), P.PORTAL_STEEPEST - 1e-6)
        self.assertAlmostEqual(math.hypot(self.ball.vx, self.ball.vy), 1400.0, delta = 1, msg = "at its own speed")
        self.assertAlmostEqual(h["dying"], P.HOLE_IMPLODE * P.HOLE_BURST, msg = "gone in a flash")
        self.assertIsNone(self.pu.big_hole())
        self.assertTrue(self.pu.minis, "then the mini ones")

    def test_no_black_hole_twins_switch(self):
        m.reset()
        self.assertFalse(hasattr(m, "hole_twins"))
        self.assertNotIn("hole_twins", save_data.collect(app)["gameplay"])
        from tests.test_settings_menus import open_screen
        self.assertNotIn("toggle_hole_twins", open_screen("match").ui_hitboxes)

    def test_a_save_with_it_still_loads(self):
        path = save_data.save_path()
        kept = path.read_text() if path.exists() else None
        try:
            data = save_data.collect(app)
            data["gameplay"]["hole_twins"] = False          # (1.8 wrote it)
            path.parent.mkdir(parents = True, exist_ok = True)
            path.write_text(json.dumps(data))
            save_data.load(app)
            self.assertFalse(hasattr(m, "hole_twins"))
        finally:
            if kept is None:
                path.unlink()
            else:
                path.write_text(kept)

    def test_with_two_balls_in_play_the_ball_comes_out_alone(self):
        self.grown()
        self.pu.split_ball()
        blue = self.pu.twin["ball"]
        self.park()
        self.feed(1000.0, blue)
        self.play(P.COLLAPSE_TIME + 0.05, balls = [])
        self.assertEqual(len([o for o in self.game.objects if o.is_ball]), 2, "no third ball")
        self.assertLess(blue.vx, 0, "heading for Red's goal, where it scores")
        self.assertAlmostEqual(math.hypot(blue.vx, blue.vy), 1000.0, delta = 1)

    def test_the_points_end(self):
        h = self.grown()
        self.feed()
        self.pu.on_point()
        self.assertIsNotNone(h["dying"], "it implodes")
        self.play(P.COLLAPSE_TIME + 0.1, balls = [])
        self.assertIsNone(self.pu.twin, "no burst once the point is over")
        self.assertIsNone(self.pu.minis)
        self.pu.serve_holes()
        self.assertEqual(self.pu.holes, [])

    def test_counted_once_and_listed(self):
        self.grown()
        self.feed()
        self.assertEqual(self.pu.in_play(), 1)
        self.assertFalse(self.pu.spawnable(BY_KEY["hole"]))
        self.assertIn(("hole", "The black hole collapsed: mini black holes"), [(k, note) for k, _, note in self.pu.court_list()])
        self.play(P.COLLAPSE_TIME + 0.05, balls = [])
        self.assertFalse(self.pu.spawnable(BY_KEY["hole"]), "not while the mini ones come and go")

    def test_said_so(self):
        about = BY_KEY["hole"].about
        for words in ("drifts", "bigger", "collapse in on itself", "ball bursts out, heading for the goal it can score in",
                      "mini black holes", "Doesn't turn up in a Black Hole match"):
            self.assertIn(words, about)
        self.assertNotIn("Twin Balls", about)


class InABlackHoleMatch(Match):
    MODE = True

    def next_point(self):
        g = self.game
        g.on_score(g.ball, {"normal": (1, 0)})
        g.message_timer = 0.001
        g.update(0.01)

    def test_it_drifts_clear_of_the_serve(self):
        h = self.hole
        self.park()
        for _ in range(60 * 30):
            self.play(1 / 60, dt = 1 / 60, balls = [])
            self.assertGreater(math.hypot(h["x"] - BASE_W / 2, h["y"] - BASE_H / 2), P.HOLE_SERVE_GAP - 5)

    def test_open_from_the_first_serve(self):
        self.assertIsNotNone(self.hole)
        self.assertTrue(self.hole["mode"])
        self.assertEqual((self.hole["size"], self.hole["eaten"]), (1.0, 0))
        self.assertEqual(self.pu.portals, [])

    def test_it_stays_point_after_point_as_big_as_it_has_grown(self):
        h = self.hole
        self.feed()
        self.out()
        self.play(P.HOLE_GROW_TIME + 0.1, balls = [])
        for _ in range(3):
            self.next_point()
            self.assertIs(self.pu.big_hole(), h)
            self.assertIsNone(h["dying"])
            self.assertAlmostEqual(h["size"], 1 + P.HOLE_GROW)
        self.assertEqual(self.pu.in_play(), 0, "a game mode doesn't count")

    def test_still_while_a_point_is_announced(self):
        h = self.hole
        self.place(h["x"] - 120, h["y"] + 30, 0.0, 0.0)
        x, y = h["x"], h["y"]
        self.game.message_timer = 1.0
        try:
            self.pu.update_holes(0.5)
        finally:
            self.game.message_timer = 0.0
        self.assertEqual((h["x"], h["y"]), (x, y))
        self.assertEqual((self.ball.vx, self.ball.vy), (0.0, 0.0), "no pull")

    def test_after_it_collapses_a_new_one_opens_at_the_next_serve(self):
        h = self.grown()
        self.feed()
        self.play(P.COLLAPSE_TIME + 0.05, balls = [])
        self.assertIsNone(self.pu.big_hole())
        self.next_point()
        new = self.pu.big_hole()
        self.assertIsNotNone(new)
        self.assertIsNot(new, h)
        self.assertEqual((new["size"], new["eaten"]), (1.0, 0))
        self.assertIsNone(self.pu.minis)

    def test_no_black_hole_talisman(self):
        self.assertFalse(self.pu.spawnable(BY_KEY["hole"]))

    def test_switched_off_mid_match_it_goes_at_the_next_serve(self):
        m.mode_black_hole = False
        self.next_point()
        self.assertEqual(self.pu.holes, [])

    def test_saved_and_on_match_setup(self):
        gameplay = save_data.collect(app)["gameplay"]
        self.assertIs(gameplay["mode_black_hole"], True)
        self.assertIs(gameplay["mode_portal_pair"], True, "written as 1.7's Portal Pair too, for 1.7")
        self.assertIn("black_hole", app.renderer.MODE_TIPS)
        self.assertEqual(m.MODE_NAMES["black_hole"], "Black Hole")
        self.assertNotIn("portal_pair", m.MODES)

    def test_a_1_7_save_with_portal_pair_on_has_the_black_hole_mode_on(self):
        path = save_data.save_path()
        kept = path.read_text() if path.exists() else None
        try:
            path.parent.mkdir(parents = True, exist_ok = True)
            for saved, on in (({"mode_portal_pair": True}, True), ({"mode_portal_pair": False}, False),
                              ({"mode_portal_pair": True, "mode_black_hole": False}, False)):
                data = save_data.collect(app)
                data["gameplay"] = saved
                path.write_text(json.dumps(data))
                m.reset()                                       # (as at launch)
                save_data.load(app)
                self.assertIs(m.mode_black_hole, on, saved)
        finally:
            if kept is None:
                path.unlink()
            else:
                path.write_text(kept)


class MiniHoles(Match):
    def start(self):
        self.pu.holes = []
        self.pu.minis = {"next": 0.0}
        self.park()

    def minis(self):
        return [h for h in self.pu.holes if h["kind"] == P.HOLE_MINI]

    def test_every_half_a_second_to_a_second_and_a_half_each_five_to_ten_seconds(self):
        self.assertEqual((P.MINI_EVERY, P.MINI_LIFE, P.MINI_MOST), ((0.5, 1.5), (5.0, 10.0), 6))
        self.start()
        opened = []
        real = self.pu.open_mini
        self.pu.open_mini = lambda: (opened.append(1), real())
        self.play(4.0, balls = [])
        self.assertGreaterEqual(len(opened), 3)
        self.assertGreaterEqual(len(self.minis()), 3, "and they're still there")

    def test_come_and_go_up_to_six_until_the_point_ends(self):
        self.start()
        opened, most = [], 0
        real = self.pu.open_mini
        self.pu.open_mini = lambda: (opened.append(1), real())
        for _ in range(40):
            self.play(0.5, balls = [])
            live = self.minis()
            most = max(most, len(live))
            for h in live:
                self.assertTrue(BASE_W / 3 - 1 <= h["x"] <= BASE_W * 2 / 3 + 1, "in the middle third")
        self.assertLessEqual(most, P.MINI_MOST)
        self.assertGreater(len(opened), 5, "new ones keep coming")
        self.pu.on_point()
        self.assertIsNone(self.pu.minis)

    def test_each_fades_in_lasts_its_while_drifting_and_fades_out(self):
        self.start()
        self.play(DT, balls = [])
        h = self.minis()[0]
        self.pu.minis["next"] = 999.0
        self.assertTrue(P.MINI_LIFE[0] - DT <= h["left"] <= P.MINI_LIFE[1])
        powers, seen = [], [(h["x"], h["y"])]
        while h in self.pu.holes:
            self.play(1 / 30, balls = [])
            powers.append(h["power"])
            seen.append((h["x"], h["y"]))
        path = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(seen, seen[1:]))
        self.assertGreater(path, P.HOLE_DRIFT[0] * P.MINI_LIFE[0] * 0.9, "drifting (1.8 playtest)")
        self.assertTrue(any(0.2 < p < 0.8 for p in powers[:20]), "fading in")
        self.assertTrue(any(0.2 < p < 0.8 for p in powers[-20:]), "fading out")

    def test_they_have_gravity_too(self):
        self.start()
        self.play(DT, balls = [])
        h = self.minis()[0]
        self.pu.minis["next"] = 999.0
        h["age"], h["left"], h["power"], h["vx"], h["vy"] = 2.0, 4.0, 1.0, 0.0, 0.0
        serve = self.ball.speed * math.sqrt(2)
        self.ball.hole_cool = 0.0
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

    def test_a_mini_one_flings_it_on_a_little_slower(self):
        self.start()
        self.play(DT, balls = [])
        h = self.minis()[0]
        self.pu.minis["next"] = 999.0
        h["age"], h["left"], h["power"], h["vx"], h["vy"] = 2.0, 3.0, 1.0, 0.0, 0.0
        speed = 1500.0
        self.ball.hole_cool = 0.0
        self.place(h["x"] - 150, h["y"], speed, 0.0)
        for _ in range(60):
            self.play(DT, balls = [self.ball])
            if self.ball.transit:
                break
        self.assertTrue(self.ball.transit, "in")
        self.assertGreater(h["flash"], 0.5, "its heart pulses")
        self.play(P.MINI_HOLD * 1.5, balls = [])
        self.assertIsNone(self.ball.transit)
        self.assertGreater(self.ball.vx, 0, "on towards the side it was heading for")
        self.assertGreaterEqual(self.ball.vx / math.hypot(self.ball.vx, self.ball.vy), P.PORTAL_STEEPEST - 1e-6)
        self.assertAlmostEqual(math.hypot(self.ball.vx, self.ball.vy), speed * (1 - P.PORTAL_SLOW), delta = 1)


class FriendsScreenAndReplays(Match):
    def guest(self, holes):
        guest = GuestMatchState.__new__(GuestMatchState)
        guest.serve_speed = self.ball.speed
        guest.view = SimpleNamespace(
            stones = [], settings = SimpleNamespace(pace = 1.0), ball = SimpleNamespace(curve = 0.0),
            powerups = SimpleNamespace(alpha = 1.0, ghostly = lambda: False, wind = 0.0, portals = [], holes = holes))
        return guest

    def test_the_friends_screen_feels_it_grow(self):
        bent = []
        for size in (1.0, FULL):
            hole = dict(self.hole, x = 960.0, y = 540.0, size = size)
            x, y, vx, vy = self.guest([hole]).fly(600.0, 540 + 330, 900.0, 0.0, self.ball.width / 2, 0.4)
            bent.append(-vy)
        self.assertGreater(bent[1], bent[0] * 1.5)

    def test_the_friends_screen_lets_it_through_while_it_collapses(self):
        hole = dict(self.hole, x = 960.0, y = 540.0, collapse = 0.5)
        x, y, vx, vy = self.guest([hole]).fly(760.0, 540.0, 1000.0, 0.0, self.ball.width / 2, 0.4)
        self.assertGreater(x, 1060)
        self.assertEqual(vy, 0.0)

    def test_replays_show_it_grow_collapse_and_burst_and_the_minis(self):
        rec = self.game.recorder
        h = self.hole
        app.dt = DT
        stages = [dict(size = 1.0), dict(size = 1.4, eaten = 2), dict(size = FULL, eaten = P.HOLE_GROWTHS, collapse = 0.9)]
        for stage in stages:
            h.update(stage)
            rec.capture(1 / 60)
        h.update(collapse = None, dying = P.HOLE_IMPLODE * P.HOLE_BURST * 0.5, power = 0.0)
        rec.capture(1 / 60)
        self.pu.minis = {"next": 0.0}
        self.park()
        self.pu.update_minis(DT)
        rec.capture(1 / 60)
        view = ReplayView(rec.clip(), app)
        n = len(view.clip.frames)
        for i, stage in enumerate(stages):
            view.show(n - 5 + i)
            seen = view.powerups.holes[0]
            self.assertAlmostEqual(seen["size"], stage["size"], places = 4)
            self.assertEqual(seen["collapse"] is None, "collapse" not in stage)
            if "collapse" in stage:
                self.assertAlmostEqual(seen["collapse"], stage["collapse"], places = 4)
            app.renderer.draw_world(app.virtual, view)
        view.show(n - 2)
        self.assertAlmostEqual(view.powerups.holes[0]["dying"], P.HOLE_IMPLODE * P.HOLE_BURST * 0.5, places = 4)
        app.renderer.draw_world(app.virtual, view)
        view.show(n - 1)
        self.assertIn(P.HOLE_MINI, [hole["kind"] for hole in view.powerups.holes])
        app.renderer.draw_world(app.virtual, view)

    def test_earlier_1_8_rows_still_load(self):
        """Rows from before this playtest (layout 3) gave each black hole 15 numbers: its way out,
        two arrows and where Portal Pair's portals were as they collapsed (kind 2)."""
        rec = self.game.recorder
        self.hole.update(x = 900.0, y = 500.0)
        rec.capture(1 / 60)
        clip = rec.clip()
        row = array("f")
        row.frombytes(clip.frames[-1])
        old = list(row[:-HOLE_FIELDS]) + [900.0, 500.0, 2, 1.0, 3.0, 0.0, -1.0, 1, NO_AIM, NO_AIM, NO_AIM,
                                          -200.0, 0.0, 200.0, 0.0]
        clip.frames[-1] = array("f", old).tobytes()
        clip.info["rows"] = 3
        view = ReplayView(clip, app)
        view.show(len(clip.frames) - 1)
        seen = view.powerups.holes[0]
        self.assertEqual((round(seen["x"]), round(seen["y"]), seen["kind"], seen["size"], seen["collapse"]),
                         (900, 500, P.HOLE_TALISMAN, 1.0, None))
        app.dt = DT
        app.renderer.draw_world(app.virtual, view)

    def test_no_black_hole_has_an_arrow(self):
        holes = [dict(self.hole, size = size, collapse = c, flash = flash)
                 for size in (1.0, FULL) for c in (None, 0.2, 1.2) for flash in (0.0, 0.8)]
        holes += [{"x": 700, "y": 400, "kind": P.HOLE_MINI, "age": 1.0, "power": 1.0, "spin": 1, "way": 0.2,
                   "flash": flash, "dying": None} for flash in (0.0, 0.8)]
        app.dt = DT
        self.assertEqual(straight_lines(lambda: app.renderer.draw_holes(app.virtual, SimpleNamespace(holes = holes), 0, 0)), 0)

    def test_its_art_is_built_ahead(self):
        sizes = [1.0, 1.1, 1.2, 1.25, 1.3, 1.4, 1.5, 1.6, 1.75, 1.8, 1.9, 2.0]
        holes = [dict(self.hole, size = size, age = age, flash = flash, collapse = None, dying = None)
                 for size in sizes for age in (0.1, 0.3, 0.6, 5.0) for flash in (0.0, 0.5, 1.0)]
        holes += [dict(self.hole, size = FULL, collapse = i * 0.05, dying = None) for i in range(32)]
        holes += [dict(self.hole, size = size, collapse = None, dying = d, power = 0.0)
                  for size in sizes for d in (0.65, 0.5, 0.35, P.HOLE_IMPLODE * P.HOLE_BURST, 0.2, 0.1, 0.02)]
        holes += [{"x": 700, "y": 400, "kind": P.HOLE_MINI, "age": 1.0, "power": power, "spin": 1, "way": None,
                   "flash": flash, "dying": dying}
                  for power in (0.1, 0.4, 0.7, 1.0) for flash in (0.0, 0.6) for dying in (None, 0.5, 0.1)]
        app.dt = DT
        with Counting() as c:
            for t in (3.0, 3.013, 3.031):                       # (the collapse's flare flickers)
                app.fx.time = t
                app.renderer.draw_holes(app.virtual, SimpleNamespace(holes = holes), 0, 0)
        self.assertEqual(c.built, [])


class TheAI(Match):
    def test_cant_read_which_way_a_ball_inside_a_mini_will_come_out(self):
        self.pu.holes = []
        self.pu.minis = {"next": 0.0}
        self.park()
        self.pu.update_minis(DT)
        h = self.pu.holes[0]
        self.pu.minis["next"] = 999.0
        h["age"], h["power"], h["vx"], h["vy"] = 2.0, 1.0, 0.0, 0.0
        self.ball.hole_cool = 0.0
        self.place(h["x"] - 120, h["y"], 1500.0, 0.0)
        self.play(0.15, balls = [self.ball])
        self.assertTrue(self.ball.transit)
        ai = self.game.p2.ai
        ai.reset()
        x, y, vx, vy = ai.perceive(self.ball, 1 / 120, 0.0)
        self.assertEqual((round(x), round(y), vx, vy), (round(h["x"]), round(h["y"]), 0.0, 0.0), "where it went in, still")

    def test_sees_a_ball_held_still_as_it_collapses(self):
        h = self.grown()
        self.feed()
        self.play(0.5, balls = [])
        ai = self.game.p2.ai
        ai.reset()
        x, y, vx, vy = ai.perceive(self.ball, 1 / 120, 0.0)
        self.assertEqual((round(x), round(y), vx, vy), (round(h["x"]), round(h["y"]), 0.0, 0.0))

    def test_reckons_with_its_size_and_its_drift(self):
        h = self.hole
        h.update(x = 960.0, y = 540.0, vx = 0.0, vy = 0.0)
        r = self.ball.width / 2
        reckon = lambda: self.pu.hole_path(560.0, 540 + 300, 1000.0, 0.0, r, 1500.0)
        small = reckon()
        h["size"] = FULL
        big = reckon()
        self.assertTrue(big[2] or big[1] < small[1] - 30, "a bigger one bends it further")
        h["size"], h["vy"] = 1.0, 300.0                             # drifting down towards its path
        drifting = reckon()
        self.assertTrue(drifting[2] or drifting[1] < small[1] - 30)
        self.assertEqual((h["x"], h["y"]), (960.0, 540.0), "(reckoned, not moved)")


if __name__ == "__main__":
    unittest.main()

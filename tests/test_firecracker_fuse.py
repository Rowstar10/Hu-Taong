"""The Firecracker's 5-second fuse, 1.6 (Rowan's playtest list, 2026-11-16).

It used to bang after 3 hits.  Now its fuse is lit when it's taken and burns for 5 seconds of play,
shown burning down on the ball; then it bangs, away from whoever hit the ball last.  It still goes
out without a bang if the point ends first.

Playtesting 1.6 (2026-11-17): a number over the ball now counts the fuse down, 5 to 1, red for
the last two, so it can be read mid-rally; online and in replays too.
"""
import math
import unittest

from tests import harness

app = harness.app()

from game.powerups import BY_KEY                                # noqa: E402
from game.replay import ReplayView                              # noqa: E402
from tests.test_powerup_fixes import Match, place               # noqa: E402

DT = 1 / 120


class Fuse(Match):
    def setUp(self):
        super().setUp()
        place(self.ball, 960, 540)
        self.ball.vx, self.ball.vy = 600.0, 0.0
        self.pu.collect({"kind": "cracker", "x": 900, "y": 500}, self.p1)

    def burn(self, seconds):
        for _ in range(int(round(seconds / DT))):
            self.pu.update_cracker(DT)

    def test_lit_as_it_is_taken(self):
        self.assertAlmostEqual(self.pu.cracker_fuse(self.ball), 5.0)
        self.assertIn(("cracker", 5.0), [(k, left) for k, left, _ in self.pu.court_list()])

    def test_bangs_after_five_seconds(self):
        self.burn(4.9)
        self.assertIsNotNone(self.pu.cracker, "not yet")
        self.assertAlmostEqual(self.pu.cracker_fuse(self.ball), 0.1, delta = 0.01)
        before = math.hypot(self.ball.vx, self.ball.vy)
        self.burn(0.2)
        self.assertIsNone(self.pu.cracker, "bang")
        self.assertTrue(self.ball.blazing)
        self.assertGreater(math.hypot(self.ball.vx, self.ball.vy), before * 1.5)

    def test_hits_no_longer_count(self):
        for _ in range(5):
            self.pu.on_hit(self.ball, self.p2, (-1, 0))
        self.assertAlmostEqual(self.pu.cracker_fuse(self.ball), 5.0)

    def test_the_point_ending_puts_it_out(self):
        self.burn(3.0)
        self.pu.on_point()
        self.assertIsNone(self.pu.cracker)
        self.assertFalse(self.ball.blazing, "no bang")

    def test_away_from_whoever_hit_it_last(self):
        self.ball.last_paddle = self.p2
        self.ball.vx = 900.0                     # coming back at Blue
        self.burn(5.1)
        self.assertLess(self.ball.vx, 0)

    def test_no_hit_yet_away_from_whoever_took_it(self):
        self.ball.last_paddle = None
        self.ball.vx = -900.0                    # heading for Red, who took it
        self.burn(5.1)
        self.assertGreater(self.ball.vx, 0)

    def test_only_the_red_ball_carries_it(self):
        self.pu.split_ball()
        blue = self.pu.twin["ball"]
        self.assertEqual(self.pu.cracker_fuse(blue), 0)
        self.assertGreater(self.pu.cracker_fuse(self.ball), 0)


class GameTime(Match):
    def test_the_fuse_waits_through_a_countdown(self):
        self.pu.collect({"kind": "cracker", "x": 900, "y": 500}, self.p1)
        self.game.start_countdown(3)
        for _ in range(60):
            self.game.update(1 / 60)
        self.assertAlmostEqual(self.pu.cracker_fuse(self.ball), 5.0)

    def test_it_burns_at_the_game_pace(self):
        self.game.settings.pace = 0.5
        try:
            self.pu.collect({"kind": "cracker", "x": 900, "y": 500}, self.p1)
            place(self.ball, 960, 540)
            self.ball.vx, self.ball.vy = 300.0, 0.0
            for _ in range(60):                  # a second of play at half pace...
                self.game.update(1 / 60)
            self.assertAlmostEqual(self.pu.cracker_fuse(self.ball), 4.5, delta = 0.05)   # ...burns half a second
        finally:
            self.game.settings.pace = 1.0


class Shown(Match):
    def test_the_fuse_is_recorded_for_replays_and_online(self):
        self.pu.collect({"kind": "cracker", "x": 900, "y": 500}, self.p1)
        self.pu.update_cracker(1.5)
        for _ in range(3):
            self.game.recorder.capture(1 / 60)
        clip = self.game.recorder.clip()
        view = ReplayView(clip, app)
        view.show(len(clip.frames) - 1)
        self.assertAlmostEqual(view.powerups.cracker_fuse(view.ball), 3.5, delta = 0.01)

    def test_the_fuse_is_drawn_shorter_as_it_burns(self):
        """The fuse is drawn from the cracker on the ball; less of it is left as it burns."""
        renderer = app.renderer
        drawn = {}
        real_lines = __import__("pygame").draw.lines

        def spy(surface, colour, closed, points, width = 1):
            drawn["points"] = points
            return real_lines(surface, colour, closed, points, width)
        import pygame
        rect = pygame.Rect(900, 500, 60, 60)
        lengths = []
        pygame.draw.lines = spy
        try:
            for fuse in (5.0, 2.5, 0.5):
                renderer.draw_cracker(app.virtual, rect, fuse)
                (x0, y0), (x1, y1) = drawn["points"][0], drawn["points"][-1]
                lengths.append(math.hypot(x1 - x0, y1 - y0))
        finally:
            pygame.draw.lines = real_lines
        self.assertGreater(lengths[0], lengths[1])
        self.assertGreater(lengths[1], lengths[2])

    def test_descriptions_say_so(self):
        kind = BY_KEY["cracker"]
        self.assertIn("5 seconds", kind.blurb)
        self.assertIn("5 s", kind.about)
        self.assertNotIn("hits", kind.about)
        self.assertIn("point ends first", kind.about)


class CountedDown(Match):
    """The number over the ball: the fuse's seconds, rounded up, red for the last two."""

    def setUp(self):
        super().setUp()
        place(self.ball, 960, 540)
        self.shown = []
        renderer = app.renderer
        self.real = renderer.cracker_digit
        renderer.cracker_digit = lambda n: self.shown.append(n) or self.real(n)

    def tearDown(self):
        app.renderer.cracker_digit = self.real
        super().tearDown()

    def number_at(self, fuse, game = None):
        game = game or self.game
        self.shown.clear()
        if fuse is not None:
            self.pu.cracker = {"fuse": fuse, "taker": self.p1}
        app.renderer.draw_world(app.virtual, game)
        return self.shown[-1] if self.shown else None

    def test_five_to_one(self):
        self.assertEqual([self.number_at(f) for f in (5.0, 4.01, 4.0, 2.5, 2.0, 1.0, 0.3)],
                         [5, 5, 4, 3, 2, 1, 1])

    def test_no_number_without_a_firecracker(self):
        self.pu.cracker = None
        self.assertIsNone(self.number_at(None))

    def test_red_and_bigger_for_the_last_two(self):
        cream, red = self.real(3), self.real(2)
        self.assertGreater(red.get_height(), cream.get_height())
        def reddest(surf):
            w, h = surf.get_size()
            return max(surf.get_at((x, y))[0] - surf.get_at((x, y))[1]
                       for x in range(0, w, 2) for y in range(0, h, 2) if surf.get_at((x, y))[3] > 200)
        self.assertGreater(reddest(red), 120)
        self.assertLess(reddest(cream), 120)

    def test_hidden_while_a_ghost_ball_fades(self):
        self.pu.ball_alpha = lambda ball = None: 0.4
        self.assertIsNone(self.number_at(3.0))

    def test_under_the_ball_by_the_top_wall(self):
        """Over the ball, unless that would put it off the top of the screen."""
        class Screen:
            def blit(self, surf, rect, *a, **k):
                self.at = rect
        spots = {}
        self.pu.cracker = {"fuse": 3.5, "taker": self.p1}
        for y in (500, 30):
            place(self.ball, 960, y)
            screen = Screen()
            app.renderer.draw_cracker_count(screen, self.game, self.pu, 0, 0)
            spots[y] = screen.at.centery
        self.assertLess(spots[500], 500 - self.ball.height / 2)
        self.assertGreater(spots[30], 30 + self.ball.height / 2)

    def test_shown_in_replays_and_online(self):
        """The joining player and replays draw from the recorded rows, which carry the fuse."""
        self.pu.collect({"kind": "cracker", "x": 900, "y": 500}, self.p1)
        self.pu.update_cracker(1.5)
        for _ in range(3):
            self.game.recorder.capture(1 / 60)
        clip = self.game.recorder.clip()
        view = ReplayView(clip, app)
        view.show(len(clip.frames) - 1)
        self.assertEqual(self.number_at(None, view), 4)

    def test_built_while_loading(self):
        """Its digits are made ahead, so the first one shown mid-rally costs nothing."""
        art = app.art
        for key in [k for k in art.cache if k[0] == "gilded" and k[2] in "12345"]:
            del art.cache[key]
        for job in app.renderer.prewarm_jobs():
            job()
        built = []
        real = art._gilded
        art._gilded = lambda text, *a: built.append(text) or real(text, *a)
        try:
            for fuse in (5.0, 4.0, 3.0, 2.0, 1.0):
                self.number_at(fuse)
        finally:
            art._gilded = real
        self.assertEqual([t for t in built if t in "12345"], [])

if __name__ == "__main__":
    unittest.main()

"""The Firecracker's 5-second fuse, 1.6 (Rowan's playtest list, 2026-11-16).

It used to bang after 3 hits.  Now its fuse is lit when it's taken and burns for 5 seconds of play,
shown burning down on the ball; then it bangs, away from whoever hit the ball last.  It still goes
out without a bang if the point ends first.
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


if __name__ == "__main__":
    unittest.main()

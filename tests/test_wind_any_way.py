"""Wind Gust blows any way, 1.9 (Rowan, phase 3: "change the Wind Gust talisman so that the gusts
of wind aren't just up or down, but in any direction").

Each gust blows at an angle of its own, any of 360 degrees.  As before it turns the ball's path
without speeding it up; now it can also hold the ball back or hurry it on across the court, but it
never tips it steeper than about 70 degrees (where it would bounce between the walls and never
reach a paddle) nor turns it back.  The leaves, the HUD's arrow and its words, the AI's reckoning,
and replays (and the friend's screen online, which uses the same rows) all follow the way it blows.
"""
import math
import random
import unittest

from tests import harness

app = harness.app()

from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import PowerUps                              # noqa: E402
from game.replay import ReplayView                              # noqa: E402

m = app.settings.match
DT = 1 / 60


class Wind(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        m.reset()
        self.game = g = Hu_Taong(app)
        g.start()
        g.countdown, g.paused = None, False
        self.pu = g.powerups
        self.pu.wait = 999.0
        g.p1.ai_enabled = g.p2.ai_enabled = False

    def tearDown(self):
        self.game.stop()
        m.reset()

    def blow(self, angle):
        self.pu.collect({"kind": "wind", "x": 900, "y": 500}, self.game.p1)
        self.pu.wind["angle"], self.pu.wind["t"], self.pu.wind["left"] = angle, math.pi / 2 / 2.3, 5.0

    def test_any_way_at_all(self):
        angles = []
        for _ in range(60):
            self.pu.wind = None
            self.pu.collect({"kind": "wind", "x": 900, "y": 500}, self.game.p1)
            angles.append(self.pu.wind["angle"])
        quarters = {int((a % math.tau) // (math.pi / 2)) for a in angles}
        self.assertEqual(quarters, {0, 1, 2, 3}, "not just up or down")
        self.blow(0.0)
        wx, wy = self.pu.wind_vector()
        self.assertAlmostEqual(wx, PowerUps.WIND, delta = 1)
        self.assertAlmostEqual(wy, 0.0, delta = 1)

    def test_words(self):
        way = PowerUps.wind_way
        self.assertEqual(way(math.pi / 2), "down")
        self.assertEqual(way(-math.pi / 2), "up")
        self.assertEqual(way(0.0), "right")
        self.assertEqual(way(math.pi), "left")
        self.assertEqual(way(-3 * math.pi / 4), "up and to the left")
        self.blow(math.pi / 4)
        texts = [text for key, _, text in self.pu.court_list() if key == "wind"]
        self.assertEqual(texts, ["Wind blowing down and to the right"])

    def test_it_bends_the_path_but_keeps_the_speed(self):
        self.blow(math.pi / 2 + 0.3)                                     # down, a little to the left
        b = self.game.ball
        b.vx, b.vy = 900.0, -200.0
        speed = math.hypot(b.vx, b.vy)
        for _ in range(30):
            self.pu.update_flight(DT)
        self.assertAlmostEqual(math.hypot(b.vx, b.vy), speed, delta = 1)
        self.assertGreater(b.vy, -200.0, "bent the way it blows")

    def test_a_headwind_never_turns_it_back_or_sends_it_up_the_court(self):
        self.blow(math.pi + 0.2)                                         # against a ball going right
        b = self.game.ball
        b.vx, b.vy = 500.0, 400.0
        for _ in range(int(10 / DT)):
            self.pu.wind["left"] = 5.0                                   # (blowing all the while)
            self.pu.update_flight(DT)
            self.assertGreater(b.vx, 0, "never turned back")
            speed = math.hypot(b.vx, b.vy)
            self.assertGreaterEqual(b.vx, PowerUps.WIND_ACROSS * speed - 1, "never steeper than ~70 degrees")

    def test_the_ai_reads_it(self):
        """With a sideways wind, the AI still sees where the ball will cross its line."""
        self.blow(math.pi / 2 + 0.6)
        g = self.game
        g.p2.ai_enabled = True
        b = g.ball
        b.x0, b.x1 = 900 - b.width / 2, 900 + b.width / 2
        b.y0, b.y1 = 300 - b.width / 2, 300 + b.width / 2
        b.vx, b.vy = 1100.0, 0.0
        path = self.pu.hole_path(900, 300, 1100.0, 0.0, b.width / 2, g.p2.x0, 1.0, self.pu.wind_vector())
        self.assertIsNotNone(path)
        self.assertGreater(path[1], 300, "it bends down on the way")

    def test_a_replay_shows_it(self):
        self.blow(math.pi + 0.5)                                         # left and up
        rec = self.game.recorder
        for _ in range(20):
            self.game.update(DT)
            rec.capture(DT)
        view = ReplayView(rec.clip(), app)
        view.show(len(view.clip.frames) - 1 if hasattr(view, "clip") else 10)
        wx, wy = view.powerups.wind_vector()
        self.assertLess(wx, -50)
        self.assertLess(wy, -50)

    def test_the_leaves_and_arrow_draw(self):
        self.blow(2.4)
        app.renderer.draw_wind(app.virtual, self.pu)
        self.assertTrue(app.renderer._leaves)
        from core.states.game_state import GameState
        app.hud.draw(GameState(app), app.virtual, self.game)
        self.assertAlmostEqual(app.hud._wind_way, 2.4, delta = 0.01)


if __name__ == "__main__":
    unittest.main()

"""Talismans fade out, 1.8 (Rowan's 1.8 plan, phase 2, 2026-11-18).

Lantern Night, Wind Gust and any other talisman with a big effect on the court fade out smoothly
when they end, rather than cutting straight back to normal: the night lifts into dawn, the wind dies
down over 1.5 s, a Ghost Ball fades back into sight, closing portals shrink away, Shape Shift's
sizes ease back, Sticky Goo's coat fades off the paddles and Open Court's wall fades back in.
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


class Match(unittest.TestCase):
    def setUp(self):
        random.seed(3)
        m.reset()
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.pu = self.game.powerups
        self.pu.wait = 999.0
        self.game.p1.ai_enabled = self.game.p2.ai_enabled = False

    def tearDown(self):
        self.game.stop()
        m.reset()

    def take(self, key):
        self.pu.collect({"kind": key, "x": 900, "y": 500}, self.game.p1)


class OnTheCourt(Match):
    def test_lantern_night_lifts_into_dawn(self):
        self.take("lantern")
        self.pu.lantern["age"] = 5.0
        self.pu.lantern["left"] = 0.01
        self.pu.update(DT)
        levels = []
        for _ in range(80):
            self.pu.update_popups(DT)
            levels.append(self.pu.lantern_level())
        self.assertTrue(any(0.2 < v < 0.8 for v in levels), "it lifts gradually")
        self.assertEqual(levels[-1], 0.0)

    def test_the_wind_dies_down(self):
        self.take("wind")
        self.pu.wind["t"], self.pu.wind["left"] = 0.0, 5.0              # (at full strength)
        full = math.hypot(*self.pu.wind_vector())                       # (any way, 1.9)
        self.pu.wind["left"] = PowerUps.WIND_DIES / 2
        self.assertAlmostEqual(math.hypot(*self.pu.wind_vector()), full / 2, delta = full * 0.05)
        self.pu.wind["left"] = 0.05
        self.assertLess(math.hypot(*self.pu.wind_vector()), full * 0.05)

    def test_a_ghost_ball_fades_back_in(self):
        self.take("ghost")
        self.pu.ghost["alpha"], self.pu.ghost["left"] = 0.0, 0.01
        seen = []
        for _ in range(30):
            if not self.pu.ghost:
                break
            self.pu.update_ghost(DT)
            seen.append(self.pu.ball_alpha())
        self.assertTrue(any(0.1 < a < 0.9 for a in seen), "not straight back")
        self.assertIsNone(self.pu.ghost)
        self.assertEqual(self.pu.ball_alpha(), 1.0)

    def test_closing_portals_shrink_away(self):
        self.pu.open_portals()
        self.pu.close_portals()
        self.assertEqual(self.pu.portals, [])
        self.assertEqual(len(self.pu.closing), 2)
        for _ in range(3):
            self.game.recorder.capture(DT)
        view = ReplayView(self.game.recorder.clip(), app)
        view.show(len(view.clip.frames) - 1)
        self.assertEqual((len(view.powerups.portals), len(view.powerups.closing)), (0, 2), "in replays too")
        app.renderer.draw_world(app.virtual, view)
        for _ in range(round(PowerUps.PORTAL_SHUT / DT) + 2):
            self.pu.update_popups(DT)
        self.assertEqual(self.pu.closing, [])

    def test_the_talismans_portals_shrink_away_at_the_points_end(self):
        self.pu.open_portals()
        self.pu.on_point()
        self.assertEqual(len(self.pu.closing), 2)

    def test_shape_shifts_sizes_ease_back(self):
        g = self.game
        self.take("shape")
        for obj in (g.p1, g.p2, g.ball):
            obj.drift["size"][0] = obj.drift["size"][1] = 1.0           # as big as they go
        g.apply_gameplay_settings()
        big = g.p1.height
        normal = m.paddle_height
        g.on_score(g.ball, {"normal": (1, 0)})
        heights = []
        while g.message_timer > 0:
            g.update(DT)
            heights.append(g.p1.height)
        self.assertGreater(heights[0], normal + 20, "not snapped back")
        self.assertTrue(any(normal + 5 < h < big - 5 for h in heights), "eased")
        self.assertAlmostEqual(heights[-1], normal, delta = 1)
        self.assertAlmostEqual(g.p1.height, normal, delta = 1)


class Drawn(Match):
    def test_goo_fades_off_the_paddles(self):
        g, r = self.game, app.renderer
        self.take("sticky")
        app.dt = DT
        for _ in range(5):
            r.draw_world(app.virtual, g)
        g.p1.effects.pop("sticky")
        g.p2.effects.pop("sticky")
        built = []
        real = app.art.get
        app.art.get = lambda key, *a: (built.append(key[0]), real(key, *a))[1]
        try:
            for _ in range(5):
                r.draw_world(app.virtual, g)
        finally:
            app.art.get = real
        self.assertIn("goo_fade", built, "the coat fades off")
        for _ in range(40):
            r.draw_world(app.virtual, g)
        self.assertEqual(r._fades[("goo", True)], 0.0)

    def test_open_courts_wall_fades_back(self):
        g, r = self.game, app.renderer
        app.dt = DT
        self.take("wall")
        for _ in range(40):
            r.draw_world(app.virtual, g)
        self.assertEqual(r._fades["cord"], 0.0)
        self.pu.on_point()
        r.draw_world(app.virtual, g)
        self.assertTrue(0.0 < r._fades["cord"] < 0.2, "on its way back")


if __name__ == "__main__":
    unittest.main()

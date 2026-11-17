"""Shape Shift, 1.6 (Rowan's playtest, 2026-11-17).

The Chaos Mode + talisman is now Shape Shift: for the rest of the point the paddles and the ball
drift bigger and smaller, each on its own, but their speeds no longer drift.  Everything is back to
normal for the next serve.  The Chaos Mode + setting is unchanged (sizes and speeds).  Saves and
replays from before, which call it "chaos", still load, and know it as Shape Shift.
"""
import json
import os
import unittest

from tests import harness

app = harness.app()

from core import save_data                                      # noqa: E402
from game.powerups import BY_KEY, UNTIL_POINT                   # noqa: E402
from game.replay import KIND_KEYS, Clip, ReplayView             # noqa: E402
from render.hud import SHORT                                    # noqa: E402
from tests.test_powerup_fixes import Match, place               # noqa: E402

DT = 1 / 60


class Named(unittest.TestCase):
    def test_shape_shift_not_chaos_mode_plus(self):
        kind = BY_KEY["shape"]
        self.assertEqual(kind.name, "Shape Shift")
        self.assertEqual(kind.glyph, "变")
        self.assertNotIn("chaos", BY_KEY)
        self.assertIn("growing and shrinking", kind.blurb)
        self.assertIn("Speeds stay as they are", kind.about)
        self.assertNotIn("faster", kind.about)
        self.assertEqual(SHORT["shape"], "Sizes drifting")

    def test_its_icon_is_drawn(self):
        icon = app.art.power_icon(64, "shape", "Wild")
        self.assertGreater(icon.get_width(), 0)


class Drifting(Match):
    def setUp(self):
        super().setUp()
        self.s = self.game.settings
        self.was_mode = self.s.chaos_mode
        self.s.chaos_mode = 0
        place(self.ball, 960, 540)
        self.ball.vx, self.ball.vy = 500.0, 300.0

    def tearDown(self):
        self.s.chaos_mode = self.was_mode
        super().tearDown()

    def drift(self, seconds):
        """Seconds of drift, every frame's sizes and speeds as play would set them."""
        seen = []
        for _ in range(int(seconds / DT)):
            self.game.update_drift(DT)
            self.game.apply_gameplay_settings()
            seen.append((self.p1.height, self.p2.height, self.ball.diameter,
                         self.p1.speed, self.p2.speed, self.ball.speed, (self.ball.vx, self.ball.vy)))
        return seen

    def test_sizes_drift_speeds_dont(self):
        self.pu.collect({"kind": "shape", "x": 900, "y": 500}, self.p1)
        seen = self.drift(8.0)
        for i, name in enumerate(("Red's paddle", "Blue's paddle", "the ball")):
            sizes = [f[i] for f in seen]
            self.assertGreater(max(sizes) - min(sizes), 10, f"{name} kept its size")
        self.assertEqual({f[3] for f in seen} | {f[4] for f in seen}, {self.s.paddle_speed})
        self.assertEqual({f[5] for f in seen}, {self.s.ball_speed})
        self.assertEqual({f[6] for f in seen}, {(500.0, 300.0)}, "the ball in play kept its speed")

    def test_shown_until_the_point_ends(self):
        self.pu.collect({"kind": "shape", "x": 900, "y": 500}, self.p1)
        self.assertIn(("shape", UNTIL_POINT, "Shape Shift: sizes drifting"), self.pu.court_list())

    def test_back_to_normal_for_the_next_serve(self):
        self.pu.collect({"kind": "shape", "x": 900, "y": 500}, self.p1)
        self.drift(5.0)
        self.pu.on_point()
        self.game.apply_gameplay_settings()
        self.assertEqual((self.p1.height, self.p2.height), (self.s.paddle_height, self.s.paddle_height))
        self.assertEqual(self.ball.diameter, self.s.ball_diameter)
        self.assertNotIn("shape", [k for k, _, _ in self.pu.court_list()])
        seen = self.drift(2.0)
        self.assertEqual({f[0] for f in seen}, {self.s.paddle_height}, "no more drifting")

    def test_the_chaos_mode_plus_setting_still_drifts_speeds_too(self):
        self.s.chaos_mode = 2
        self.game.reset_drift()
        seen = self.drift(8.0)
        speeds = [f[3] for f in seen]
        self.assertGreater(max(speeds) - min(speeds), 10)
        self.assertFalse(self.pu.spawnable(BY_KEY["shape"]), "no Shape Shift on top of Chaos Mode +")

    def test_recorded_for_replays_and_online(self):
        """The friend's screen and replays draw the host's sizes from the rows."""
        self.pu.collect({"kind": "shape", "x": 900, "y": 500}, self.p1)
        self.drift(3.0)
        for _ in range(3):
            self.game.recorder.capture(DT)
        view = ReplayView(self.game.recorder.clip(), app)
        view.show(len(view.clip.frames) - 1)
        self.assertAlmostEqual(view.p1.height, self.p1.height, delta = 0.5)
        self.assertAlmostEqual(view.ball.width, self.ball.diameter, delta = 0.5)
        self.assertIn("shape", [item[0] for item in view.powerups.court_list()])


class OldFiles(unittest.TestCase):
    def tearDown(self):
        app.settings.gameplay.pu_shape = True

    def load_gameplay(self, saved):
        data = save_data.collect(app)
        data["gameplay"] = saved
        save_data.save_path().parent.mkdir(parents = True, exist_ok = True)
        save_data.save_path().write_text(json.dumps(data))
        app.settings.gameplay.pu_shape = True
        save_data.load(app)

    def test_an_old_save_keeps_the_talisman_switched_off(self):
        self.load_gameplay({"pu_chaos": False})
        self.assertFalse(app.settings.gameplay.pu_shape)
        self.load_gameplay({"pu_chaos": True})
        self.assertTrue(app.settings.gameplay.pu_shape)

    def test_saved_under_its_new_name(self):
        app.settings.gameplay.pu_shape = False
        data = save_data.collect(app)
        self.assertIs(data["gameplay"]["pu_shape"], False)
        self.assertNotIn("pu_chaos", data["gameplay"])

    def test_the_released_1_6_replay_knows_it_as_shape_shift(self):
        clip = Clip.load(os.path.join(harness.GAME, "tests", "data", "replay_1.6_gravity_frost.htreplay"))
        self.assertIsNotNone(clip)
        old = clip.info["kinds"].index("chaos")
        self.assertEqual(KIND_KEYS[clip.info["remap"][old]], "shape")
        view = ReplayView(clip, app)
        self.assertEqual(view.kind(old), "shape")


if __name__ == "__main__":
    unittest.main()

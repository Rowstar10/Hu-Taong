"""Game modes, 1.7 (Rowan's 1.7 plan, 2026-11-17).

Chaos (Every point: new sizes and speeds each point, fixed through the rally; Constant drift: see
test_shape_shift), Curveball and Lantern Night for the whole match, Twin Ball (two balls every
point, under the Twin Balls rules) and Talisman Rush (talismans much more often).  A talisman that
would do what a mode already does doesn't turn up while it's on.
"""
import math
import unittest

from tests import harness

app = harness.app()

from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import BY_KEY, PowerUps                      # noqa: E402
from game.replay import ReplayView                              # noqa: E402

m = app.settings.match
DT = 1 / 120


class ModeMatch(unittest.TestCase):
    MODES = {}

    def setUp(self):
        m.reset()
        for name, value in self.MODES.items():
            setattr(m, name, value)
        app.keys_down.clear()
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.pu = self.game.powerups
        self.pu.wait = 999.0
        self.rules = self.game.settings          # the match's own copy of the rules

    def tearDown(self):
        self.game.stop()
        m.reset()

    def score_point(self):
        """A goal for Blue straight away, then on to the next serve."""
        g = self.game
        g.on_score(g.ball, {"normal": (1, 0)})
        g.message_timer = 0.001
        g.update(0.01)


class TwinBall(ModeMatch):
    MODES = {"mode_twin_ball": True}

    def balls(self):
        return {b.side: b for b in self.pu.balls()}

    def test_both_balls_from_the_first_serve(self):
        balls = self.balls()
        self.assertEqual(set(balls), {"red", "blue"})
        self.assertGreater(balls["red"].vx, 0, "red heads for Blue's goal, where it can score")
        self.assertLess(balls["blue"].vx, 0, "blue for Red's")
        self.assertEqual(sum(1 for o in self.game.objects if o.is_ball), 2)

    def test_and_every_point_after(self):
        for _ in range(3):
            self.score_point()
            self.assertEqual(set(self.balls()), {"red", "blue"})
            self.assertEqual(sum(1 for o in self.game.objects if o.is_ball), 2, "the old blue ball is gone")

    def test_the_blue_ball_scores_in_reds_goal(self):
        g, blue = self.game, self.balls()["blue"]
        g.p1.y0, g.p1.y1 = 0, g.p1.height                     # Red's paddle out of the way, up top
        blue.x0, blue.x1 = 300, 300 + blue.width
        blue.y0, blue.y1 = 800, 800 + blue.height
        blue.vx, blue.vy = -1500.0, 0.0
        for _ in range(int(1.0 / DT)):
            g.update(DT)
            if g.message_text:
                break
        self.assertEqual((g.p1.score, g.p2.score), (0, 1))

    def test_served_at_the_usual_pace(self):
        for b in self.pu.balls():
            self.assertAlmostEqual(math.hypot(b.vx, b.vy), m.ball_speed * math.sqrt(2), delta = 1)

    def test_no_twin_balls_talisman(self):
        self.assertFalse(self.pu.spawnable(BY_KEY["twin"]))

    def test_in_replays(self):
        for _ in range(3):
            self.game.recorder.capture(1 / 60)
        view = ReplayView(self.game.recorder.clip(), app)
        view.show(len(view.clip.frames) - 1)
        self.assertEqual(len(view.extra_balls), 1)


class TalismanRush(ModeMatch):
    MODES = {"mode_talisman_rush": True, "powerups": False}

    def test_talismans_even_with_power_ups_off(self):
        self.assertTrue(self.pu.kinds())

    def test_always_chaotic(self):
        """(1.9, Rowan: CHAOS, as it's called now, spawns at Chaotic's 1.5-3 s whatever Spawn says;
        as Talisman Rush it made the rate set three times as often.)"""
        lo, hi = PowerUps.WAITS[PowerUps.CHAOTIC]
        self.assertEqual((lo, hi), (1.5, 3))
        for rate in range(len(m.powerup_rate_options)):
            self.rules.powerup_rate = rate
            waits = [self.pu.next_wait() for _ in range(200)]
            self.assertLessEqual(max(waits), hi + 1e-9)
            self.assertGreaterEqual(min(waits), lo - 1e-9)

    def test_as_many_at_once_as_come(self):
        """(1.8: Talismans at Once sets a limit, 1 to 3; Talisman Rush lifts it.)"""
        self.rules.powerup_rate = 0
        self.assertEqual(self.rules.talisman_limit, float("inf"))

    def test_without_it_power_ups_off_means_none(self):
        self.rules.mode_talisman_rush = False
        self.assertEqual(self.pu.kinds(), [])


class ChaosEveryPoint(ModeMatch):
    MODES = {"mode_chaos": True, "chaos_timing": 0}

    def sizes_and_speeds(self):
        g = self.game
        return (g.p1.height, g.ball.diameter, g.p1.speed, g.ball.speed)

    def test_new_sizes_and_speeds_each_point_fixed_through_the_rally(self):
        seen = set()
        for _ in range(4):
            self.score_point()
            now = self.sizes_and_speeds()
            seen.add(now)
            g = self.game
            g.countdown, g.paused = None, False
            for _ in range(60):
                g.update(DT)
                self.assertEqual(self.sizes_and_speeds(), now, "changed mid-rally")
        self.assertGreater(len(seen), 1, "the same every point")

    def test_your_own_settings_are_never_touched(self):
        """1.7: the sizes and speeds are rolled into the match's own copy of the rules (1.6 rolled
        them into yours, and put yours back when the match ended)."""
        mine = {k: getattr(m, k) for k in ("ball_speed", "ball_diameter", "paddle_speed", "paddle_height")}
        rolled = set()
        for _ in range(3):
            self.score_point()
            rolled.add(self.game.settings.ball_speed)
            self.assertEqual({k: getattr(m, k) for k in mine}, mine)
        self.assertNotEqual(rolled, {mine["ball_speed"]})


class WholeMatchTalismans(ModeMatch):
    def test_curveball_and_lantern_night_modes(self):
        self.rules.mode_curveball = self.rules.mode_lantern_night = True
        self.assertTrue(self.pu.curving())
        self.assertEqual(self.pu.lantern_level(), 1.0)
        self.assertFalse(self.pu.spawnable(BY_KEY["curve"]))
        self.assertFalse(self.pu.spawnable(BY_KEY["lantern"]))

    def test_texts_say_which_mode(self):
        for key, mode in (("curve", "Curveball"), ("lantern", "Lantern Night"), ("twin", "Twin Ball"),
                          ("shape", "Shape Shift"), ("swap", "Soul Swap")):
            self.assertIn(f"in a {mode} match", BY_KEY[key].about)


if __name__ == "__main__":
    unittest.main()

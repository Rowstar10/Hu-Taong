"""The settings regrouped, and game modes, 1.7 (Rowan's 1.7 plan, 2026-11-17).

What changes the match for both players is a Match setting; the rest is each player's own:
Gameplay (the keys, Auto-Pause, touch), Display (now with the effects, shake and trail) and
Interface (menus, the HUD, tooltips).  Chaos Mode, Chaos Switch, Curveball and Lantern Night became
game modes, any of them together, with Chaos and Switch each at a timing.

The save file keeps 1.6's sections and still writes 1.6's names for the modes, so 1.6 and 1.7 can
share it (every version uses the one save).
"""
import json
import os
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from core import save_data                                      # noqa: E402

s = app.settings


def load_file(data):
    save_data.save_path().parent.mkdir(parents = True, exist_ok = True)
    save_data.save_path().write_text(json.dumps(data))
    for group in (s.match, s.gameplay, s.display, s.interface):
        group.reset()
    save_data.load(app)


class Groups(unittest.TestCase):
    def test_each_setting_where_the_design_rules_put_it(self):
        where = {"match": ["ball_speed", "paddle_height", "pace", "winning_score_index", "win_by_two",
                           "middle_wall", "ai_difficulty", "ai_style", "adaptive_ai", "court", "powerups",
                           "powerup_rate", "pu_fire", "countdown", "mode_chaos", "chaos_timing", "mode_switch",
                           "switch_timing", "mode_curveball", "mode_lantern_night", "mode_twin_ball",
                           "mode_talisman_rush", "mode_black_hole"],
                 "gameplay": ["p1_up", "p2_right", "auto_pause", "touch_steer", "touch_sensitivity", "vibration"],
                 "display": ["max_fps", "dim", "court_dim_level", "effects", "screen_shake", "ball_trail"],
                 "interface": ["tooltips", "ai_banter", "hud", "instant_replay", "hide_cursor"]}
        for group, names in where.items():
            for name in names:
                self.assertIs(s.group_of(name), getattr(s, group), f"{name} should be in {group}")

    def test_no_name_in_two_groups(self):
        seen = {}
        for group in ("match", "gameplay", "display", "audio", "interface"):
            for name in vars(getattr(s, group)):
                if name != "app":
                    self.assertNotIn(name, seen, f"{name} is in {seen.get(name)} and {group}")
                    seen[name] = group

    def test_the_old_chaos_settings_are_gone(self):
        for name in ("chaos_mode", "chaos_switch", "curveball", "lantern_night"):
            self.assertIsNone(s.group_of(name))


class Modes(unittest.TestCase):
    def tearDown(self):
        s.match.reset()

    def test_off_by_default(self):
        s.match.reset()
        self.assertEqual(s.match.modes_on(), [])

    def test_timings(self):
        m = s.match
        m.mode_chaos, m.chaos_timing = True, 0
        self.assertTrue(m.chaos_each_point)
        self.assertFalse(m.chaos_drift)
        m.chaos_timing = 1
        self.assertTrue(m.chaos_drift)
        m.mode_chaos = False
        self.assertFalse(m.chaos_drift, "a timing does nothing while its mode is off")
        m.mode_switch = True
        for timing, each, mid in ((0, True, False), (1, False, True)):
            m.switch_timing = timing
            self.assertEqual((m.switch_each_point, m.switch_mid_rally), (each, mid))

    def test_any_together(self):
        m = s.match
        for mode in m.MODES:
            setattr(m, "mode_" + mode, True)
        self.assertEqual(m.modes_on(), list(m.MODES))

    def test_talisman_rush_brings_talismans(self):
        s.match.powerups = False
        self.assertFalse(s.match.talismans_on)
        s.match.mode_talisman_rush = True
        self.assertTrue(s.match.talismans_on)


class OldSaves(unittest.TestCase):
    def tearDown(self):
        s.match.reset()
        s.gameplay.reset()

    def released(self):
        with open(os.path.join(harness.GAME, "tests", "data", "save_1.6.json"), encoding = "utf-8") as f:
            return json.load(f)

    def test_the_released_1_6_save_loads(self):
        data = self.released()
        data["interface"]["p1_up"] = pygame.K_i
        data["interface"]["countdown"] = 2
        data["interface"]["effects"] = 1
        load_file(data)
        self.assertEqual(s.gameplay.p1_up, pygame.K_i, "its keys")
        self.assertEqual(s.match.serve_seconds, 1, "its serve countdown")
        self.assertEqual(s.display.effects, 1, "its effects")
        self.assertEqual(s.match.modes_on(), [])

    def test_its_chaos_settings_become_modes(self):
        cases = [({"chaos_mode": 1}, ("chaos", 0)), ({"chaos_mode": 2}, ("chaos", 1)),
                 ({"chaos_switch": 1}, ("switch", 0)), ({"chaos_switch": 2}, ("switch", 1)),
                 ({"chaos_switch": 3}, ("switch", 1))]          # 1.6's "Chaos Switch & +": Mid-rally (no Both since 1.7)
        for old, (mode, timing) in cases:
            with self.subTest(old = old):
                data = self.released()
                data["gameplay"].update(old)
                load_file(data)
                self.assertEqual(s.match.modes_on(), [mode])
                self.assertEqual(getattr(s.match, mode + "_timing"), timing)
        data = self.released()
        data["gameplay"].update(curveball = True, lantern_night = True)
        load_file(data)
        self.assertEqual(s.match.modes_on(), ["curveball", "lantern_night"])

    def test_nonsense_is_ignored(self):
        data = self.released()
        data["gameplay"].update(chaos_mode = 7, chaos_switch = True, curveball = "yes")
        load_file(data)
        self.assertEqual(s.match.modes_on(), [])


class SharedWith1_6(unittest.TestCase):
    """1.6 reads the same file: what 1.7 writes keeps 1.6's sections and names."""

    def tearDown(self):
        s.match.reset()
        s.gameplay.reset()

    def test_written_where_1_6_looks(self):
        s.match.mode_switch, s.match.switch_timing = True, 1
        s.match.mode_lantern_night = True
        data = save_data.collect(app)
        self.assertEqual(data["gameplay"]["chaos_switch"], 2)
        self.assertEqual(data["gameplay"]["chaos_mode"], 0)
        self.assertIs(data["gameplay"]["lantern_night"], True)
        for name in ("p1_up", "auto_pause", "countdown", "effects", "screen_shake", "ball_trail"):
            self.assertIn(name, data["interface"])

    def test_round_trip(self):
        m = s.match
        m.mode_chaos, m.chaos_timing, m.mode_twin_ball, m.mode_talisman_rush = True, 1, True, True
        s.gameplay.bind("p2_up", pygame.K_o)
        save_data.save(app)
        m.reset()
        s.gameplay.reset()
        save_data.load(app)
        self.assertEqual(m.modes_on(), ["chaos", "twin_ball", "talisman_rush"])
        self.assertEqual(m.chaos_timing, 1)
        self.assertEqual(s.gameplay.p2_up, pygame.K_o)

    def test_the_new_names_win(self):
        """Written by 1.7, both are there: the modes, not 1.6's names, are read back."""
        data = save_data.collect(app)
        data["gameplay"].update(mode_chaos = False, chaos_mode = 2)
        load_file(data)
        self.assertFalse(s.match.mode_chaos)


if __name__ == "__main__":
    unittest.main()

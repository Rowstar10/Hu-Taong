"""Menu order, defaults and labels, 1.9 (Rowan's list, 2026-11-20).

- Achievements sits next to Replays on Stats; the Controls card is to the right of UI.
- Defaults: Court Dim 50%, a controller steers with either stick, the Speed Cap on.
- Show Ping, right below Show FPS: online, in a match, the round trip, for the host as well as the
  friend who joined (only the friend saw it before, always).
- Points to Win's tip lists every option and marks the one in use, as the other tips do.
- Shape Shift's and Soul Swap's off is "OFF", in capitals as every switch; so is Practice's scoring.
- "Practice vs AI" is "Practice Mode", and "vs Human" is "Multiplayer".
"""
import unittest

from tests import harness

app = harness.app()

from render.renderer import TIPS                                # noqa: E402
from tests.test_settings_menus import open_screen               # noqa: E402

s = app.settings


def texts(screen):
    """Every button's words on a screen, as drawn."""
    seen = []
    real = app.renderer.text

    def spy(surface, text, *a, **k):
        seen.append(text)
        return real(surface, text, *a, **k)
    app.renderer.text = spy
    try:
        screen.draw(app.virtual)
    finally:
        del app.renderer.text
    return seen


class Order(unittest.TestCase):
    def test_achievements_next_to_replays(self):
        boxes = open_screen("stats").ui_hitboxes
        replays, achievements = boxes["open_replays"], boxes["open_achievements"]
        self.assertLess(replays.left, achievements.left)
        self.assertEqual(replays.centery, achievements.centery, "side by side")
        # (the others left the panel for the footer after 1.9's release: tests/test_back_bottom_left.py)

    def test_controls_to_the_right_of_ui(self):
        boxes = open_screen("settings").ui_hitboxes
        self.assertGreater(boxes["gameplay"].left, boxes["interface"].left)
        self.assertEqual(max(boxes[k].left for k in ("display", "audio", "interface", "gameplay")),
                         boxes["gameplay"].left, "the last card")


class Defaults(unittest.TestCase):
    def setUp(self):
        app.reset_all_settings()

    def test_the_new_defaults(self):
        self.assertEqual(s.display.court_dim_level, 0.5)
        self.assertEqual(s.gameplay.PAD_STICKS[s.gameplay.pad_stick], "Either stick")
        self.assertTrue(s.match.speed_cap)
        self.assertTrue(s.display.show_ping)

    def test_show_ping_below_show_fps(self):
        boxes = open_screen("display").ui_hitboxes
        self.assertGreater(boxes["toggle_show_ping"].top, boxes["toggle_show_fps"].bottom - 1)
        self.assertLess(boxes["toggle_show_ping"].top - boxes["toggle_show_fps"].bottom, 40, "right below it")

    def test_ping_shows_for_host_and_guest_in_a_match(self):
        from types import SimpleNamespace
        drawn = []
        real = app.renderer.draw_ping
        app.renderer.draw_ping = lambda screen, ping: drawn.append(ping)
        sm = app.state_manager
        try:
            sm.set_state("main_menu", mute = True)
            sm.push_state("game", mute = True)
            harness.settle(app)
            app.net = SimpleNamespace(ping = 0.05)          # (no network: just a ping to show)
            app.show_ping()
            self.assertIn(0.05, drawn)
            drawn.clear()
            s.display.show_ping = False
            app.show_ping()
            self.assertEqual(drawn, [], "off: not shown")
        finally:
            app.net = None
            app.renderer.draw_ping = real
            s.display.show_ping = True
            sm.set_state("main_menu", mute = True)
            harness.settle(app)


class Labels(unittest.TestCase):
    def setUp(self):
        app.reset_all_settings()

    def test_points_to_win_tip_lists_them_all(self):
        """(Read as the screen offers it, with the menus' highlight resting on the setting.)"""
        nav = app.navigator
        screen = open_screen("match")
        nav.snapshot()
        nav.active, nav.via, nav.key = True, "keys", "cycle_win_score_left"
        try:
            screen.draw(app.virtual)
            tip = app.renderer.tips.offered
        finally:
            nav.active, nav.key = False, None
        m = s.match
        self.assertTrue(tip and tip.startswith("Points to Win\n"), tip)
        for v in m.winning_scores:
            self.assertIn("Endless Mode" if v == "Endless Mode" else f"First to {v}", tip)
        self.assertIn(f"» First to {m.winning_scores[m.winning_score_index]}", tip, "the one in use marked")

    def test_off_in_capitals(self):
        from tests.test_settings_menus import open_modes
        drawn = texts(open_modes())                 # (the modes: Choose Modes' page, later in 1.9)
        self.assertIn("Shape Shift: OFF", drawn)
        self.assertIn("Soul Swap: OFF", drawn)
        self.assertNotIn("Shape Shift: Off", drawn)

    def test_practice_mode_and_multiplayer(self):
        drawn = texts(open_screen("match_setup"))
        self.assertIn("Practice Mode", drawn)     # (Rowan tried "Practice", and went back: "I do prefer it
        self.assertIn("Multiplayer", drawn)       # when it's called practice mode")
        self.assertNotIn("Practice vs AI", drawn)
        self.assertNotIn("vs Human", drawn)
        self.assertTrue(TIPS["opponent_ai"].startswith("Practice Mode\n"))
        self.assertTrue(TIPS["opponent_human"].startswith("Multiplayer\n"))


if __name__ == "__main__":
    unittest.main()

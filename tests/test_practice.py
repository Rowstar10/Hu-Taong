"""Practice vs AI, 1.9 (Rowan's 1.9 plan, phase 2, step 8; folded into vs AI after Rowan's test).

First it was a mode of its own beside vs AI and vs Human, with a talisman picker.  Rowan, testing
phase 3 (2026-11-20): "Combine vs AI and practice into one thing.  The only thing that needs to stay
from practice is the AI/wall toggle and the scoring on/off toggle.  Selecting only one talisman
feels too restrictive for a sandbox mode ... delete the entire practice game mode, rename "vs AI"
to "Practice vs AI", and add the two toggles."  So Practice vs AI has Against (AI or Wall) and
Scoring (On or Off).  Against the AI with scoring on it's the old vs AI, a real match that counts;
against the wall or with scoring off it's practice, which counts for nothing.  Against the wall,
the other end of the court is a wall (the other paddle sits out), so the ball always comes back;
with scoring on it counts your misses and never ends.  Online, a host's own choices are ignored.
"""
import json
import unittest

from tests import harness

app = harness.app()

from config import BASE_W                                       # noqa: E402
from core import save_data                                      # noqa: E402
from core.states.game_state import GameState                    # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.replay import ReplayView                              # noqa: E402
from tests.test_settings_menus import click, open_screen        # noqa: E402

m = app.settings.match


def practice(**rules):
    m.reset()
    m.vs_ai = True
    for name, value in rules.items():
        setattr(m, name, value)
    g = Hu_Taong(app)
    g.start()
    g.countdown, g.paused = None, False
    return g


def send(g, x, vx, y = 540.0):
    b, r = g.ball, g.ball.width / 2
    b.x0, b.x1, b.y0, b.y1 = x - r, x + r, y - r, y + r
    b.vx, b.vy = vx, 0.0


def run(g, seconds, until = lambda: False):
    for _ in range(int(seconds * 120)):
        g.update(1 / 120)
        if until():
            return True
    return False


class MatchSetup(unittest.TestCase):
    def tearDown(self):
        m.reset()

    def test_no_practice_mode_and_vs_ai_is_practice_vs_ai(self):
        m.reset()
        screen = open_screen("match_setup")
        self.assertNotIn("opponent_practice", screen.ui_hitboxes, "Practice is no longer a mode of its own")
        self.assertIn("opponent_ai", screen.ui_hitboxes)
        self.assertFalse(any("practice_talisman" in key for key in screen.ui_hitboxes), "no talisman picker")
        self.assertFalse(hasattr(m, "practice") or hasattr(m, "practice_talisman"))
        from render.renderer import TIPS
        self.assertTrue(TIPS["opponent_ai"].startswith("Practice vs AI\n"))
        self.assertNotIn("opponent_practice", TIPS)

    def test_the_two_choices_show_with_practice_vs_ai(self):
        m.reset()
        screen = open_screen("match_setup")
        for key in ("practice_ai", "practice_wall", "practice_scoring_on", "practice_scoring_off"):
            self.assertIn(key, screen.ui_hitboxes)
        self.assertEqual((m.vs_wall, m.scoring), (False, True), "by default, the old vs AI")

    def test_its_choices(self):
        m.reset()
        screen = open_screen("match_setup")
        click(screen, "practice_wall")
        self.assertTrue(m.vs_wall)
        click(screen, "practice_ai")
        self.assertFalse(m.vs_wall)
        click(screen, "practice_scoring_off")
        self.assertFalse(m.scoring)
        click(screen, "practice_scoring_on")
        self.assertTrue(m.scoring)

    def test_greyed_out_for_vs_human(self):
        m.reset()
        m.vs_ai = False
        screen = open_screen("match_setup")
        click(screen, "practice_wall")
        click(screen, "practice_scoring_off")
        self.assertEqual((m.vs_wall, m.scoring), (False, True), "they only matter against the AI")

    def test_saved(self):
        m.reset()
        m.vs_wall, m.scoring = True, False
        gameplay = save_data.collect(app)["gameplay"]
        self.assertEqual((gameplay["vs_wall"], gameplay["scoring"]), (True, False))
        for old in ("practice", "practice_wall", "practice_scoring", "practice_talisman"):
            self.assertNotIn(old, gameplay)


class AgainstTheWall(unittest.TestCase):
    def tearDown(self):
        self.g.stop()
        m.reset()

    def test_the_other_end_is_a_wall(self):
        self.g = g = practice(vs_wall = True, powerups = False)
        self.assertIs(g.bench, g.p2)
        self.assertNotIn(g.p2, g.objects)
        self.assertFalse(g.p1.ai_enabled or g.p2.ai_enabled)
        self.assertEqual(g.p2.controls_label, "Wall")
        self.assertTrue(g.practice)
        send(g, BASE_W - 300, 1400)
        self.assertTrue(run(g, 1.0, lambda: g.ball.vx < 0), "it bounces back")
        self.assertEqual((g.p1.score, g.p2.score), (0, 0))
        self.assertLess(g.ball.x1, BASE_W - Hu_Taong.PRACTICE_WALL + 2)

    def test_on_the_blue_side_the_wall_is_on_the_left(self):
        self.g = g = practice(vs_wall = True, play_as_blue = True, powerups = False)
        self.assertIs(g.bench, g.p1)
        self.assertFalse(g.p2.ai_enabled)

    def test_with_scoring_it_counts_misses_and_never_ends(self):
        self.g = g = practice(vs_wall = True, powerups = False)
        win = m.winning_scores[m.winning_score_index]
        for n in range(1, win + 3):
            g.countdown, g.paused = None, False
            g.message_timer = 0.0
            send(g, 200, -1600, y = 100 if g.p1.y0 > 300 else 980)
            self.assertTrue(run(g, 1.5, lambda: g.p2.score == n), n)
            self.assertEqual(g.message_text, "Missed!")
        self.assertIsNot(app.state_manager.current().__class__.__name__, "WinState")
        self.assertGreater(g.p2.score, win)

    def test_no_swapping_paddles(self):
        self.g = g = practice(vs_wall = True, mode_switch = True, pu_swap = True)
        self.assertFalse(g.settings.mode_switch)
        self.assertNotIn("swap", [k.key for k in g.powerups.kinds()])
        g.reset_round()
        self.assertFalse(g.settings.mode_switch, "and at every serve")

    def test_every_other_talisman_as_set(self):
        self.g = g = practice(vs_wall = True, powerups = True, pu_fire = False)
        kinds = [k.key for k in g.powerups.kinds()]
        self.assertNotIn("fire", kinds)
        self.assertIn("giant", kinds)

    def test_the_ball_never_slips_past_it(self):
        self.g = g = practice(vs_wall = True, powerups = False)
        send(g, BASE_W + 20, 900)
        g.keep_ball_in()
        self.assertEqual((g.p1.score, g.p2.score), (0, 0))
        self.assertLess(g.ball.vx, 0)

    def test_a_replay_shows_the_wall(self):
        self.g = g = practice(vs_wall = True, powerups = False)
        for _ in range(60):
            g.update(1 / 120)
            g.recorder.capture(1 / 120)
        view = ReplayView(g.recorder.clip(), app)
        view.show(0)
        self.assertIs(view.bench, view.p2)
        self.assertNotIn(view.p2, view.objects)


class Scoring(unittest.TestCase):
    def tearDown(self):
        self.g.stop()
        m.reset()

    def test_scoring_off_nobody_scores(self):
        self.g = g = practice(scoring = False, powerups = False)
        self.assertTrue(g.p2.ai_enabled)
        self.assertTrue(g.practice)
        g.p1.y0, g.p1.y1 = 0, g.p1.height
        send(g, 300, -1600, y = 980)
        self.assertTrue(run(g, 1.5, lambda: bool(g.message_text)))
        self.assertEqual((g.p1.score, g.p2.score), (0, 0))
        self.assertIn("not counted", g.message_text)

    def test_against_the_ai_with_scoring_on_is_the_old_vs_ai(self):
        self.g = g = practice(powerups = True)
        self.assertFalse(g.practice, "a real match")
        self.assertIsNone(g.bench)
        self.assertTrue(g.p2.ai_enabled)
        self.assertIn(g.p2, g.objects)

    def test_vs_human_ignores_them(self):
        """(Saved choices from Practice vs AI don't follow you into vs Human.)"""
        self.g = g = practice(vs_ai = False, vs_wall = True, scoring = False, powerups = False)
        self.assertFalse(g.practice or g.scoreless)
        self.assertIsNone(g.bench)
        self.assertFalse(g.p1.ai_enabled or g.p2.ai_enabled)


class WhatCounts(unittest.TestCase):
    def setUp(self):
        app.stats.reset()
        app.achievements.reset()

    def tearDown(self):
        app.stats.reset()
        app.achievements.reset()            # (the real match earns some: leave none behind)
        app.renderer._banners = []
        m.reset()

    def play_to_a_win(self, **rules):
        m.reset()
        for name, value in rules.items():
            setattr(m, name, value)
        m.powerups = False
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        state = sm.current()
        self.assertIsInstance(state, GameState)
        g = state.game
        g.countdown, g.paused = None, False
        g.p1.score = m.winning_scores[m.winning_score_index] - 1
        g.p2.y0, g.p2.y1 = 0, g.p2.height
        send(g, BASE_W - 300, 1600, y = 980)
        for _ in range(240):
            state.update(1 / 120)
            harness.settle(app)
            if sm.current() is not state:
                break
        return sm.current().__class__.__name__

    def test_practice_counts_for_nothing(self):
        """Against the wall the winning shot only bounces back: nothing is won, and nothing counts."""
        before = app.stats.to_dict()
        self.assertEqual(self.play_to_a_win(vs_wall = True), "GameState", "(against the wall it never ends)")
        after = app.stats.to_dict()
        for key in ("matches", "wins_vs_ai", "points", "play_time", "best_rally"):
            self.assertEqual(after[key], before[key], key)
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_a_real_match_still_counts(self):
        before = app.stats.to_dict()
        self.assertEqual(self.play_to_a_win(), "WinState")
        after = app.stats.to_dict()
        self.assertEqual(after["wins_vs_ai"], before["wins_vs_ai"] + 1)
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)


class NotOnline(unittest.TestCase):
    def test_a_host_plays_a_real_match(self):
        """Practice is your own: hosting, the match is a real one whatever you'd picked."""
        from core.net import HostSession
        m.reset()
        m.vs_wall, m.scoring = True, False
        app.net = HostSession(app, port = 0, upnp = False)       # (on this PC only: no public servers)
        try:
            g = Hu_Taong(app)
            g.start()
            self.assertFalse(g.practice or g.scoreless)
            self.assertIsNone(g.bench)
            self.assertIn(g.p2, g.objects)
            g.stop()
        finally:
            app.net.close()
            app.net = None
            m.reset()


class OldSaves(unittest.TestCase):
    def test_a_save_with_the_old_practice_mode_loads(self):
        """A 1.9 test build's save (Practice as a mode) loads: its Practice fields are ignored."""
        path = save_data.save_path()
        kept = path.read_text() if path.exists() else None
        try:
            data = save_data.collect(app)
            data["gameplay"].pop("vs_wall")
            data["gameplay"].pop("scoring")
            data["gameplay"].update(practice = True, practice_wall = True, practice_scoring = False,
                                    practice_talisman = 5)
            path.parent.mkdir(parents = True, exist_ok = True)
            path.write_text(json.dumps(data))
            m.reset()
            save_data.load(app)
            self.assertEqual((m.vs_ai, m.vs_wall, m.scoring), (True, False, True))
            self.assertFalse(hasattr(m, "practice"))
        finally:
            if kept is None:
                path.unlink()
            else:
                path.write_text(kept)
            m.reset()


if __name__ == "__main__":
    unittest.main()

"""Match Setup keeps the rules most matches change, 1.9 (Rowan, 2026-11-20).

Rowan: "it feels a little bit weird being able to access all of these settings that should
normally apply to the game you're in from the main menu."  So the main menu's Settings has no Match
card (it's there in a match, from Pause, for that match only), and Match Setup has the rules most
matches change, with its Match Settings button for the rest.  Which ones, in Rowan's words: who
plays ("definitely"), the court ("definitely"), AI Level ("Yep") and Points to Win; "do not include
goals" and "Definitely not the modes. Move that back into extra settings."

Everything stays changeable mid-match, from the next serve, which brought two fixes:
- A court picked from Pause did nothing (the stones were built once, as the match was made): it
  now comes in at the next serve.
- The achievements took the rules as they stood at the end, so switching to Insane for match
  point won Beat Insane: a match now counts at the easiest it was played at.
"""
import unittest
from types import SimpleNamespace
from unittest import mock

from tests import harness

app = harness.app()

from core.states.win_state import WinState                      # noqa: E402
from game import courts                                         # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.replay import ReplayView                              # noqa: E402
from tests.test_settings_menus import click, open_screen        # noqa: E402

m = app.settings.match


class MatchSetup(unittest.TestCase):
    def setUp(self):
        m.reset()

    def tearDown(self):
        m.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_who_plays_the_court_ai_level_and_points_to_win(self):
        keys = open_screen("match_setup").ui_hitboxes
        for key in ("opponent_ai", "opponent_human", "opponent_online", "side_red", "side_blue", "practice_ai",
                    "practice_wall", "cycle_ai_left", "cycle_win_score_left", "cycle_court_left",
                    "open_match_settings", "start_match"):
            self.assertIn(key, keys)
        self.assertFalse([k for k in keys if "_mode_" in k or "scoring" in k or "goals" in k],
                         "Goals and the modes are in Match Settings")

    def test_ai_level_under_against_and_points_under_your_paddle(self):
        boxes = open_screen("match_setup").ui_hitboxes
        ai = boxes["cycle_ai_left"].union(boxes["cycle_ai_right"])
        points = boxes["cycle_win_score_left"].union(boxes["cycle_win_score_right"])
        against = boxes["practice_ai"].union(boxes["practice_wall"])
        paddle = boxes["side_red"].union(boxes["side_blue"])
        self.assertGreater(ai.top, against.bottom)
        self.assertLess(abs(ai.centerx - against.centerx), 3)
        self.assertLess(abs(points.centerx - paddle.centerx), 3)
        self.assertEqual(ai.width, points.width, "one width")

    def test_they_change_the_rules(self):
        screen = open_screen("match_setup")
        level, points = m.ai_difficulty, m.winning_score_index
        click(screen, "cycle_ai_right")
        click(screen, "cycle_win_score_left")
        self.assertEqual(m.ai_difficulty, (level + 1) % len(m.ai_difficulties))
        self.assertEqual(m.winning_score_index, (points - 1) % len(m.winning_scores))

    def test_mode_and_opponent(self):
        """Rowan: 'Rename "Opponent" to "Mode", and "Against" to "Opponent"' (Match settings'
        Players, and Match Setup's headings with it)."""
        from render.ui.layout import Form
        from tests.test_menu_asks_1_9 import texts
        from tests.test_settings_menus import laid_out
        drawn = texts(open_screen("match_setup"))
        sm = app.state_manager
        sm.push_state("game", mute = True)
        sm.push_state("match", mute = True)
        harness.settle(app)
        page = sm.current()
        page.draw(app.virtual)
        players = [name.text for node in laid_out(page._laid[0]) if isinstance(node, Form)
                   for name, _ in node.rows if name is not None]          # (the rows' names)
        for words in (drawn, players):
            self.assertIn("Mode", words)
            self.assertIn("Opponent", words)
            self.assertNotIn("Against", words)

    def test_greyed_out_where_they_dont_count(self):
        screen = open_screen("match_setup")
        level, points = m.ai_difficulty, m.winning_score_index
        m.vs_wall = True                    # against the wall: no AI, and the match never ends
        click(screen, "cycle_ai_right")
        click(screen, "cycle_win_score_right")
        self.assertEqual((m.ai_difficulty, m.winning_score_index), (level, points))
        m.vs_wall, m.vs_ai = False, False   # Multiplayer: no AI
        click(screen, "cycle_ai_right")
        self.assertEqual(m.ai_difficulty, level)
        m.scoring = False                   # Goals off (in Match Settings): nobody scores
        click(screen, "cycle_win_score_right")
        self.assertEqual(m.winning_score_index, points)
        self.assertIn("Goals are off", app.renderer.win_tip(m, "Goals are off (Match Settings): nobody scores"))


def match(**rules):
    m.reset()
    m.powerups = False
    for name, value in rules.items():
        setattr(m, name, value)
    g = Hu_Taong(app)
    g.start()
    g.countdown, g.paused = None, False
    return g


def stones(g):
    return [o for o in g.objects if getattr(o, "is_obstacle", False)]


class CourtMidMatch(unittest.TestCase):
    def tearDown(self):
        m.reset()

    def test_a_court_picked_from_pause_comes_in_at_the_next_serve(self):
        g = match(court = 0)
        self.addCleanup(g.stop)
        self.assertEqual(stones(g), [])
        g.rules.court = courts.NAMES.index("Twin Stones")
        self.assertEqual(stones(g), [], "not mid-rally")
        g.reset_round()
        self.assertEqual(g.court.name, "Twin Stones")
        self.assertEqual(len(stones(g)), len(g.court.pieces))
        g.rules.court = courts.NAMES.index("Graveyard")
        g.reset_round()
        self.assertEqual(len(stones(g)), len(courts.COURTS[2].pieces), "the old stones gone")
        self.assertEqual(m.court, 0, "your own: untouched")

    def test_random_stays_put(self):
        g = match(court = courts.RANDOM)
        self.addCleanup(g.stop)
        court = g.court
        for _ in range(5):
            g.reset_round()
        self.assertIs(g.court, court, "Random picks once a match, not every serve")

    def test_a_replay_shows_the_new_court(self):
        g = match(court = 0)
        self.addCleanup(g.stop)
        g.rules.court = courts.NAMES.index("Twin Stones")
        g.reset_round()
        for _ in range(3):
            g.recorder.capture(1 / 60)
        view = ReplayView(g.recorder.clip(), app)
        view.show(len(g.recorder.clip().frames) - 1)
        self.assertEqual(len(view.stones), 2)


class AchievementsAtTheEasiest(unittest.TestCase):
    def tearDown(self):
        m.reset()

    def judged(self, g):
        g.p1.score, g.p2.score = 5, 3
        with mock.patch.object(app.achievements, "match_over") as over:
            WinState.judge(SimpleNamespace(app = app), g.p1, g.p2)
        return over.call_args.kwargs

    def test_insane_for_match_point_isnt_beat_insane(self):
        g = match(vs_ai = True, ai_difficulty = 4)
        self.addCleanup(g.stop)
        g.rules.ai_difficulty = 0
        g.reset_round()
        g.rules.ai_difficulty = 4
        g.reset_round()
        self.assertEqual(g.settings.ai_difficulty, 4)
        self.assertEqual(self.judged(g)["ai_level"], 0, "the easiest it was played at")

    def test_insane_all_along_is(self):
        g = match(vs_ai = True, ai_difficulty = 4)
        self.addCleanup(g.stop)
        g.reset_round()
        self.assertEqual(self.judged(g)["ai_level"], 4)

    def test_a_second_player_for_a_while(self):
        g = match(vs_ai = True, ai_difficulty = 4)
        self.addCleanup(g.stop)
        g.rules.vs_ai = False
        g.reset_round()
        g.rules.vs_ai = True
        g.reset_round()
        self.assertTrue(g.p2.ai_enabled)
        self.assertIsNone(self.judged(g)["ai_level"], "not a match against the AI all along")

    def test_chaos_for_the_last_point_isnt_utter_chaos(self):
        g = match(vs_ai = True, mode_talisman_rush = False)
        self.addCleanup(g.stop)
        g.rules.mode_talisman_rush = True
        g.reset_round()
        self.assertFalse(self.judged(g)["chaos"])

    def test_a_court_changed_midway_doesnt_count_for_grand_tour(self):
        g = match(vs_ai = True, court = 0)
        self.addCleanup(g.stop)
        self.assertEqual(self.judged(g)["court"], "Classic")
        g.rules.court = 1
        g.reset_round()
        self.assertIsNone(self.judged(g)["court"])


if __name__ == "__main__":
    unittest.main()

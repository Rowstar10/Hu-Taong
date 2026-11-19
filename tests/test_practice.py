"""Practice, 1.9 (Rowan's 1.9 plan, phase 2, step 8).

"Practice mode as a mode choice on Match Setup: scoring can be turned off; opponent is a wall or
the AI; a talisman picker; all normal settings and modes apply; practice doesn't count towards
stats or achievements."  Practice sits beside vs AI and vs Human.  Against the wall, the other end
of the court is a wall (the other paddle sits out), so the ball always comes back; with scoring on
it counts your misses and never ends.  Online, a host's own Practice choice is ignored.
"""
import json
import unittest

from tests import harness

app = harness.app()

from config import BASE_W                                       # noqa: E402
from core import save_data                                      # noqa: E402
from core.states.game_state import GameState                    # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import KINDS                                 # noqa: E402
from game.replay import ReplayView                              # noqa: E402
from tests.test_settings_menus import click, open_screen        # noqa: E402

m = app.settings.match
KEYS = [kind.key for kind in KINDS]


def practice(**rules):
    m.reset()
    m.practice = True
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

    def test_practice_beside_vs_ai_and_vs_human(self):
        m.reset()
        screen = open_screen("match_setup")
        self.assertIn("opponent_practice", screen.ui_hitboxes)
        self.assertNotIn("practice_wall", screen.ui_hitboxes, "its choices only show once it's picked")
        click(screen, "opponent_practice")
        self.assertTrue(m.practice)
        screen = open_screen("match_setup")
        for key in ("practice_wall", "practice_ai", "practice_scoring_on", "practice_scoring_off",
                    "cycle_practice_talisman_right", "side_red", "side_blue"):
            self.assertIn(key, screen.ui_hitboxes)
        click(screen, "opponent_ai")
        self.assertFalse(m.practice)
        self.assertTrue(m.vs_ai)

    def test_its_choices(self):
        m.reset()
        m.practice = True
        screen = open_screen("match_setup")
        click(screen, "practice_ai")
        self.assertFalse(m.practice_wall)
        click(screen, "practice_scoring_off")
        self.assertFalse(m.practice_scoring)
        click(screen, "cycle_practice_talisman_right")
        self.assertEqual(m.practice_talisman, 1)
        click(screen, "cycle_practice_talisman_left")
        click(screen, "cycle_practice_talisman_left")
        self.assertEqual(KINDS[m.practice_talisman - 1].key, KEYS[-1], "round from the end")

    def test_no_soul_swap_to_pick_against_the_wall(self):
        m.reset()
        m.practice, m.practice_wall = True, False
        m.practice_talisman = KEYS.index("swap") + 1
        screen = open_screen("match_setup")
        click(screen, "practice_wall")
        self.assertEqual(m.practice_talisman, 0, "back to As set")
        self.assertNotIn(KEYS.index("swap") + 1, m.practice_talismans())

    def test_saved(self):
        m.reset()
        m.practice, m.practice_wall, m.practice_scoring, m.practice_talisman = True, False, False, 5
        gameplay = save_data.collect(app)["gameplay"]
        self.assertEqual((gameplay["practice"], gameplay["practice_wall"], gameplay["practice_scoring"],
                          gameplay["practice_talisman"]), (True, False, False, 5))


class AgainstTheWall(unittest.TestCase):
    def tearDown(self):
        self.g.stop()
        m.reset()

    def test_the_other_end_is_a_wall(self):
        self.g = g = practice(practice_wall = True, powerups = False)
        self.assertIs(g.bench, g.p2)
        self.assertNotIn(g.p2, g.objects)
        self.assertFalse(g.p1.ai_enabled)
        self.assertEqual(g.p2.controls_label, "Wall")
        send(g, BASE_W - 300, 1400)
        self.assertTrue(run(g, 1.0, lambda: g.ball.vx < 0), "it bounces back")
        self.assertEqual((g.p1.score, g.p2.score), (0, 0))
        self.assertLess(g.ball.x1, BASE_W - Hu_Taong.PRACTICE_WALL + 2)

    def test_on_the_blue_side_the_wall_is_on_the_left(self):
        self.g = g = practice(practice_wall = True, play_as_blue = True, powerups = False)
        self.assertIs(g.bench, g.p1)
        self.assertFalse(g.p2.ai_enabled)

    def test_with_scoring_it_counts_misses_and_never_ends(self):
        self.g = g = practice(practice_wall = True, powerups = False)
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
        self.g = g = practice(practice_wall = True, mode_switch = True, pu_swap = True)
        self.assertFalse(g.settings.mode_switch)
        self.assertNotIn("swap", [k.key for k in g.powerups.kinds()])

    def test_the_ball_never_slips_past_it(self):
        self.g = g = practice(practice_wall = True, powerups = False)
        send(g, BASE_W + 20, 900)
        g.keep_ball_in()
        self.assertEqual((g.p1.score, g.p2.score), (0, 0))
        self.assertLess(g.ball.vx, 0)

    def test_a_replay_shows_the_wall(self):
        self.g = g = practice(practice_wall = True, powerups = False)
        for _ in range(60):
            g.update(1 / 120)
            g.recorder.capture(1 / 120)
        view = ReplayView(g.recorder.clip(), app)
        view.show(0)
        self.assertIs(view.bench, view.p2)
        self.assertNotIn(view.p2, view.objects)


class ScoringAndTalismans(unittest.TestCase):
    def tearDown(self):
        self.g.stop()
        m.reset()

    def test_scoring_off_nobody_scores(self):
        self.g = g = practice(practice_wall = False, practice_scoring = False, powerups = False)
        self.assertTrue(g.p2.ai_enabled)
        g.p1.y0, g.p1.y1 = 0, g.p1.height
        send(g, 300, -1600, y = 980)
        self.assertTrue(run(g, 1.5, lambda: bool(g.message_text)))
        self.assertEqual((g.p1.score, g.p2.score), (0, 0))
        self.assertIn("not counted", g.message_text)

    def test_a_picked_talisman_is_the_only_one_even_with_power_ups_off(self):
        self.g = g = practice(practice_wall = False, powerups = False, practice_talisman = KEYS.index("fire") + 1)
        self.assertEqual([k.key for k in g.powerups.kinds()], ["fire"])
        g.reset_round()
        self.assertEqual([k.key for k in g.powerups.kinds()], ["fire"], "and at every serve")
        self.assertFalse(m.powerups, "your own settings are as they were")

    def test_as_set_leaves_them_alone(self):
        self.g = g = practice(practice_wall = False, powerups = True, pu_fire = False)
        self.assertNotIn("fire", [k.key for k in g.powerups.kinds()])
        self.assertIn("giant", [k.key for k in g.powerups.kinds()])


class CountsForNothing(unittest.TestCase):
    def setUp(self):
        app.stats.reset()

    def tearDown(self):
        app.stats.reset()
        m.reset()

    def test_no_stats(self):
        m.reset()
        m.practice, m.practice_wall, m.powerups = True, False, False
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        state = sm.current()
        self.assertIsInstance(state, GameState)
        g = state.game
        g.countdown, g.paused = None, False
        before = app.stats.to_dict()
        g.p1.score = m.winning_scores[m.winning_score_index] - 1
        g.p2.y0, g.p2.y1 = 0, g.p2.height
        send(g, BASE_W - 300, 1600, y = 980)
        for _ in range(240):
            state.update(1 / 120)
            harness.settle(app)
            if sm.current() is not state:
                break
        self.assertEqual(sm.current().__class__.__name__, "WinState", "(the practice match was won)")
        after = app.stats.to_dict()
        for key in ("matches", "wins_vs_ai", "points", "play_time", "best_rally"):
            self.assertEqual(after[key], before[key], key)
        sm.set_state("main_menu", mute = True)
        harness.settle(app)


class NotOnline(unittest.TestCase):
    def test_a_host_plays_a_real_match(self):
        """Practice is your own: hosting, the match is a real one whatever you'd picked."""
        from core.net import HostSession
        m.reset()
        m.practice = True
        app.net = HostSession(app, port = 0, upnp = False)       # (on this PC only: no public servers)
        try:
            g = Hu_Taong(app)
            g.start()
            self.assertFalse(g.practice)
            self.assertIsNone(g.bench)
            self.assertIn(g.p2, g.objects)
            g.stop()
        finally:
            app.net.close()
            app.net = None
            m.reset()


class OldSaves(unittest.TestCase):
    def test_a_save_without_practice_loads(self):
        path = save_data.save_path()
        kept = path.read_text() if path.exists() else None
        try:
            data = save_data.collect(app)
            for key in ("practice", "practice_wall", "practice_scoring", "practice_talisman"):
                data["gameplay"].pop(key)
            path.parent.mkdir(parents = True, exist_ok = True)
            path.write_text(json.dumps(data))
            m.practice = True
            m.reset()
            save_data.load(app)
            self.assertEqual((m.practice, m.practice_wall, m.practice_scoring, m.practice_talisman),
                             (False, True, True, 0))
        finally:
            if kept is None:
                path.unlink()
            else:
                path.write_text(kept)
            m.reset()


if __name__ == "__main__":
    unittest.main()

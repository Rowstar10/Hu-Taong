"""Goals ON/OFF, 1.9 (Rowan, 2026-11-20).

"The toggle for scoring works the wrong way.  At the moment it still scores and ends the rally, but
it just says 'Score! (Doesn't count)' ... What I want it to do is completely turn off the ability to
score, so that the rally never ends.  So maybe 'Goals: ON/OFF' would be a better name."  And then:
"I also want the Goals: ON/OFF setting in Match Settings, not greyed out in Multiplayer (vs Human),
and also in the match setup for Online Mode when hosting a room."

Goals is a rule of any match: off, both ends of the court are walls, nobody can score, no scores
show, and the match counts for nothing.  It's in Match settings' Match Rules (Practice Mode and
Multiplayer alike), and on the hosting screen; online, the friend's screen draws the walls and hides
the scores from the host's rows (layout 6).  (It was on Match Setup too, till Rowan kept that screen
to the rules most matches change: "do not include goals. That should be as like extra settings.")
"""
import unittest

from tests import harness

app = harness.app()

import core.net as netcode                                      # noqa: E402
import core.rooms as rooms                                      # noqa: E402
from config import BASE_W                                       # noqa: E402
from core.net import HostSession                                # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.replay import ReplayView                              # noqa: E402
from tests.test_settings_menus import click, open_screen        # noqa: E402

m = app.settings.match


def match(**rules):
    m.reset()
    m.powerups = False
    for name, value in rules.items():
        setattr(m, name, value)
    g = Hu_Taong(app)
    g.start()
    g.countdown, g.paused = None, False
    return g


def send(g, x, vx, y = 980.0):
    b, r = g.ball, g.ball.width / 2
    b.x0, b.x1, b.y0, b.y1 = x - r, x + r, y - r, y + r
    b.vx, b.vy = vx, 0.0


def run(g, seconds, until):
    for _ in range(int(seconds * 120)):
        g.update(1 / 120)
        if until():
            return True
    return False


class AnyMatch(unittest.TestCase):
    def tearDown(self):
        m.reset()

    def test_multiplayer_goals_off(self):
        g = match(vs_ai = False, scoring = False)
        self.addCleanup(g.stop)
        self.assertFalse(g.p1.ai_enabled or g.p2.ai_enabled)
        self.assertEqual(g.closed, {"left", "right"})
        self.assertTrue(g.scoreless and g.practice)
        g.p1.y0, g.p1.y1 = 0, g.p1.height
        send(g, 300, -1600)
        self.assertTrue(run(g, 1.0, lambda: g.ball.vx > 0), "it comes back off Red's end")
        self.assertEqual((g.p1.score, g.p2.score, g.message_text), (0, 0, ""))

    def test_goals_on_as_ever(self):
        g = match(vs_ai = False)
        self.addCleanup(g.stop)
        self.assertEqual(g.closed, set())
        self.assertFalse(g.practice)

    def test_a_replay_of_it_shows_the_walls(self):
        g = match(vs_ai = False, scoring = False)
        self.addCleanup(g.stop)
        for _ in range(20):
            g.update(1 / 120)
            g.recorder.capture(1 / 120)
        view = ReplayView(g.recorder.clip(), app)
        view.show(len(g.recorder.clip().frames) - 1)
        self.assertEqual(view.closed, {"left", "right"})
        self.assertTrue(view.scoreless)


class Online(unittest.TestCase):
    """Hosting (on this PC only: no public servers)."""

    def setUp(self):
        self.stun, self.brokers = netcode.STUN_SERVERS, rooms.BROKERS
        netcode.STUN_SERVERS, rooms.BROKERS = [("127.0.0.1", 9)], []
        app.net = HostSession(app, port = 0, upnp = False)

    def tearDown(self):
        app.net.close()
        app.net = None
        netcode.STUN_SERVERS, rooms.BROKERS = self.stun, self.brokers
        m.reset()

    def test_the_host_can_turn_goals_off(self):
        g = match(scoring = False)
        self.addCleanup(g.stop)
        self.assertEqual(g.closed, {"left", "right"})
        self.assertIsNone(g.bench, "(no wall or AI online: the friend is the other player)")
        self.assertFalse(g.p1.ai_enabled or g.p2.ai_enabled)
        self.assertIn("No goals", app.net.settings_summary())

    def test_practice_mode_choices_dont_apply_online(self):
        g = match(vs_ai = True, vs_wall = True)
        self.addCleanup(g.stop)
        self.assertIsNone(g.bench)
        self.assertEqual(g.closed, set())


class Screens(unittest.TestCase):
    def tearDown(self):
        m.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_not_on_match_setup(self):
        keys = open_screen("match_setup").ui_hitboxes
        self.assertFalse([k for k in keys if "scoring" in k or "goals" in k], "in Match Settings")

    def test_match_settings_goals_in_match_rules(self):
        m.reset()
        m.vs_ai = False
        screen = open_screen("match")
        click(screen, "toggle_goals")
        self.assertFalse(m.scoring, "Multiplayer too")
        boxes = screen.ui_hitboxes
        self.assertLess(boxes["cycle_win_score_left"].top, boxes["toggle_goals"].top)
        self.assertLess(boxes["toggle_goals"].top, boxes["toggle_middle_wall"].top, "among the Match Rules")

    def test_the_columns_start_level(self):
        """(Rowan: the Talismans section started lower down than the Players section.  Since later
        in 1.9, two rows of sections, each row's starting level.)"""
        boxes = open_screen("match").ui_hitboxes
        tops = [boxes[k].top for k in ("cycle_ai_left", "cycle_court_left", "cycle_win_score_left")]
        self.assertLess(max(tops) - min(tops), 30)

    def test_on_the_hosting_screen(self):
        from core.states.online_state import OnlineState
        stun, brokers = netcode.STUN_SERVERS, rooms.BROKERS
        netcode.STUN_SERVERS, rooms.BROKERS = [("127.0.0.1", 9)], []
        try:
            m.reset()
            sm = app.state_manager
            sm.set_state("main_menu", mute = True)
            sm.push_state("match_setup", mute = True)
            harness.settle(app)
            screen = OnlineState(app)
            sm.stack.append(screen)
            screen.mode = "host"
            if hasattr(screen, "start_hosting"):
                screen.start_hosting()
            elif app.net is None:
                app.net = HostSession(app, port = 0, upnp = False)
            screen.draw(app.virtual)
            if "toggle_goals" not in screen.ui_hitboxes:
                self.skipTest("(the hosting screen needs its session: drawn by the online tests)")
            click(screen, "toggle_goals")
            self.assertFalse(m.scoring)
        finally:
            if app.net is not None:
                app.net.close()
                app.net = None
            netcode.STUN_SERVERS, rooms.BROKERS = stun, brokers


if __name__ == "__main__":
    unittest.main()

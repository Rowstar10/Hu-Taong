"""Match settings from the pause menu, 1.7 (Rowan's 1.7 plan, 2026-11-17).

Pause has a Match Settings button.  What you change there comes in at the next serve, never
mid-rally: a match plays by its own copy of the rules, renewed at each serve (Chaos's every-point
sizes and speeds are rolled into that copy, never into your own settings).  Online only the host
can change them: its game sends its friend its rules, and the friend sees them read only.
"""
import time
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from core.net import RULES, GuestSession, HostSession, Link, pack_json, unpack_json    # noqa: E402
from core.settings import MatchSettings                         # noqa: E402
from core.state_manager import StateManager                     # noqa: E402

m = app.settings.match


def click(screen, key):
    screen.draw(app.virtual)
    x, y = screen.ui_hitboxes[key].center
    pos = (x / app.sx, y / app.sy)
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos))


class FromPause(unittest.TestCase):
    def setUp(self):
        m.reset()
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        self.game = sm.current().game
        self.game.countdown, self.game.paused = None, False
        sm.push_state("pause", mute = True)
        harness.settle(app)
        self.pause = sm.current()

    def tearDown(self):
        m.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def open_match_settings(self):
        click(self.pause, "match_settings")
        harness.settle(app)
        screen = app.state_manager.current()
        self.assertEqual(screen.NAME, "match")
        screen.draw(app.virtual)
        return screen

    def test_pause_opens_the_match_settings(self):
        screen = self.open_match_settings()
        self.assertFalse(screen.read_only)
        self.assertEqual(screen.note, screen.IN_MATCH_NOTE, "it says changes come in at the next serve")
        self.assertIn("reset_defaults", screen.ui_hitboxes)

    def test_changes_come_in_at_the_next_serve(self):
        game = self.game
        screen = self.open_match_settings()
        click(screen, "toggle_middle_wall")
        click(screen, "cycle_countdown_right")
        m.ball_speed = m.ball_speed_max
        self.assertFalse(m.middle_wall)
        game.apply_gameplay_settings()
        self.assertTrue(game.wall_up, "not mid-rally")
        self.assertNotEqual(game.ball.speed, m.ball_speed_max)
        game.on_score(game.ball, {"normal": (1, 0)})
        game.message_timer = 0.001
        game.update(0.01)                                        # the next serve
        self.assertFalse(game.wall_up)
        self.assertEqual(game.ball.speed, m.ball_speed_max)
        self.assertEqual(game.countdown.shown_value, 2)

    def test_a_mode_switched_on_comes_in_at_the_next_serve(self):
        game = self.game
        screen = self.open_match_settings()
        click(screen, "toggle_mode_twin_ball")
        self.assertEqual(len(game.powerups.balls()), 1)
        game.on_score(game.ball, {"normal": (1, 0)})
        game.message_timer = 0.001
        game.update(0.01)
        self.assertEqual(len(game.powerups.balls()), 2)


class TheHostSendsItsRules(unittest.TestCase):
    def setUp(self):
        m.reset()
        self.net = HostSession(app, port = 0, upnp = False)
        app.net = self.net
        self.friend = Link(0)
        self.friend.peer = ("127.0.0.1", self.net.port)
        self.net.guest = self.net.last_guest = ("127.0.0.1", self.friend.port)
        self.net.link.peer = self.net.guest
        self.net.link.heard = time.perf_counter()

    def tearDown(self):
        m.reset()
        self.friend.close()
        app.leave_online()

    def heard(self):
        time.sleep(0.05)
        return [(kind, payload) for kind, payload, *_ in self.friend.receive() if kind == RULES]

    def test_twice_a_second(self):
        m.mode_switch, m.switch_timing, m.pu_fire = True, 2, False
        self.net.send_due()
        sent = self.heard()
        self.assertEqual(len(sent), 1)
        rules = unpack_json(sent[0][1])
        self.assertEqual((rules["mode_switch"], rules["switch_timing"]), (True, 2))
        self.assertIn("fire", rules["off"])
        self.net.send_due()
        self.assertEqual(self.heard(), [], "not every frame")
        self.net.last_rules -= 0.6
        self.net.send_due()
        self.assertEqual(len(self.heard()), 1)


class TheFriendSeesThemReadOnly(unittest.TestCase):
    def setUp(self):
        m.reset()
        self.net = GuestSession(app, address = ("127.0.0.1", 9))
        app.net = self.net
        host = MatchSettings(app)
        host.mode_twin_ball, host.winning_score_index, host.pu_ghost = True, 4, False
        self.rules = host.rules()
        self.net.link.receive = lambda: [(RULES, pack_json(self.rules), ("127.0.0.1", 9), 11)]
        self.net.update(1 / 60)
        self.net.link.receive = lambda: []

    def tearDown(self):
        m.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)
        app.leave_online()

    def test_the_rules_arrive(self):
        self.assertEqual(self.net.rules["winning_score_index"], 4)

    def open_from_pause(self):
        pause = StateManager.create("guest_pause", app)
        app.state_manager.stack = [pause]
        click(pause, "match_settings")
        harness.settle(app)
        screen = app.state_manager.current()
        screen.update(1 / 60)
        screen.draw(app.virtual)
        return screen

    def test_the_hosts_rules_not_yours(self):
        screen = self.open_from_pause()
        self.assertEqual(screen.NAME, "match")
        self.assertTrue(screen.read_only)
        self.assertTrue(screen.shown.mode_twin_ball)
        self.assertFalse(m.mode_twin_ball, "yours are untouched")
        self.assertFalse(screen.shown.pu_ghost)
        self.assertEqual(screen.note, screen.READ_ONLY_NOTE)

    def test_nothing_can_be_changed(self):
        screen = self.open_from_pause()
        before = (m.modes_on(), screen.shown.modes_on(), m.winning_score_index)
        for key in ("toggle_mode_chaos", "cycle_win_score_right", "open_powerups", "open_ball_paddles"):
            click(screen, key)
        harness.settle(app)
        self.assertIs(app.state_manager.current(), screen, "nothing opened")
        screen.update(1 / 60)
        self.assertEqual((m.modes_on(), screen.shown.modes_on(), m.winning_score_index), before)
        self.assertNotIn("reset_defaults", screen.ui_hitboxes)

    def test_not_before_they_arrive(self):
        self.net.rules = None
        pause = StateManager.create("guest_pause", app)
        app.state_manager.stack = [pause]
        click(pause, "match_settings")
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "guest_pause")


class TakingRules(unittest.TestCase):
    def test_nonsense_is_ignored_or_kept_in_range(self):
        shown = MatchSettings(app)
        shown.take_rules({"court": 99, "countdown": -3, "mode_chaos": "yes", "ball_speed": "fast", "off": ["fire"]})
        self.assertEqual(shown.court, len(shown.court_options) - 1)
        self.assertEqual(shown.countdown, 0)
        self.assertFalse(shown.mode_chaos)
        self.assertFalse(shown.pu_fire)
        self.assertTrue(shown.pu_ghost)
        shown.take_rules("nothing")


if __name__ == "__main__":
    unittest.main()

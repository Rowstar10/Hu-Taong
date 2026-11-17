"""Match settings mid-match, 1.7 (Rowan's 1.7 plan, 2026-11-17).

From Pause > Settings > Match you can change the rules mid-match, and what you change comes in at
the next serve, never mid-rally: a match plays by its own copy of the rules, renewed at each serve
(Chaos's every-point sizes and speeds are rolled into that copy, never into your own settings).

Rowan's playtest of 1.7 (same day): Pause doesn't need its own Match Settings button, as Settings
has it; and online only the host has the Match card (the host's rules are the match's), so the
friend who joined doesn't see it at all.
"""
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from core.net import GuestSession, HostSession                  # noqa: E402
from core.state_manager import StateManager                     # noqa: E402

m = app.settings.match


def click(screen, key):
    screen.draw(app.virtual)
    x, y = screen.ui_hitboxes[key].center
    pos = (x / app.sx, y / app.sy)
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos))


def opened(screen, key):
    click(screen, key)
    harness.settle(app)
    top = app.state_manager.current()
    top.draw(app.virtual)
    return top


class MidMatch(unittest.TestCase):
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
        self.pause.draw(app.virtual)

    def tearDown(self):
        m.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def open_match_settings(self):
        screen = opened(opened(self.pause, "settings"), "match")
        self.assertEqual(screen.NAME, "match")
        return screen

    def test_no_button_of_its_own_on_pause(self):
        self.assertNotIn("match_settings", self.pause.ui_hitboxes)

    def test_settings_has_it_and_says_when_changes_come_in(self):
        screen = self.open_match_settings()
        self.assertEqual(screen.note, screen.IN_MATCH_NOTE)
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


class OnlyTheHostOnline(unittest.TestCase):
    def tearDown(self):
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)
        app.leave_online()

    def hub_cards(self):
        hub = StateManager.create("settings", app)
        hub.draw(app.virtual)
        return set(hub.ui_hitboxes) & {"match", "gameplay", "display", "audio", "interface"}

    def test_the_host_has_the_match_card(self):
        app.net = HostSession(app, port = 0, upnp = False)
        self.assertIn("match", self.hub_cards())

    def test_the_friend_who_joined_doesnt(self):
        app.net = GuestSession(app, address = ("127.0.0.1", 9))
        self.assertEqual(self.hub_cards(), {"gameplay", "display", "audio", "interface"})
        pause = StateManager.create("guest_pause", app)
        pause.draw(app.virtual)
        self.assertNotIn("match_settings", pause.ui_hitboxes)

    def test_offline_everyone_has_it(self):
        app.net = None
        self.assertIn("match", self.hub_cards())


if __name__ == "__main__":
    unittest.main()

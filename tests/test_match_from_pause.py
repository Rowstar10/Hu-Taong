"""Match settings mid-match, 1.7 (Rowan's 1.7 plan, 2026-11-17).

From Pause > Settings > Match you can change the rules mid-match, and what you change comes in at
the next serve, never mid-rally: a match plays by its own copy of the rules, renewed at each serve
(Chaos's every-point sizes and speeds are rolled into that copy, never into your own settings).

Rowan's playtest of 1.7 (same day): Pause doesn't need its own Match Settings button, as Settings
has it; and online only the host has the Match card (the host's rules are the match's), so the
friend who joined doesn't see it at all.

Rowan, 1.9: "Everything accessed and changed in match settings during a match should only apply to
that current match, and the global match settings should remain unchanged by creating a new match."
So a match keeps its own rules (`game.rules`, a copy taken as it's made): Match settings opened
mid-match changes those, never your saved ones, and a new match starts from your saved ones again.
And Match settings has a Players section with Match Setup's choices (Practice Mode or Multiplayer,
the AI or a wall, your paddle, goals), which mid-match change this match from its next serve.
"""
import unittest

from tests import harness
from config import BALL_PACE                                    # noqa: E402  (the ball's pace, 1.9)

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


def reach(screen, key):
    """Scroll the page so the control is on show (the Match page scrolls)."""
    screen.draw(app.virtual)
    if key not in screen.ui_hitboxes and hasattr(screen, "reveal"):
        screen.reveal(key)
        screen.scroll = screen.scroll_target
        screen.draw(app.virtual)
        screen.draw(app.virtual)


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

    def next_serve(self):
        game = self.game
        game.on_score(game.ball, {"normal": (1, 0)})
        game.message_timer = 0.001
        game.update(0.01)

    def test_changes_come_in_at_the_next_serve(self):
        game = self.game
        rules = game.rules
        screen = self.open_match_settings()
        reach(screen, "toggle_middle_wall")
        click(screen, "toggle_middle_wall")
        reach(screen, "cycle_countdown_right")
        click(screen, "cycle_countdown_right")
        rules.ball_speed = rules.ball_speed_max
        self.assertFalse(rules.middle_wall)
        game.apply_gameplay_settings()
        self.assertTrue(game.wall_up, "not mid-rally")
        self.assertNotEqual(game.ball.speed, rules.ball_speed_max * BALL_PACE)
        self.next_serve()
        self.assertFalse(game.wall_up)
        self.assertEqual(game.ball.speed, rules.ball_speed_max * BALL_PACE)
        self.assertEqual(game.countdown.shown_value, 2)

    def test_only_this_match(self):
        """Your saved Match settings stay as they were, and a new match starts from them."""
        rules = self.game.rules
        screen = self.open_match_settings()
        reach(screen, "toggle_middle_wall")
        click(screen, "toggle_middle_wall")
        self.assertFalse(rules.middle_wall)
        self.assertTrue(m.middle_wall, "your own: untouched")
        from core import save_data
        self.assertTrue(save_data.collect(app)["gameplay"]["middle_wall"])
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        self.assertTrue(sm.current().game.rules.middle_wall, "a new match: from your own")

    def test_from_match_setup_it_is_your_own(self):
        """(From the main menu's Settings till later in 1.9: now Match Setup has it.)"""
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("match_setup", mute = True)
        sm.push_state("match", mute = True)
        harness.settle(app)
        screen = sm.current()
        self.assertIsNone(screen.note)
        reach(screen, "toggle_middle_wall")
        click(screen, "toggle_middle_wall")
        self.assertFalse(m.middle_wall)
        self.assertNotIn("cycle_opponent_left", harness.every_box(screen), "Players: on Match Setup, behind it")

    def test_players_mid_match(self):
        """Match Setup's choices, in Match settings: a second player takes over the AI's paddle."""
        game = self.game
        screen = self.open_match_settings()
        for key in ("cycle_opponent_right", "cycle_against_right", "cycle_your_paddle_right", "toggle_goals"):
            reach(screen, key)
            self.assertIn(key, screen.ui_hitboxes)
        self.assertTrue(game.p2.ai_enabled)
        click(screen, "cycle_opponent_right")
        self.assertFalse(game.rules.vs_ai)
        self.assertTrue(game.p2.ai_enabled, "not mid-rally")
        self.next_serve()
        self.assertFalse(game.p1.ai_enabled or game.p2.ai_enabled, "Multiplayer: both played here")
        self.assertTrue(m.vs_ai, "your own: untouched")

    def test_your_paddle_and_the_wall_mid_match(self):
        game, rules = self.game, self.game.rules
        rules.play_as_blue = True
        self.next_serve()
        self.assertTrue(game.p1.ai_enabled)
        self.assertFalse(game.p2.ai_enabled, "you're Blue now")
        rules.vs_wall = True
        self.next_serve()
        self.assertIs(game.bench, game.p1)
        self.assertNotIn(game.p1, game.objects)
        self.assertEqual(game.closed, {"left"})
        rules.vs_wall = False
        self.next_serve()
        self.assertIsNone(game.bench)
        self.assertIn(game.p1, game.objects, "back on the court")
        self.assertTrue(game.p1.ai_enabled)
        self.assertEqual(game.closed, set())
        self.assertTrue(game.practice, "(it was practice for a while: the match counts for nothing)")

    def test_goals_off_mid_match_comes_in_on_its_own(self):
        """With goals off no serve would come: a change made from Pause brings one."""
        game, rules = self.game, self.game.rules
        rules.scoring = False
        self.next_serve()
        self.assertEqual(game.closed, {"left", "right"})
        game.countdown, game.paused = None, False
        rules.scoring = True
        game.update(0.01)
        self.assertEqual(game.closed, set(), "the goals are back")
        self.assertIsNotNone(game.countdown, "with a serve")

    def test_a_mode_switched_on_comes_in_at_the_next_serve(self):
        game = self.game
        screen = opened(self.open_match_settings(), "open_modes")       # (Choose Modes' page, 1.9)
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

    def in_a_match(self):
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)

    def test_the_host_has_the_match_card_in_a_match(self):
        """(In the lobby, the hosting screen has its own Match Settings button.)"""
        self.in_a_match()
        app.net = HostSession(app, port = 0, upnp = False)
        self.assertIn("match", self.hub_cards())

    def test_the_friend_who_joined_doesnt(self):
        app.net = GuestSession(app, address = ("127.0.0.1", 9))
        self.assertEqual(self.hub_cards(), {"gameplay", "display", "audio", "interface"})
        pause = StateManager.create("guest_pause", app)
        pause.draw(app.virtual)
        self.assertNotIn("match_settings", pause.ui_hitboxes)

    def test_offline_everyone_has_it_in_a_match(self):
        app.net = None
        self.in_a_match()
        self.assertIn("match", self.hub_cards())

    def test_not_from_the_main_menu(self):
        """Rowan, 1.9: "it feels a little bit weird being able to access all of these settings that
        should normally apply to the game you're in from the main menu"."""
        app.net = None
        self.assertNotIn("match", self.hub_cards())


if __name__ == "__main__":
    unittest.main()

"""Pausing and carrying on, 1.6 (Rowan's playtest list, 2026-11-16).

- Clicking away pauses a match (Auto-Pause); clicking back now carries on by itself, after a
  3-2-1.  A pause the player made, or took in hand (opened Settings from it, say), stays put.
- Every resume from a pause mid-point counts 3-2-1 first, so both players see it coming.

Playtesting 1.6 again (2026-11-17): that 3-2-1 goes at the serve countdown's pace, a second a
number, offline too.  Offline it had been three times quicker.
"""
import unittest
from types import SimpleNamespace

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

DT = 1 / 60


def frames(n = 1):
    """Whole frames of the game, events and all, as App.run plays them."""
    for _ in range(n):
        app.state_manager.process_changes()
        app.dt = DT
        app.loop()


def post(kind, **attrs):
    pygame.event.post(pygame.event.Event(kind, **attrs))


def top():
    return getattr(app.state_manager.current(), "NAME", "")


class PauseAndResume(unittest.TestCase):
    def setUp(self):
        pygame.event.clear()
        app.net = None
        app.has_focus = True
        app.settings.interface.auto_pause = True
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        self.game = sm.current().game
        self.game.countdown, self.game.paused = None, False     # past the serve, ball in play
        self.game.p1.ai_enabled = self.game.p2.ai_enabled = False
        self.game.powerups.wait = 999.0
        frames(2)

    def tearDown(self):
        pygame.event.clear()
        app.has_focus = True
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def ball_at(self):
        return (self.game.ball.x0, self.game.ball.y0)

    def click(self, key):
        """Click the middle of a button on the screen on top."""
        rect = app.state_manager.current().ui_hitboxes[key]
        cx, cy = rect.center
        post(pygame.MOUSEBUTTONDOWN, button = 1, pos = (cx / app.sx, cy / app.sy))
        post(pygame.MOUSEBUTTONUP, button = 1, pos = (cx / app.sx, cy / app.sy))

    def test_clicking_back_carries_on_after_a_countdown(self):
        post(pygame.WINDOWFOCUSLOST)
        frames(2)
        self.assertEqual(top(), "pause")
        held = self.ball_at()
        frames(30)
        self.assertEqual(top(), "pause", "stays paused while the window is away")
        self.assertEqual(self.ball_at(), held)

        post(pygame.WINDOWFOCUSGAINED)
        frames(2)
        self.assertEqual(top(), "game")
        cd = self.game.countdown
        self.assertIsNotNone(cd, "back to the match with a countdown")
        self.assertEqual(cd.shown_value, 3)

        frames(170)                     # 2.83 s: still counting (a second a number, 3 s in all)
        self.assertIsNotNone(self.game.countdown)
        self.assertEqual(self.ball_at(), held, "the ball waits for the countdown")
        frames(15)
        self.assertIsNone(self.game.countdown, "done after 3 s")
        frames(5)
        self.assertNotEqual(self.ball_at(), held, "play carries on")

    def test_a_pause_you_made_stays_paused(self):
        post(pygame.KEYDOWN, key = pygame.K_ESCAPE, mod = 0, unicode = "", scancode = 0)
        frames(2)
        self.assertEqual(top(), "pause")
        post(pygame.WINDOWFOCUSLOST)
        frames(2)
        post(pygame.WINDOWFOCUSGAINED)
        frames(10)
        self.assertEqual(top(), "pause")

    def test_a_pause_taken_in_hand_stays_paused(self):
        post(pygame.WINDOWFOCUSLOST)
        frames(2)
        self.assertEqual(top(), "pause")
        self.click("settings")
        frames(2)
        self.assertNotEqual(top(), "pause", "Settings opened over the pause")
        post(pygame.WINDOWFOCUSGAINED)
        frames(5)
        app.state_manager.pop_state(mute = True)     # back out of the settings
        frames(5)
        self.assertEqual(top(), "pause", "opening Settings made it the player's pause")

    def test_resume_counts_down_at_the_serve_pace_offline(self):
        """The same pace as the serve countdown: as long from 3 to go, number for number."""
        def seconds_to_go():
            n = 0
            while self.game.countdown is not None:
                frames()
                n += 1
            return n * DT
        self.game.start_countdown(3)
        serve = seconds_to_go()
        post(pygame.KEYDOWN, key = pygame.K_ESCAPE, mod = 0, unicode = "", scancode = 0)
        frames(2)
        post(pygame.KEYDOWN, key = pygame.K_ESCAPE, mod = 0, unicode = "", scancode = 0)
        frames(2)                       # the second of these is the countdown's first
        self.assertEqual(top(), "game")
        self.assertEqual(self.game.countdown.shown_value, 3)
        resume = seconds_to_go() + DT
        self.assertAlmostEqual(resume, serve, delta = 2 * DT)
        self.assertAlmostEqual(resume, 3.0, delta = 3 * DT)

    def test_a_serve_countdown_just_carries_on(self):
        self.game.start_countdown(3)
        serve = self.game.countdown
        post(pygame.WINDOWFOCUSLOST)
        frames(2)
        post(pygame.WINDOWFOCUSGAINED)
        frames(2)
        self.assertEqual(top(), "game")
        self.assertIs(self.game.countdown, serve)


class ResumeCountdown(unittest.TestCase):
    """Hu_Taong.resume_countdown on its own."""

    def setUp(self):
        app.state_manager.set_state("main_menu", mute = True)
        app.state_manager.push_state("game", mute = True)
        harness.settle(app)
        self.game = app.state_manager.current().game
        self.game.countdown, self.game.paused = None, False

    def tearDown(self):
        self.game.net = None
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_online_and_off_count_three_seconds(self):
        for net in (SimpleNamespace(), None):
            self.game.countdown, self.game.paused, self.game.net = None, False, net
            self.game.resume_countdown()
            self.assertEqual((self.game.countdown.shown_value, self.game.countdown.remaining), (3, 3.0))

    def test_a_goal_message_plays_out(self):
        self.game.message_text = "Red scored!"
        self.game.resume_countdown()
        self.assertIsNone(self.game.countdown)

    def test_a_goal_held_for_word_of_a_save_keeps_waiting(self):
        self.game.paused = True                 # online: the host waits for the friend's word
        self.game.resume_countdown()
        self.assertIsNone(self.game.countdown)
        self.assertTrue(self.game.paused)


if __name__ == "__main__":
    unittest.main()

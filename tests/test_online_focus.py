"""Clicking away from an online match, 1.6 (Rowan's playtest list, 2026-11-16).

Online, clicking away used to leave the match running for the other player.  Now if either player's
window loses focus, the match pauses for both; it only carries on while both windows are in front,
and always after a 3-2-1 that both screens show (the host's countdown travels in its pictures).
A pause the window losing focus opened ends by itself once both players are back.
"""
import struct
import time
import unittest

from tests import harness

app = harness.app()

from core.net import INPUT, GuestSession, HostSession, Link, pack_json, unpack_json    # noqa: E402
from core.state_manager import StateManager                                           # noqa: E402


class Hosting(unittest.TestCase):
    def setUp(self):
        app.has_focus = True
        app.settings.gameplay.auto_pause = True
        self.net = HostSession(app, port = 0, upnp = False)
        app.net = self.net
        self.friend = Link(0)                                   # the friend's end of the line
        self.friend.peer = ("127.0.0.1", self.net.port)
        self.net.guest = self.net.last_guest = ("127.0.0.1", self.friend.port)
        self.net.link.peer = self.net.guest
        self.net.link.heard = time.perf_counter()
        self.seq = 0
        self.asked = {"pause": 0, "resume": 0}
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        self.game = sm.current().game
        self.game.countdown, self.game.paused = None, False     # past the serve, ball in play
        self.game.powerups.wait = 999.0

    def tearDown(self):
        app.has_focus = True
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)
        self.friend.close()
        app.leave_online()

    def friend_says(self, focus = 1, ask = None):
        """One of the friend's inputs: no keys, their window in front or not, maybe a request."""
        if ask:
            self.asked[ask] += 1
        self.seq += 1
        extra = dict(self.asked, menu = 0, focus = focus)
        self.friend.send(INPUT, struct.pack("<IBd", self.seq, 0, time.perf_counter()) + pack_json(extra))

    def frame(self):
        """One frame of the game: hear from the friend, react, change screens."""
        time.sleep(0.02)                                        # let the packet arrive
        self.net.update(1 / 60)
        app.online_requests()
        app.state_manager.update(1 / 60)
        harness.settle(app)
        return app.state_manager.current()

    def test_the_friend_clicking_away_pauses_for_both_until_they_are_back(self):
        self.friend_says(focus = 0)
        pause = self.frame()
        self.assertEqual(pause.NAME, "pause")
        self.assertTrue(pause.auto)
        self.assertTrue(pause.by_friend)
        for _ in range(3):
            self.friend_says(focus = 0)
            self.assertEqual(self.frame().NAME, "pause", "waits while they're away")

        self.friend_says(focus = 1)
        self.frame()
        screen = self.frame()
        self.assertEqual(screen.NAME, "game", "carries on once they're back")
        self.assertIsNotNone(self.game.countdown)
        self.assertEqual(self.game.countdown.shown_value, 3)
        self.assertGreater(self.game.countdown.remaining, 2.9, "3-2-1 at the usual pace, for both")

    def test_you_clicking_away_pauses_for_both_too(self):
        self.friend_says(focus = 1)
        app.has_focus = False
        pause = self.frame()
        self.assertEqual(pause.NAME, "pause")
        self.assertFalse(pause.by_friend)
        self.assertFalse(app.focused(), "the friend's game is told you're away")
        app.has_focus = True
        self.friend_says(focus = 1)
        self.frame()
        self.assertEqual(self.frame().NAME, "game")
        self.assertIsNotNone(self.game.countdown)

    def test_resume_waits_while_the_friend_is_away(self):
        self.friend_says(focus = 1, ask = "pause")              # the friend paused it themselves
        pause = self.frame()
        self.assertEqual(pause.NAME, "pause")
        self.assertFalse(pause.auto, "a pause someone made stays until someone resumes")
        self.friend_says(focus = 0)
        self.frame()
        pause.resume()
        self.assertEqual(self.frame().NAME, "pause", "Resume does nothing while they're away")
        self.friend_says(focus = 1)
        self.assertEqual(self.frame().NAME, "pause", "back, but nobody pressed Resume")
        pause.resume()
        self.assertEqual(self.frame().NAME, "game")
        self.assertEqual(self.game.countdown.remaining, 3.0)

    def test_the_friends_resume_waits_while_you_are_away(self):
        self.friend_says(focus = 1, ask = "pause")
        self.frame()
        app.has_focus = False
        self.friend_says(focus = 1, ask = "resume")
        self.assertEqual(self.frame().NAME, "pause")

    def test_auto_pause_off_lets_you_click_away(self):
        app.settings.gameplay.auto_pause = False
        app.has_focus = False
        self.friend_says(focus = 1)
        self.assertEqual(self.frame().NAME, "game")


class Joining(unittest.TestCase):
    def setUp(self):
        app.has_focus = True
        app.settings.gameplay.auto_pause = True
        self.net = GuestSession(app, address = ("127.0.0.1", 9))
        app.net = self.net
        self.sent = []
        self.net.link.send = lambda kind, payload: self.sent.append((kind, payload))
        self.screen = StateManager.create("guest_pause", app)

    def tearDown(self):
        app.has_focus = True
        app.leave_online()

    def host_says(self, focus):
        self.net.snaps.append((0.0, b"", {"paused": True, "focus": focus}, time.perf_counter()))

    def test_your_window_going_away_is_told_to_the_host(self):
        app.has_focus = False
        self.net.send_input()
        kind, payload = self.sent[-1]
        self.assertEqual(kind, INPUT)
        self.assertEqual(unpack_json(payload[13:]).get("focus"), 0)

    def test_resume_waits_while_the_host_is_away(self):
        self.host_says(focus = 0)
        self.screen.ask_resume()
        self.assertEqual(self.net.requests["resume"], 0)
        self.host_says(focus = 1)
        self.screen.ask_resume()
        self.assertEqual(self.net.requests["resume"], 1)


if __name__ == "__main__":
    unittest.main()

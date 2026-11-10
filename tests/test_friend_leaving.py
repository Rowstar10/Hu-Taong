"""A friend leaving an online match (1.4 fix).

In 1.3, if your friend left from their pause screen (Leave Match opens a confirmation over it),
yours went on saying "Your friend is in the settings..." and wouldn't resume.  Now the match ends:
you're told they left, and get the end-of-match screen without Play Again, where you can still
watch and save the replay and highlights.  It works the same the other way round, for a guest
whose host leaves.  Nothing goes over the internet: the "friend" is a socket on this computer.
"""
import time
import unittest

from tests import harness

app = harness.app()

from core.net import BYE, GuestSession, HostSession, Link     # noqa: E402


class Hosting(unittest.TestCase):
    def setUp(self):
        self.net = HostSession(app, port = 0, upnp = False)
        app.net = self.net
        self.friend = Link(0)                                   # the friend's end of the line
        self.friend.peer = ("127.0.0.1", self.net.port)
        self.net.guest = self.net.last_guest = ("127.0.0.1", self.friend.port)
        self.net.link.peer = self.net.guest
        self.net.link.heard = time.perf_counter()
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        self.game = sm.current().game
        self.stats = (app.stats.online_matches, app.stats.online_wins, app.stats.online_losses)

    def tearDown(self):
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)
        self.friend.close()
        app.leave_online()

    def frame(self):
        """One frame of the game: hear from the friend, react, change screens."""
        time.sleep(0.02)                                        # let the packet arrive
        self.net.update(1 / 60)
        app.online_requests()
        harness.settle(app)
        return app.state_manager.current()

    def friend_leaves(self):
        for _ in range(3):                                      # as the game sends it
            self.friend.send(BYE, b"")
        return self.frame()

    def assert_left_screen(self, screen):
        self.assertEqual(screen.NAME, "win")
        self.assertEqual(screen.left, "Your friend left the match.")
        shown = harness.buttons(screen, app)
        self.assertLessEqual({"watch_replay", "settings", "main_menu"}, shown)
        self.assertFalse(shown & {"play_again", "continue", "lobby"}, shown)
        self.assertEqual(self.stats, (app.stats.online_matches, app.stats.online_wins, app.stats.online_losses))

    def test_friend_leaves_from_their_pause_screen(self):
        self.net.guest_menu = 2                 # their Leave Match confirmation, over their pause screen
        self.assertEqual(self.frame().NAME, "pause")
        self.assert_left_screen(self.friend_leaves())
        self.assertEqual(self.net.guest_menu, 0)

    def test_friend_leaves_while_you_are_in_the_settings(self):
        sm = app.state_manager
        sm.push_state("pause", mute = True)
        sm.push_state("settings", mute = True)
        harness.settle(app)
        self.assert_left_screen(self.friend_leaves())
        self.assertEqual([s.NAME for s in sm.stack], ["main_menu", "game", "win"])

    def test_friend_leaves_mid_rally(self):
        self.assert_left_screen(self.friend_leaves())

    def test_the_friend_going_quiet_ends_the_match_too(self):
        self.net.link.heard -= 10
        screen = self.frame()
        self.assertEqual((screen.NAME, screen.left), ("win", "Lost touch with your friend."))

    def test_friend_leaves_after_the_match_was_won(self):
        sm = app.state_manager
        sm.push_state("win", p1 = self.game.p1, p2 = self.game.p2, winner = self.game.p1, loser = self.game.p2,
                      mute = True)
        harness.settle(app)
        self.assertIn("play_again", harness.buttons(sm.current(), app))
        screen = self.friend_leaves()
        self.assertEqual((screen.NAME, screen.left), ("win", None))     # the result stands...
        shown = harness.buttons(screen, app)
        self.assertFalse(shown & {"play_again", "continue", "lobby"}, shown)   # ...but no one to play again


class Joining(unittest.TestCase):
    def setUp(self):
        self.net = GuestSession(app, address = ("127.0.0.1", 9))
        app.net = self.net
        self.net.status = "playing"
        self.net.snaps = [(1.0, b"", {"guest": 2, "info": {}}, None)]
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("guest_match", mute = True)
        sm.push_state("guest_pause", mute = True)
        harness.settle(app)
        self.stats = app.stats.online_matches

    def tearDown(self):
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)
        app.leave_online()

    def frame(self):
        app.online_requests()
        harness.settle(app)
        return app.state_manager.current()

    def test_host_leaves(self):
        self.net.status, self.net.reason = "lost", "The host left the game."
        screen = self.frame()
        self.assertEqual((screen.NAME, screen.left), ("guest_result", "Your friend left the match."))
        self.assertEqual(harness.buttons(screen, app), {"watch_replay", "settings", "leave"})
        self.assertEqual(self.stats, app.stats.online_matches)
        # and it stays there (in 1.3 the game went straight to the main menu)
        self.assertIs(self.frame(), screen)
        self.assertIs(self.frame(), screen)

    def test_host_goes_quiet(self):
        self.net.status, self.net.reason = "lost", "Lost touch with the host."
        screen = self.frame()
        self.assertEqual((screen.NAME, screen.left), ("guest_result", "Lost touch with your friend."))


if __name__ == "__main__":
    unittest.main()

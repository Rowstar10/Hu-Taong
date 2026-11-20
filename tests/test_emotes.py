"""Online quick emotes, 1.9 (Rowan's 1.9 plan, phase 3, step 13a).

"Online quick emotes ("Nice shot!", "Oops", "Good game", laughing Hu Tao, thinking Hu Tao): on keys or
controller buttons; shown near the sender's side; with a cooldown, and a setting to mute the
opponent's emotes."  Keys 1-5, or the controller buttons set in Gameplay settings.  Each side sends its
latest with a running count in every message until the next, so a lost packet doesn't lose it.  (The two
Hu Tao ones are her ghost, as the game draws the ball, laughing and thinking: no stickers.)
"""
import unittest
from types import SimpleNamespace

import pygame

from tests import harness

app = harness.app()

from core import emotes as E                                    # noqa: E402
from core.net import HostSession                                # noqa: E402

emotes = app.emotes
interface = app.settings.interface


class Online(unittest.TestCase):
    """A host on this PC only (no public servers), with its match on screen."""
    def setUp(self):
        app.settings.match.reset()
        app.net = HostSession(app, port = 0, upnp = False)
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        self.game = sm.current().game
        emotes.last_sent = -E.COOLDOWN
        emotes.clear()

    def tearDown(self):
        emotes.clear()
        interface.friend_emotes = True
        app.net.close()
        app.net = None
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def key(self, key):
        emotes.key(pygame.event.Event(pygame.KEYDOWN, key = key, mod = 0, unicode = "", scancode = 0))

    def test_key_1_sends_nice_shot_by_your_side(self):
        self.key(pygame.K_1)
        self.assertEqual(app.net.emote, [1, 0])
        self.assertEqual([b[:2] for b in emotes.bubbles], [[0, 1]], "by your side (the host plays Red)")

    def test_a_wait_before_the_next(self):
        self.key(pygame.K_1)
        self.key(pygame.K_2)
        self.assertEqual(app.net.emote, [1, 0], "too soon")
        emotes.last_sent -= E.COOLDOWN
        self.key(pygame.K_2)
        self.assertEqual(app.net.emote, [2, 1], "the count goes up: the friend sees a new one")

    def test_it_goes_out_in_every_snapshot(self):
        self.key(pygame.K_4)
        sent = []
        app.net.link.send = lambda kind, payload: sent.append(payload)
        app.net.send_snapshot()
        from core.net import unpack_json
        import struct
        seq, size = struct.unpack_from("<IH", sent[-1], 0)
        info = unpack_json(sent[-1][6:6 + size])
        self.assertEqual(info["emote"], [1, 3])
        self.assertIn("chaos", info["info"], "(and whether CHAOS is on, for the friend's achievements)")

    def test_the_friends_shows_by_their_side_once(self):
        emotes.receive(app.net, [1, 4])
        emotes.receive(app.net, [1, 4])               # (the same, in the next message)
        self.assertEqual([b[:2] for b in emotes.bubbles], [[4, 2]])
        emotes.clear()
        emotes.receive(app.net, [2, 2])
        self.assertEqual([b[:2] for b in emotes.bubbles], [[2, 2]])

    def test_muted(self):
        interface.friend_emotes = False
        emotes.receive(app.net, [1, 0])
        self.assertEqual(emotes.bubbles, [])
        self.key(pygame.K_3)
        self.assertEqual(len(emotes.bubbles), 1, "yours still show (and go)")

    def test_a_controller_button(self):
        app.gamepads.add(900, "Xbox 360 Controller")
        try:
            for e in app.gamepads.translate(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, instance_id = 900,
                                                                button = pygame.CONTROLLER_BUTTON_Y)):
                app.state_manager.handle_event(e)
            self.assertEqual(app.net.emote, [1, 0])
        finally:
            app.gamepads.pads.clear()

    def test_bubbles_draw_and_go(self):
        self.key(pygame.K_5)
        emotes.receive(app.net, [1, 3])
        app.renderer.draw_emotes(app.virtual)
        emotes.update(E.SHOW + 0.1)
        self.assertEqual(emotes.bubbles, [])


class Offline(unittest.TestCase):
    def test_nothing_offline(self):
        app.net = None
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        emotes.last_sent = -E.COOLDOWN
        emotes.key(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_1, mod = 0, unicode = "", scancode = 0))
        self.assertEqual(emotes.bubbles, [])
        sm.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_five_with_two_ghosts(self):
        self.assertEqual([t for t, _ in E.EMOTES], ["Nice shot!", "Oops", "Good game", "Hahaha!", "Hmm..."])
        for mood in ("laugh", "think"):
            self.assertGreater(app.art.emote_ghost(64, mood).get_width(), 0)

    def test_buttons_set_in_gameplay(self):
        g = app.settings.gameplay
        self.assertEqual([g.pad_emote_1, g.pad_emote_5], ["y", "rightshoulder"])
        self.assertTrue(g.pads_valid())


if __name__ == "__main__":
    unittest.main()

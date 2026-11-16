"""A smoke test: every screen draws a real frame, the ways in and out of a match work, and a long
computer-v-computer match with every power-up runs without a hitch.  Kept in the repo (1.6) so it
outlives the scratch copies that kept getting cleared away; run it after any change to the screens.
"""
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from core import net as netcode, rooms                          # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402

netcode.STUN_SERVERS = []                    # nothing here may reach the public servers
rooms.BROKERS = [("127.0.0.1", 1)]

sm = app.state_manager


def frames(n = 1):
    for _ in range(n):
        sm.process_changes()
        app.dt = 1 / 60
        app.loop()


def top():
    return getattr(sm.current(), "NAME", "")


def colours():
    """How many different colours the frame has (a blank or broken screen has a handful)."""
    small = pygame.transform.smoothscale(app.virtual, (96, 54))
    return len({small.get_at((x, y))[:3] for x in range(96) for y in range(54)})


def click(key):
    x, y = sm.current().ui_hitboxes[key].center
    pos = (x / app.sx, y / app.sy)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos))


class Screens(unittest.TestCase):
    MENUS = ("main_menu", "settings", "display", "audio", "interface", "gameplay", "powerups", "stats",
             "replays", "background_selection", "match_setup", "online")

    def setUp(self):
        pygame.event.clear()
        app.has_focus = True

    def tearDown(self):
        pygame.event.clear()
        sm.set_state("main_menu", mute = True)
        harness.settle(app)

    def assert_drawn(self, name):
        self.assertEqual(top(), name)
        self.assertGreater(colours(), 60, f"{name} looks blank")
        self.assertTrue(getattr(sm.current(), "ui_hitboxes", None) is not None)

    def test_every_menu_draws(self):
        for name in self.MENUS:
            with self.subTest(name):
                sm.set_state("main_menu", mute = True)
                if name != "main_menu":
                    sm.push_state(name, mute = True)
                frames(40)                                   # past the fade between screens
                self.assert_drawn(name)
                self.assertTrue(sm.current().ui_hitboxes, f"{name} has no buttons")

    def test_into_a_match_and_out_again(self):
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        frames(40)
        self.assert_drawn("game")
        game = sm.current().game
        game.p1.ai_enabled = game.p2.ai_enabled = True
        frames(240)                                          # serve, and a few seconds of play
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_ESCAPE, mod = 0, unicode = "",
                                             scancode = 0))
        frames(20)
        self.assert_drawn("pause")
        click("watch_replay")                                # the match so far, and back
        frames(60)
        self.assert_drawn("replay")
        sm.pop_state(mute = True)
        frames(20)
        self.assertEqual(top(), "pause")
        click("main_menu")                                   # leave the match
        frames(20)
        if top() == "confirm_choice":
            click("confirm")
            frames(20)
        self.assert_drawn("main_menu")
        sm.push_state("game", mute = True)                   # and straight back into a new one
        frames(40)
        self.assert_drawn("game")

    def test_the_end_of_a_match(self):
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        frames(5)
        game = sm.current().game
        sm.push_state("win", p1 = game.p1, p2 = game.p2, winner = game.p1, loser = game.p2, mute = True)
        frames(40)
        self.assert_drawn("win")


class LongMatch(unittest.TestCase):
    """Computer v computer for four minutes of game time, every power-up on, Chaotic."""

    def setUp(self):
        self.g = g = app.settings.gameplay
        g.reset_powerups()
        g.powerup_rate = 3
        g.winning_score_index = g.winning_scores.index("Endless Mode")

    def tearDown(self):
        self.g.reset()
        self.g.reset_powerups()

    def test_every_power_up_and_no_stuck_points(self):
        for wall in (True, False):
            with self.subTest(middle_wall = wall):
                self.g.middle_wall = wall
                game = Hu_Taong(app)
                game.start()
                game.p1.ai_enabled = game.p2.ai_enabled = True
                taken, points, longest, t_point, last = set(), 0, 0.0, 0.0, (0, 0)
                collect = game.powerups.collect

                def noting(item, owner):
                    taken.add(item["kind"])
                    return collect(item, owner)
                game.powerups.collect = noting
                for _ in range(240 * 60):
                    game.update(1 / 60)
                    t_point += 1 / 60
                    score = (game.p1.score, game.p2.score)
                    if score != last:
                        points, last = points + 1, score
                        longest, t_point = max(longest, t_point), 0.0
                game.stop()
                self.assertGreater(points, 4)
                self.assertLess(longest, 90, "a point that never ends")
                self.assertGreater(len(taken), 12, sorted(taken))


if __name__ == "__main__":
    unittest.main()

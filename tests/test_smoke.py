"""A smoke test: every screen draws a real frame, the ways in and out of a match work, and a long
computer-v-computer match with every power-up runs without a hitch, (1.7) another with every
game mode on at once, and (1.8) more under each physics and the Speed Cap.  Kept in the repo (1.6) so it outlives the scratch copies that kept getting
cleared away; run it after any change to the screens.
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
    MENUS = ("main_menu", "settings", "display", "audio", "interface", "gameplay", "match", "ball_paddles",
             "powerups", "stats",
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


# Seconds a computer v computer point may run before it counts as one that never ends.  (90 until
# the 1.8 playtest's stronger Black Hole: about one point in 250 with it then ran just past 90 s,
# longest 93 s in 32 four-minute matches, against 76 s without it.  120 until 1.9, whose AIs go back
# round a ball that got past them: their rallies run longer, a 142 s one once, 60-odd hits a minute.)
LONGEST = 200
# ...and how long a point may go with no paddle touching a ball: a point that never ends is a ball
# stuck somewhere, not a long rally (1.9)
NO_HIT = 30


class Quiet:
    """The longest spell in a match with no paddle touching a ball."""

    def __init__(self, game):
        self.game, self.hits, self.spell, self.longest, self.score = game, 0, 0.0, 0.0, (0, 0)

    def tick(self, dt):
        game = self.game
        hits, score = len(game.recorder.shots), (game.p1.score, game.p2.score)
        if hits != self.hits or score != self.score:
            self.hits, self.score, self.spell = hits, score, 0.0
        self.spell += dt
        self.longest = max(self.longest, self.spell)

class LongMatch(unittest.TestCase):
    """Computer v computer for four minutes of game time, every power-up on, Chaotic."""

    def setUp(self):
        self.g = g = app.settings.match
        g.reset_powerups()
        g.mode_talisman_rush = True                # (CHAOS: talismans every 1.5-3 s, Chaotic, 1.9)
        g.talismans_at_once = len(g.at_once_options) - 1      # (1.8: as many at once as allowed, to see them all)
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
                quiet = Quiet(game)
                collect = game.powerups.collect

                def noting(item, owner):
                    taken.add(item["kind"])
                    return collect(item, owner)
                game.powerups.collect = noting
                for _ in range(240 * 60):
                    game.update(1 / 60)
                    t_point += 1 / 60
                    quiet.tick(1 / 60)
                    score = (game.p1.score, game.p2.score)
                    if score != last:
                        points, last = points + 1, score
                        longest, t_point = max(longest, t_point), 0.0
                game.stop()
                self.assertGreater(points, 4)
                self.assertLess(longest, LONGEST, "a point that never ends")
                self.assertLess(quiet.longest, NO_HIT, "no paddle touched a ball for 30 s: it's stuck")
                self.assertGreater(len(taken), 12, sorted(taken))


class EveryPhysics(unittest.TestCase):
    """1.8: computer v computer under Classic and v0.9 physics, and with the Speed Cap, every
    talisman on, Chaotic, the Middle Wall up and down, recorded and played back as it goes."""

    def setUp(self):
        self.g = g = app.settings.match
        g.reset_powerups()
        g.mode_talisman_rush = True                # (CHAOS: talismans every 1.5-3 s, Chaotic, 1.9)
        g.talismans_at_once = len(g.at_once_options) - 1      # (1.8: as many at once as allowed, to see them all)
        g.winning_score_index = g.winning_scores.index("Endless Mode")

    def tearDown(self):
        self.g.reset()
        self.g.reset_powerups()

    def test_each_physics_with_every_talisman(self):
        from game.replay import ReplayView
        for physics, cap, wall in ((1, False, True), (2, False, False), (0, True, False), (2, True, True)):
            with self.subTest(physics = self.g.PHYSICS[physics], cap = cap, middle_wall = wall):
                self.g.physics, self.g.speed_cap, self.g.middle_wall = physics, cap, wall
                game = Hu_Taong(app)
                game.start()
                game.p1.ai_enabled = game.p2.ai_enabled = True
                taken, points, longest, t_point, last = set(), 0, 0.0, 0.0, (0, 0)
                quiet = Quiet(game)
                collect = game.powerups.collect

                def noting(item, owner):
                    taken.add(item["kind"])
                    return collect(item, owner)
                game.powerups.collect = noting
                for i in range(120 * 60):
                    game.update(1 / 60)
                    game.recorder.capture(1 / 60)
                    if i % 900 == 0:
                        app.renderer.draw_world(app.virtual, game)
                    t_point += 1 / 60
                    quiet.tick(1 / 60)
                    score = (game.p1.score, game.p2.score)
                    if score != last:
                        points, last = points + 1, score
                        longest, t_point = max(longest, t_point), 0.0
                game.stop()
                self.assertGreater(points, 0)                   # (Classic's rallies between computers run long:
                self.assertLess(max(longest, t_point), LONGEST, "a point that never ends")    # 25-60 s a point)
                self.assertLess(quiet.longest, NO_HIT, "no paddle touched a ball for 30 s: it's stuck")
                self.assertGreater(len(taken), 5, sorted(taken))      # (2 minutes, a few at a time)
                view = ReplayView(game.recorder.clip(), app)
                view.show(len(view.clip.frames) - 1)
                app.renderer.draw_world(app.virtual, view)


class EveryMode(unittest.TestCase):
    """1.7: computer v computer with every game mode on at once (each Chaos timing in turn, Switch
    both ways), every talisman, drawn and recorded as it goes."""

    def setUp(self):
        self.g = g = app.settings.match
        g.reset_powerups()
        g.winning_score_index = g.winning_scores.index("Endless Mode")
        for mode in g.MODES:
            setattr(g, "mode_" + mode, True)
        g.switch_timing = 1                       # mid-rally

    def tearDown(self):
        self.g.reset()
        self.g.reset_powerups()

    def test_all_at_once(self):
        from game.replay import ReplayView
        for timing in (0, 1):
            with self.subTest(chaos = self.g.CHAOS_TIMINGS[timing]):
                self.g.chaos_timing = timing
                game = Hu_Taong(app)
                game.start()
                game.p1.ai_enabled = game.p2.ai_enabled = True
                points, longest, t_point, last = 0, 0.0, 0.0, (0, 0)
                quiet = Quiet(game)
                for i in range(120 * 60):
                    game.update(1 / 60)
                    game.recorder.capture(1 / 60)
                    if i % 600 == 0:
                        app.renderer.draw_world(app.virtual, game)
                    t_point += 1 / 60
                    quiet.tick(1 / 60)
                    score = (game.p1.score, game.p2.score)
                    if score != last:
                        points, last = points + 1, score
                        longest, t_point = max(longest, t_point), 0.0
                game.stop()
                self.assertGreater(points, 3)
                self.assertLess(longest, LONGEST, "a point that never ends")
                self.assertLess(quiet.longest, NO_HIT, "no paddle touched a ball for 30 s: it's stuck")
                # (two minutes of this makes 3 to 7 mid-rally switches, by chance: it once made 2, in
                # 1.8's full run, and the test fell over.  What matters is that they happen.)
                self.assertGreater(game.switches, 0, "no switches")
                view = ReplayView(game.recorder.clip(), app)
                view.show(len(view.clip.frames) - 1)
                app.renderer.draw_world(app.virtual, view)


if __name__ == "__main__":
    unittest.main()

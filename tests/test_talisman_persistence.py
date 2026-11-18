"""Talismans across points, and how many at once, 1.8 (Rowan's 1.8 plan, phase 2, 2026-11-18).

Rowan's decisions:
- Giant Paddle, Swift Step, Spirit Fire and Shrink Curse persist between points with the time they
  had left (their clocks used to run on through the point's announcement).
- Lantern Night lasts 20 s of play, and stays between points; dawn comes when its time is up.
- Talismans waiting on the court last 20 s of play (14 s before) and stay through points.
- Soul Swap ends with the point, and puts the players back on their own paddles for the next
  serve; in a Switch match the switch goes on from where they are instead.
- Sticky Goo lets the ball go a little slower (75% of its speed, from 85%).
- Talismans at Once (Match settings, 1 to 3, 1 by default) limits the talismans in play: their
  effects and any waiting on the court.  Safety Teleport, Double or Nothing, Lantern Night and
  Open Court don't count, nor do game modes; Talisman Rush lifts the limit.
"""
import unittest

from tests import harness

app = harness.app()

from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import BY_KEY, PowerUps                      # noqa: E402

m = app.settings.match


class Match(unittest.TestCase):
    RULES = {}

    def setUp(self):
        m.reset()
        for name, value in self.RULES.items():
            setattr(m, name, value)
        app.keys_down.clear()
        self.game = Hu_Taong(app)
        self.game.start()
        self.game.countdown, self.game.paused = None, False
        self.pu = self.game.powerups
        self.pu.wait = 999.0
        self.p1, self.p2 = self.game.p1, self.game.p2
        self.p1.ai_enabled = self.p2.ai_enabled = False             # (the AI would go and take talismans)

    def tearDown(self):
        self.game.stop()
        m.reset()

    def take(self, key, owner = None):
        self.pu.collect({"kind": key, "x": 900, "y": 500}, owner or self.p1)

    def point_over(self):
        g = self.game
        g.on_score(g.ball, {"normal": (1, 0)})

    def through_the_announcement(self):
        g = self.game
        while g.message_timer > 0:
            g.update(1 / 60)

    def play(self, seconds):
        g = self.game
        g.countdown, g.paused = None, False
        for _ in range(round(seconds * 60)):
            g.ball.vx = g.ball.vy = 0.0                             # (no points meanwhile)
            g.update(1 / 60)


class Persisting(Match):
    def test_boons_and_curses_keep_their_time(self):
        for key in ("giant", "swift", "fire"):
            self.take(key)
        self.take("shrink")                                        # (on the other player)
        self.play(3.0)
        before = (dict(self.p1.effects), dict(self.p2.effects))
        self.point_over()
        self.through_the_announcement()
        self.assertEqual((self.p1.effects, self.p2.effects), before, "their clocks ran between points")
        self.assertEqual(set(self.p1.effects), {"giant", "swift", "fire"})
        self.assertIn("shrink", self.p2.effects)
        self.play(1.0)
        self.assertLess(self.p1.effects["giant"], before[0]["giant"] - 0.9, "and run again in play")

    def test_lantern_night_lasts_20_seconds_of_play_and_stays_between_points(self):
        self.take("lantern")
        self.play(5.0)
        self.point_over()
        self.through_the_announcement()
        self.assertEqual(self.pu.lantern_level(), 1.0, "it's still night for the next serve")
        self.assertAlmostEqual(self.pu.lantern["left"], 15.0, delta = 0.1)
        self.play(15.2)
        self.assertIsNotNone(self.pu.lantern["lifting"], "dawn comes when its time is up")
        self.play(1.5)
        self.assertIsNone(self.pu.lantern)
        self.assertEqual(BY_KEY["lantern"].seconds, 20)

    def test_talismans_on_the_court_stay_through_points(self):
        self.pu.spawn("giant")
        self.pu.pickups[0].update(x = 960, y = 140)                 # out of everyone's way
        self.game.ball.vx = self.game.ball.vy = 0.0
        self.play(4.0)
        age = self.pu.pickups[0]["age"]
        self.point_over()
        self.through_the_announcement()
        self.assertEqual([i["kind"] for i in self.pu.pickups], ["giant"])
        self.assertEqual(self.pu.pickups[0]["age"], age)
        self.assertEqual(PowerUps.LIFETIME, 20.0)

    def test_what_acts_on_the_court_still_ends_with_the_point(self):
        for key in ("ghost", "wind", "blink", "curve", "double", "cracker"):
            self.take(key)
        self.point_over()
        self.assertFalse(any((self.pu.ghost, self.pu.wind, self.pu.blink, self.pu.curve_on, self.pu.double,
                              self.pu.cracker)))

    def test_goo_lets_go_slower(self):
        self.assertEqual(PowerUps.STICK_SPEED, 0.75)


class SoulSwapUndone(Match):
    def soul_swap(self, times):
        g, ball = self.game, self.game.ball
        self.take("swap")
        for _ in range(times):
            g.switch_warning = g.SWITCH_GRACE + 0.1
            g.on_hit(ball, self.p1, {"normal": (-1, 0)})

    def test_back_on_your_own_paddle_for_the_next_serve(self):
        keys, colour = self.p1.up, self.p1.colour
        self.soul_swap(1)
        self.assertNotEqual(self.p1.up, keys, "(it swapped)")
        self.point_over()
        self.through_the_announcement()
        self.assertEqual((self.p1.up, self.p1.colour), (keys, colour))

    def test_twice_is_already_home(self):
        keys = self.p1.up
        self.soul_swap(2)
        self.point_over()
        self.through_the_announcement()
        self.assertEqual(self.p1.up, keys)


class SoulSwapInASwitchMatch(Match):
    RULES = {"mode_switch": True, "switch_timing": 0}

    def test_the_switch_goes_on_from_where_they_are(self):
        keys = self.p1.up
        self.take("swap")
        g = self.game
        g.switch_warning = g.SWITCH_GRACE + 0.1
        g.on_hit(g.ball, self.p1, {"normal": (-1, 0)})
        swapped = self.p1.up
        self.assertNotEqual(swapped, keys)
        self.point_over()
        self.through_the_announcement()
        self.assertEqual(self.p1.up, keys, "one switch on from where they were (not undone, then switched)")


class AtOnce(Match):
    def test_one_by_default(self):
        self.assertEqual(m.at_once_options[m.talismans_at_once], 1)
        self.assertTrue(self.pu.room())
        self.take("giant")
        self.assertFalse(self.pu.room(), "a Boon in play leaves no room")

    def test_a_talisman_waiting_counts(self):
        self.pu.spawn("ghost")
        self.assertFalse(self.pu.room())

    def test_these_dont_count(self):
        for key in ("teleport", "double", "lantern", "wall"):
            self.take(key)
        self.pu.spawn("double")
        self.assertTrue(self.pu.room())

    def test_more_when_set(self):
        self.game.settings.talismans_at_once = 1                    # (two)
        self.take("giant")
        self.assertTrue(self.pu.room())
        self.take("ghost")
        self.assertFalse(self.pu.room())

    def test_game_modes_dont_count(self):
        self.game.settings.mode_twin_ball = True
        self.pu.twin_serve()
        self.assertTrue(self.pu.room())

    def test_no_more_turn_up_than_allowed(self):
        self.pu.wait = 0.0
        for _ in range(400):
            self.pu.update(0.05)
            waiting = [i for i in self.pu.pickups if i["kind"] not in PowerUps.NOT_COUNTED]
            self.assertLessEqual(self.pu.in_play() + len(waiting), 1)


class AtOnceInATalismanRush(Match):
    RULES = {"mode_talisman_rush": True}

    def test_no_limit(self):
        for key in ("giant", "ghost", "wind", "blink"):
            self.take(key)
        self.assertTrue(self.pu.room())


class Settings(unittest.TestCase):
    def tearDown(self):
        m.reset()

    def test_saved(self):
        from core import save_data
        m.talismans_at_once = 2
        save_data.save(app)
        m.reset()
        save_data.load(app)
        self.assertEqual(m.at_once_options[m.talismans_at_once], 3)

    def test_on_the_match_screen(self):
        import pygame
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("match", mute = True)
        harness.settle(app)
        screen = sm.current()
        screen.draw(app.virtual)
        x, y = screen.ui_hitboxes["cycle_at_once_right"].center
        pos = (x / app.sx, y / app.sy)
        screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
        self.assertEqual(m.talismans_at_once, 1)
        sm.set_state("main_menu", mute = True)
        harness.settle(app)


if __name__ == "__main__":
    unittest.main()

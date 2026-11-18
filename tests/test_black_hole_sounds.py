"""Black holes are heard, 1.8 (Rowan's third 1.8 playtest, 2026-11-18).

"Make them have SOUND while they are on the court, and especially when the collapse animation plays."
A low hum while a black hole is on the court, louder as the Black Hole grows (a mini one hums softly);
a deep "whoomp" as one swallows a ball; and a roar spinning up through the collapse, ending in a boom
as it bursts.  It's all heard from the holes as they're shown, so the match, the friend's screen online
and replays sound alike; when nothing plays them on (paused, a menu), the hum fades away.  The sounds
were synthesised for the game (see CREDITS.md).
"""
import random
import time
import unittest
import wave
from array import array

from tests import harness

app = harness.app()

from config import SOUND_DIR                                    # noqa: E402
from core.hole_sounds import COLLAPSE, HUM, SWALLOW, HoleSounds  # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.powerups import PowerUps                              # noqa: E402

P = PowerUps
m = app.settings.match


def hole(**k):
    return dict(dict(x = 960.0, y = 540.0, kind = P.HOLE_TALISMAN, age = 5.0, power = 1.0, spin = 1, way = None,
                     flash = 0.0, dying = None, size = 1.0, collapse = None), **k)


class Heard(unittest.TestCase):
    def setUp(self):
        self.sound = app.sound_manager
        self.played = []
        real = self.sound.play
        self.sound.play = lambda name, *a, **k: (self.played.append(name), real(name, *a, **k))[1]
        self.addCleanup(lambda: setattr(self.sound, "play", real))
        self.ears = HoleSounds(self.sound)
        self.addCleanup(self.ears.quiet)

    def hear(self, holes, frames = 1):
        for _ in range(frames):
            self.ears.heard = (self.ears.heard or time.perf_counter()) - 1 / 60     # (a frame on)
            self.ears.hear(holes)

    def test_the_sounds_are_there(self):
        for name in (HUM, SWALLOW, COLLAPSE):
            with wave.open(str(SOUND_DIR / name)) as w:
                self.assertGreater(w.getnframes(), 0)

    def test_the_hum_loops_without_a_seam(self):
        with wave.open(str(SOUND_DIR / HUM)) as w:
            samples = array("h", w.readframes(w.getnframes()))
        steps = [abs(b - a) for a, b in zip(samples, samples[1:])]
        self.assertLess(abs(samples[0] - samples[-1]), max(steps) * 1.5)

    def test_a_hum_while_one_is_on_the_court(self):
        self.hear([hole()], frames = 60)
        self.assertGreater(self.ears.level, 0.25)
        if self.ears.hum is None:
            self.skipTest("no sound here")
        self.assertTrue(self.ears.hum.get_busy())

    def test_louder_as_it_grows_and_softly_for_a_mini_one(self):
        self.hear([hole()], frames = 120)
        small = self.ears.level
        self.hear([hole(size = 1 + P.HOLE_GROW * P.HOLE_GROWTHS)], frames = 120)
        self.assertGreater(self.ears.level, small * 1.6)
        self.hear([hole(kind = P.HOLE_MINI)], frames = 240)
        self.assertLess(self.ears.level, small / 2)

    def test_it_fades_away_when_nothing_plays_the_holes_on(self):
        self.hear([hole()], frames = 30)
        self.ears.heard -= 1.0                                   # (paused, or a menu)
        self.ears.tick()
        self.assertIsNone(self.ears.hum)
        self.assertEqual(self.ears.level, 0.0)

    def test_and_when_the_holes_go(self):
        self.hear([hole()], frames = 30)
        self.hear([hole(dying = 0.5)], frames = 120)
        self.assertIsNone(self.ears.hum)

    def test_a_whoomp_as_one_swallows_a_ball(self):
        self.hear([hole()], frames = 5)
        self.hear([hole(flash = 1.0)])
        self.hear([hole(flash = 0.98)], frames = 10)
        self.assertEqual(self.played.count(SWALLOW), 1)

    def test_a_roar_as_it_collapses_once(self):
        self.hear([hole(size = 2.0)], frames = 5)
        for i in range(90):
            self.hear([hole(size = 2.0, collapse = i / 60)])
        self.assertEqual(self.played.count(COLLAPSE), 1)

    def test_not_from_half_way_through_one(self):
        """(A replay jumped to the middle of a collapse doesn't start its roar from the beginning.)"""
        self.hear([hole(size = 2.0, collapse = 0.8)], frames = 10)
        self.assertNotIn(COLLAPSE, self.played)

    def test_drifting_holes_are_still_the_same_holes(self):
        for i in range(120):
            self.hear([hole(x = 800.0 + i * 1.2, flash = 0.0)])
        self.assertEqual(self.played, [])


class InAMatch(unittest.TestCase):
    """The match plays the holes on to them as it goes (and replays and the friend's screen do too:
    core/states/replay_state.py and guest_state.py)."""

    def test_a_black_hole_match_hums(self):
        random.seed(3)
        m.reset()
        m.mode_black_hole = True
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        try:
            ears = app.sound_manager.holes
            game = sm.current().game
            game.countdown, game.paused = None, False
            heard = ears.heard
            for _ in range(5):
                sm.current().update(1 / 60)
            self.assertNotEqual(ears.heard, heard)
            self.assertGreater(ears.level, 0.0)
        finally:
            sm.set_state("main_menu", mute = True)
            harness.settle(app)
            m.reset()
            app.sound_manager.holes.quiet()


if __name__ == "__main__":
    unittest.main()

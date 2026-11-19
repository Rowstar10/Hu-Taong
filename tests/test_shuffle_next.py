"""Next on Shuffle picks a random track, 1.9 (Rowan, 2026-11-19).

"Clicking the next track button when it's on shuffle should choose a random track, but it chooses
the next one in the list."  On Shuffle, Next plays a random track (never the one on now); in order,
or on Loop, it's still the next one in the list.
"""
import random
import unittest
from types import SimpleNamespace

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from core.states.jukebox import JukeboxControls                 # noqa: E402

sound = app.sound_manager
audio = app.settings.audio


class NextOnShuffle(unittest.TestCase):
    def setUp(self):
        self.kept = (audio.play_mode, sound.mood, sound.now_playing, sound.play_music)
        self.played = []
        sound.play_music = lambda music: (self.played.append(music), setattr(sound, "now_playing", music))
        sound.mood = "game"
        sound.now_playing = sound.pool[0]

    def tearDown(self):
        audio.play_mode, sound.mood, sound.now_playing, sound.play_music = self.kept

    def press_next(self, times):
        me = SimpleNamespace(app = app)
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = (0, 0))
        for _ in range(times):
            JukeboxControls.handle_jukebox(me, click, "cycle_music_right")

    def test_on_shuffle_its_random(self):
        audio.play_mode = 1
        random.seed(19)
        pool = sound.pool
        self.press_next(30)
        in_order = [pool[(pool.index(a) + 1) % len(pool)] for a in [pool[0]] + self.played[:-1]]
        self.assertNotEqual(self.played, in_order, "not just the next in the list")
        self.assertGreater(len(set(self.played)), 5)
        for before, after in zip([pool[0]] + self.played, self.played):
            self.assertNotEqual(before, after, "never the one already on")

    def test_in_order_and_on_loop_its_the_next(self):
        for mode in (0, 2):
            with self.subTest(mode = ("in order", "shuffle", "loop")[mode]):
                audio.play_mode = mode
                pool = sound.pool
                sound.now_playing = pool[0]
                self.played.clear()
                self.press_next(3)
                self.assertEqual(self.played, pool[1:4])


if __name__ == "__main__":
    unittest.main()

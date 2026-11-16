"""Mute buttons by the volume sliders, 1.6 (Rowan's playtest list, 2026-11-16).

Each of Master, Music and SFX Volume has a Mute button.  Muting silences it but leaves the slider
where it was, so unmuting brings back that level; the mute is saved between sessions.
"""
import json
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from core import save_data                                      # noqa: E402

sound = app.sound_manager


class MuteButtons(unittest.TestCase):
    def setUp(self):
        sound.reset()
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("audio", mute = True)
        harness.settle(app)
        self.screen = sm.current()

    def tearDown(self):
        sound.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def click(self, key):
        self.screen.draw(app.virtual)
        x, y = self.screen.ui_hitboxes[key].center
        pos = (x / app.sx, y / app.sy)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos))

    def test_every_volume_slider_has_a_mute_button(self):
        self.screen.draw(app.virtual)
        for name in ("master", "music", "sfx"):
            self.assertIn(f"mute_{name}_volume", self.screen.ui_hitboxes)

    def test_mute_silences_and_unmute_brings_the_level_back(self):
        sound.music_volume = 0.37
        self.click("mute_music_volume")
        self.assertTrue(sound.music_muted)
        self.assertEqual(sound.level("music"), 0.0, "silent while muted")
        self.assertEqual(sound.music_volume, 0.37, "the slider keeps its place")
        self.assertGreater(sound.level("sfx"), 0, "the others play on")
        self.click("mute_music_volume")
        self.assertFalse(sound.music_muted)
        self.assertEqual(sound.level("music"), 0.37)

    def test_master_mute_silences_everything(self):
        self.click("mute_master_volume")
        self.assertEqual(sound.gain(sound.level("music")), 0.0)
        self.assertEqual(sound.gain(sound.level("sfx")), 0.0)
        self.assertIsNone(sound.play("countdown_tick.wav"))

    def test_sfx_mute_stops_effects(self):
        self.click("mute_sfx_volume")
        self.assertIsNone(sound.play("countdown_tick.wav"))

    def test_moving_a_muted_slider_unmutes_it(self):
        self.click("mute_sfx_volume")
        self.click("sfx_volume_slider")
        self.assertFalse(sound.sfx_muted)

    def test_reset_unmutes(self):
        self.click("mute_master_volume")
        self.click("reset_master_volume")
        self.assertFalse(sound.master_muted)


class Saved(unittest.TestCase):
    def tearDown(self):
        sound.reset()

    def test_mute_is_saved_between_sessions(self):
        sound.music_volume, sound.music_muted = 0.6, True
        save_data.save(app)
        sound.reset()
        save_data.load(app)
        self.assertTrue(sound.music_muted)
        self.assertEqual(sound.music_volume, 0.6)
        self.assertFalse(sound.master_muted or sound.sfx_muted)

    def test_a_save_from_before_mute_buttons_loads_unmuted(self):
        data = save_data.collect(app)
        for name in ("master_muted", "sfx_muted", "music_muted"):
            del data["sound"][name]
        save_data.save_path().parent.mkdir(parents = True, exist_ok = True)
        save_data.save_path().write_text(json.dumps(data))
        sound.sfx_muted = True
        save_data.load(app)
        self.assertTrue(sound.sfx_muted, "nothing in the old save changes it")
        sound.reset()
        save_data.load(app)
        self.assertFalse(sound.sfx_muted)


if __name__ == "__main__":
    unittest.main()

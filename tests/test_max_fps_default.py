"""Max FPS starts at the screen's refresh rate, 1.6 (Rowan's playtest, 2026-11-17).

New settings used to start at 120 whatever the screen.  Now they start at the main screen's refresh
rate (the next option up if it isn't one of them), or 60 if it can't be told.  A saved choice,
Unlimited included, is kept as it is.
"""
import json
import os
import unittest
from unittest import mock

from tests import harness

app = harness.app()

from core import platform, save_data, settings                  # noqa: E402

display = app.settings.display
OPTIONS = display.max_fps_options


def chosen():
    return OPTIONS[display.max_fps]


class FromTheScreen(unittest.TestCase):
    def tearDown(self):
        display.reset()

    def test_each_screen_gets_its_rate_or_the_next_one_up(self):
        for hz, fps in ((60, 60), (59, 60), (75, 120), (90, 120), (100, 120), (119, 120), (120, 120),
                        (143, 144), (144, 144), (165, 165), (180, 240), (240, 240), (360, "Unlimited"),
                        (None, 60)):
            with self.subTest(hz = hz):
                self.assertEqual(OPTIONS[display.fps_for_screen(hz)], fps)

    def test_new_settings_start_at_the_screens_rate(self):
        for hz, fps in ((144, 144), (60, 60), (None, 60)):
            with mock.patch.object(settings, "refresh_rate", return_value = hz):
                display.reset()
            self.assertEqual(chosen(), fps, f"a {hz} Hz screen")

    def test_this_pc_can_tell(self):
        """Windows answers on any PC this runs on (the tests run on Rowan's): a whole number of Hz."""
        hz = platform.refresh_rate()
        if hz is None:
            self.skipTest("no refresh rate from this system")
        self.assertIsInstance(hz, int)
        self.assertGreater(hz, 20)


class SavedChoicesKept(unittest.TestCase):
    def tearDown(self):
        display.reset()

    def load_with(self, saved_display, hz):
        data = save_data.collect(app)
        data["display"] = saved_display
        save_data.save_path().parent.mkdir(parents = True, exist_ok = True)
        save_data.save_path().write_text(json.dumps(data))
        with mock.patch.object(settings, "refresh_rate", return_value = hz):
            display.reset()
            save_data.load(app)

    def test_unlimited_stays_unlimited(self):
        self.load_with({"max_fps": OPTIONS.index("Unlimited")}, 60)
        self.assertEqual(chosen(), "Unlimited")

    def test_the_released_1_6_save_keeps_its_120(self):
        with open(os.path.join(harness.GAME, "tests", "data", "save_1.6.json"), encoding = "utf-8") as f:
            saved = json.load(f)
        self.load_with(saved["display"], 144)
        self.assertEqual(chosen(), 120)

    def test_a_save_without_one_takes_the_screens_rate(self):
        self.load_with({"show_fps": False}, 144)
        self.assertEqual(chosen(), 144)


if __name__ == "__main__":
    unittest.main()

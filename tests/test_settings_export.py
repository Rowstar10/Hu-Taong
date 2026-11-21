"""Export and import every setting, 1.9 (Rowan, 2026-11-20: "Add an option to import/export all
settings in the settings menu").

Settings has Export and Import beside Reset All Settings.  The file holds the save's own
settings sections (so any version can read it), not the stats, and never your own server's login
(a file may be shared).  Importing asks first, then replaces the settings here with the file's
(anything unknown or out of range is left out, as with a damaged save).
"""
import json
import pathlib
import tempfile
import unittest

import pygame

from tests import harness

app = harness.app()

from core import save_data                                      # noqa: E402
from tests.test_settings_menus import click, open_screen        # noqa: E402

s = app.settings


class ExportImport(unittest.TestCase):
    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.path = self.folder / "Hu Taong settings.json"
        self.real = app.choose_file
        app.choose_file = lambda save, title, name, kinds: self.path

    def tearDown(self):
        app.choose_file = self.real
        app.reset_all_settings()
        s.online.own_server, s.online.server_user, s.online.server_password = False, "", ""
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_on_the_settings_screen(self):
        screen = open_screen("settings")
        for key in ("export_settings", "import_settings", "reset_all"):
            self.assertIn(key, screen.ui_hitboxes)

    def test_a_round_trip(self):
        s.match.winning_score_index, s.match.mode_black_hole = 4, True
        s.display.court_dim_level, s.display.show_ping = 0.2, False
        s.gameplay.bind("p1_up", pygame.K_i)
        s.gameplay.pad_stick, s.interface.auto_pause = 0, False
        app.sound_manager.music_volume = 0.3
        screen = open_screen("settings")
        click(screen, "export_settings")
        self.assertTrue(self.path.exists())

        app.reset_all_settings()
        self.assertNotEqual(s.match.winning_score_index, 4)
        screen = open_screen("settings")
        click(screen, "import_settings")
        harness.settle(app)
        confirm = app.state_manager.current()
        self.assertEqual(confirm.NAME, "confirm_choice", "it asks first")
        confirm.action()
        harness.settle(app)
        self.assertEqual((s.match.winning_score_index, s.match.mode_black_hole), (4, True))
        self.assertEqual((s.display.court_dim_level, s.display.show_ping), (0.2, False))
        self.assertEqual((s.gameplay.p1_up, s.gameplay.pad_stick, s.interface.auto_pause), (pygame.K_i, 0, False))
        self.assertAlmostEqual(app.sound_manager.music_volume, 0.3)

    def test_no_stats_and_no_login_in_the_file(self):
        s.online.own_server, s.online.server_address = True, "example.com"
        s.online.server_user, s.online.server_password = "rowan", "secret"
        data = json.loads(save_data.export_settings_text(app))
        self.assertNotIn("stats", data)
        self.assertNotIn("server_password", data["online"])
        self.assertNotIn("server_user", data["online"])
        self.assertEqual(data["online"]["server_address"], "example.com")
        self.assertEqual(data["kind"], save_data.SETTINGS_KIND)

    def test_not_a_settings_file(self):
        self.assertIsNone(save_data.read_settings_export("not json"))
        self.assertIsNone(save_data.read_settings_export(json.dumps({"kind": "hu-taong-stats", "stats": {}})))
        self.assertIsNotNone(save_data.read_settings_export(json.dumps({"display": {"show_fps": False}})),
                             "a save.json will do")

    def test_nonsense_is_left_out(self):
        data = {"kind": save_data.SETTINGS_KIND, "display": {"court_dim_level": 7, "show_fps": "yes"},
                "gameplay": {"winning_score_index": -3, "made_up": 1}}
        save_data.apply_settings(app, save_data.read_settings_export(json.dumps(data)))
        self.assertLessEqual(s.display.court_dim_level, 1)
        self.assertIsInstance(s.display.show_fps, bool)
        self.assertGreaterEqual(s.match.winning_score_index, 0)


if __name__ == "__main__":
    unittest.main()

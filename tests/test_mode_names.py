"""Three game modes renamed, and CHAOS's talismans always at Chaotic, 1.9 (Rowan, 2026-11-18).

"Rename the game modes: Chaos -> Shape Shift, Switch -> Soul Swap, Talisman Rush -> CHAOS", each now
named like the talisman it's based on (or, for CHAOS, what it brings).  Their settings keep their old
names in the save, so every version still reads it.  Then "make CHAOS mode's talisman spawn rate fixed
at Chaotic (1.5-3 s), and remove the Chaotic option from the manual spawn rate selector": a save with
Chaotic set loads as Frequent.
"""
import json
import unittest

from tests import harness

app = harness.app()

from core import save_data                                      # noqa: E402
from tests.test_settings_menus import open_screen               # noqa: E402

m = app.settings.match


class Names(unittest.TestCase):
    def tearDown(self):
        m.reset()

    def test_the_new_names(self):
        self.assertEqual((m.MODE_NAMES["chaos"], m.MODE_NAMES["switch"], m.MODE_NAMES["talisman_rush"]),
                         ("Shape Shift", "Soul Swap", "CHAOS"))

    def test_their_tooltips(self):
        from render.renderer import Renderer
        tips = Renderer.MODE_TIPS
        for key, name in (("chaos", "Shape Shift"), ("switch", "Soul Swap"), ("talisman_rush", "CHAOS")):
            self.assertEqual(tips[key].split("\n")[0], name)
        self.assertIn("1.5 to 3 seconds", tips["talisman_rush"])

    def test_the_match_screen_draws_with_them_on(self):
        m.mode_chaos, m.chaos_timing, m.mode_switch, m.switch_timing, m.mode_talisman_rush = True, 1, True, 1, True
        keys = open_screen("match").ui_hitboxes
        for key in ("cycle_mode_chaos", "cycle_mode_switch", "toggle_mode_talisman_rush"):
            self.assertIn(key, keys)

    def test_the_saved_settings_keep_their_names(self):
        gameplay = save_data.collect(app)["gameplay"]
        for key in ("mode_chaos", "mode_switch", "mode_talisman_rush"):
            self.assertIn(key, gameplay)


class SpawnRate(unittest.TestCase):
    def tearDown(self):
        m.reset_powerups()

    def test_no_chaotic_on_the_spawn_rate(self):
        self.assertEqual(m.powerup_rate_options, ["Rare", "Normal", "Frequent"])

    def test_a_save_with_chaotic_loads_as_frequent(self):
        path = save_data.save_path()
        kept = path.read_text() if path.exists() else None
        try:
            data = save_data.collect(app)
            data["gameplay"]["powerup_rate"] = 3
            path.parent.mkdir(parents = True, exist_ok = True)
            path.write_text(json.dumps(data))
            m.reset_powerups()
            save_data.load(app)
            self.assertEqual(m.powerup_rate, 2)
        finally:
            if kept is None:
                path.unlink()
            else:
                path.write_text(kept)


if __name__ == "__main__":
    unittest.main()

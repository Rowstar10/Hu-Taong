"""Talisman stats, 1.9 (Rowan's 1.9 plan, phase 2, step 9).

"Talisman stats per talisman: appearances, pickups, and who wins the point while it's active.  Shown
on the existing talisman page.  Online counts on each player's own stats."  Each talisman counts the
times it turned up, the times it was taken, and the points won and lost by whoever took it (the
point it was taken in).  They're counted from the match's events, the same ones the friend's screen
gets online, so each player's own stats count their own matches.  Practice and replays don't count.
They're kept in a file of their own: older versions rewrite save.json with only what they know.
"""
import json
import unittest
from types import SimpleNamespace

from tests import harness

app = harness.app()

from core import save_data                                      # noqa: E402
from core.states.guest_state import GuestMatchState             # noqa: E402
from core.stats import Stats                                    # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402
from game.replay import KIND_KEYS                               # noqa: E402

m = app.settings.match
stats = app.stats


def match(**rules):
    m.reset()
    for name, value in rules.items():
        setattr(m, name, value)
    g = Hu_Taong(app)
    g.tally = stats.tally
    stats.new_match()
    g.start()
    g.countdown, g.paused = None, False
    return g


class Counting(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def tearDown(self):
        stats.reset()
        m.reset()

    def test_turned_up_taken_and_the_point(self):
        g = match(powerups = True)
        g.powerups.spawn("giant")
        self.assertEqual(stats.talismans["giant"][:2], [1, 0])
        item = g.powerups.pickups[-1]
        g.powerups.collect(item, g.p1)
        self.assertEqual(stats.talismans["giant"][:2], [1, 1])
        g.on_score(g.ball, {"normal": (-1, 0)})            # into Blue's goal: Red, who took it, wins it
        self.assertEqual(stats.talismans["giant"], [1, 1, 1, 0])
        g.stop()

    def test_the_takers_point_lost(self):
        g = match(powerups = True)
        g.powerups.spawn("fire")
        g.powerups.collect(g.powerups.pickups[-1], g.p2)
        g.on_score(g.ball, {"normal": (-1, 0)})            # Red scores: Blue took it and lost the point
        self.assertEqual(stats.talismans["fire"], [1, 1, 0, 1])
        g.on_score(g.ball, {"normal": (-1, 0)})
        self.assertEqual(stats.talismans["fire"], [1, 1, 0, 1], "only the point it was taken in")
        g.stop()

    def test_practice_doesnt_count(self):
        g = match(powerups = True, practice = True)
        g.powerups.spawn("giant")
        g.powerups.collect(g.powerups.pickups[-1], g.p1)
        self.assertEqual(stats.talismans, {})
        g.stop()

    def test_a_match_no_one_keeps_score_of_doesnt_count(self):
        m.reset()
        m.powerups = True
        g = Hu_Taong(app)                                   # (no tally: as in the tests, or a replay)
        g.start()
        g.powerups.spawn("giant")
        self.assertEqual(stats.talismans, {})
        g.stop()

    def test_online_the_friend_counts_the_hosts_events(self):
        """The friend's screen counts the same events, as they arrive, each once."""
        me = SimpleNamespace(app = app, view = SimpleNamespace(kind = lambda i: KIND_KEYS[int(i)]),
                             pending = [], net = SimpleNamespace(played = 0, snaps = []))
        hole = KIND_KEYS.index("hole")
        events = [[1, "spawn", hole], [2, "pickup", hole, 2], [3, "score", 2]]
        me.net.snaps = [(0.0, b"", {"events": events}, None)] * 3       # (repeated in several packets)
        GuestMatchState.take_events(me)
        GuestMatchState.take_events(me)
        self.assertEqual(stats.talismans["hole"], [1, 1, 1, 0])


class Shown(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def tearDown(self):
        stats.reset()

    def test_its_line(self):
        self.assertIn("not seen", stats.talisman_line("giant"))
        stats.talismans["giant"] = [12, 9, 6, 3]
        line = stats.talisman_line("giant")
        for words in ("turned up 12 times", "taken 9", "won 6 of the 9 points"):
            self.assertIn(words, line)

    def test_on_the_talisman_page(self):
        stats.talismans["giant"] = [12, 9, 6, 3]
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("powerups", mute = True)
        harness.settle(app)
        screen = sm.current()
        drawn = []
        real = app.renderer.ui.text
        app.renderer.ui.text = lambda font, text, colour: (drawn.append(text), real(font, text, colour))[1]
        try:
            screen.pu_hover = "giant"
            screen.draw(app.virtual)
            screen.pu_hover = "giant"
            screen.draw(app.virtual)
        finally:
            app.renderer.ui.text = real
        self.assertIn(stats.talisman_line("giant"), drawn)
        sm.set_state("main_menu", mute = True)
        harness.settle(app)


class Kept(unittest.TestCase):
    def setUp(self):
        stats.reset()

    def tearDown(self):
        stats.reset()

    def test_saved_in_a_file_of_their_own(self):
        stats.talismans["giant"] = [3, 2, 1, 1]
        save_data.save(app)
        self.assertEqual(json.loads(save_data.talismans_path().read_text())["giant"], [3, 2, 1, 1])
        self.assertNotIn("talismans", json.loads(save_data.save_path().read_text()).get("stats", {}))
        stats.reset()
        save_data.load(app)
        self.assertEqual(stats.talismans["giant"], [3, 2, 1, 1])

    def test_an_older_version_saving_cant_lose_them(self):
        stats.talismans["giant"] = [3, 2, 1, 1]
        save_data.save(app)
        data = json.loads(save_data.save_path().read_text())
        save_data.save_path().write_text(json.dumps(data))      # (1.8 rewriting save.json its own way)
        stats.reset()
        save_data.load(app)
        self.assertEqual(stats.talismans["giant"], [3, 2, 1, 1])

    def test_nonsense_is_dropped(self):
        stats.load_talismans({"giant": [1, 2, 3, 4], "nope": [1, 1, 1, 1], "fire": [1, -2, 0, 0], "hole": "x"})
        self.assertEqual(stats.talismans, {"giant": [1, 2, 3, 4]})

    def test_export_and_import_carry_them(self):
        stats.talismans["giant"] = [3, 2, 1, 1]
        text = stats.export_text()
        self.assertEqual(Stats.read_export_talismans(text), {"giant": [3, 2, 1, 1]})
        self.assertIsNotNone(Stats.read_export(text))

    def test_reset_clears_them(self):
        stats.talismans["giant"] = [3, 2, 1, 1]
        stats.reset()
        self.assertEqual(stats.talismans, {})


if __name__ == "__main__":
    unittest.main()

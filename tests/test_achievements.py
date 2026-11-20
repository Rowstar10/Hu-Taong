"""Achievements, 1.9 (Rowan's 1.9 plan, phase 2, step 10: the 21 Rowan OK'd, "Build them").

Each is earned from the match's events (the same ones the friend's screen gets online) or from how a
match ends.  "You" are the paddle with no AI (online, your own); two players on one keyboard earn the
ones that aren't about winning.  Practice, replays and computer v computer never count.  An
achievement earned shows a banner with a chime and is saved at once, in a file of its own.
"""
import json
import unittest

from tests import harness

app = harness.app()

from core import achievements as A                              # noqa: E402
from core import save_data                                      # noqa: E402
from core.states.game_state import GameState                    # noqa: E402
from game.courts import COURTS                                  # noqa: E402
from game.powerups import KINDS, PowerUps                       # noqa: E402
from game.replay import KIND_KEYS                               # noqa: E402

m = app.settings.match
ach = app.achievements


def watching(you = (1,), scores = (0, 0)):
    ach.reset()
    state = {"scores": scores}
    ach.start(lambda: set(you), lambda: state["scores"])
    return state


def feed(*events):
    for kind, *values in events:
        ach.event(kind, values)


class TheList(unittest.TestCase):
    def test_twenty_one(self):
        self.assertEqual(len(A.LIST), 21)
        self.assertEqual(len({a[0] for a in A.LIST}), 21)
        self.assertEqual(len({a[3] for a in A.LIST}), 21, "each its own seal")


class FromEvents(unittest.TestCase):
    def setUp(self):
        self.banners = []
        ach.on_earn = self.banners.append

    def tearDown(self):
        ach.on_earn = app.earned
        ach.reset()

    def test_a_rally_of_30(self):
        watching()
        feed(*[("hit", 1 + i % 2, 0.0, 0.0, 900) for i in range(29)])
        self.assertNotIn("rally_30", ach.earned)
        feed(("hit", 2, 0.0, 0.0, 900))
        self.assertIn("rally_30", ach.earned)

    def test_rocket_off_your_paddle_only(self):
        watching(you = (1,))
        feed(("hit", 2, 0.0, 0.0, 3400))
        self.assertNotIn("rocket", ach.earned)
        feed(("hit", 1, 0.0, 0.0, 3000))
        self.assertIn("rocket", ach.earned)

    def test_bank_shot(self):
        watching()
        feed(("hit", 1, 0, 0, 900), ("wall", 0, 0, 0, 0.5), ("wall", 0, 0, 0, 0.5), ("score", 1))
        self.assertNotIn("bank_shot", ach.earned, "two isn't enough")
        feed(("hit", 1, 0, 0, 900), *[("wall", 0, 0, 0, 0.5)] * 3, ("score", 1))
        self.assertIn("bank_shot", ach.earned)

    def test_trick_shot(self):
        watching()
        feed(("hit", 1, 0, 0, 900), ("stone", 0, 0, 0, 0.5), ("score", 1))
        self.assertIn("trick_shot", ach.earned)

    def test_spirit_fire_winner(self):
        watching()
        feed(("blaze", 1), ("hit", 1, 0, 0, 900), ("score", 1))
        self.assertIn("fire_winner", ach.earned)

    def test_not_off_the_other_players_shot(self):
        watching(you = (1,))
        feed(("blaze", 2), ("hit", 2, 0, 0, 900), *[("wall", 0, 0, 0, 0.5)] * 3, ("stone", 0, 0, 0, 0.5), ("score", 2))
        self.assertEqual(ach.earned, {})

    def test_saves_teleports_and_a_collapse(self):
        watching(you = (2,))
        feed(("save", 1), ("teleport", 1))
        self.assertEqual(ach.earned, {})
        feed(("save", 2), ("teleport", 2), ("collapse",))
        for key in ("great_save", "teleport_save", "into_the_void"):
            self.assertIn(key, ach.earned)

    def test_talismans(self):
        watching(you = (1,))
        for i in range(A.TALISMANS - 1):
            ach.event("pickup", [i % len(KINDS), 1])
        ach.event("pickup", [0, 2])                       # (the other player's)
        self.assertNotIn("paper_trail", ach.earned)
        self.assertIn("collection", ach.earned)
        ach.event("pickup", [0, 1])
        self.assertIn("paper_trail", ach.earned)

    def test_nobody_playing_nothing_counts(self):
        watching(you = ())
        feed(*[("hit", 1, 0, 0, 3500)] * 40, ("collapse",), ("save", 1))
        self.assertEqual(ach.earned, {})

    def test_each_earned_once(self):
        watching()
        feed(("collapse",), ("collapse",))
        self.assertEqual(self.banners, ["into_the_void"])


class FromMatches(unittest.TestCase):
    def setUp(self):
        ach.on_earn = lambda key: None

    def tearDown(self):
        ach.on_earn = app.earned
        ach.reset()

    def test_first_match_first_win_and_fifty(self):
        ach.reset()
        ach.match_over(False, ai_level = 2)
        self.assertEqual(set(ach.earned), {"first_match"})
        ach.match_over(True, lost_score = 3, ai_level = 2)
        self.assertIn("first_win", ach.earned)
        for _ in range(A.MATCHES - 2):
            ach.match_over(None)
        self.assertIn("matches_50", ach.earned)

    def test_hard_and_insane(self):
        ach.reset()
        ach.match_over(True, 4, ai_level = 3)
        self.assertIn("beat_hard", ach.earned)
        self.assertNotIn("beat_insane", ach.earned)
        ach.match_over(True, 4, ai_level = 4)
        self.assertIn("beat_insane", ach.earned)

    def test_three_in_a_row(self):
        ach.reset()
        for won in (True, True, False, True, True):
            ach.match_over(won, 4, ai_level = 1)
        self.assertNotIn("three_in_a_row", ach.earned)
        ach.match_over(True, 4, ai_level = 1)
        self.assertIn("three_in_a_row", ach.earned)

    def test_flawless_and_two_players_win_nothing(self):
        ach.reset()
        ach.match_over(None, 0)
        self.assertNotIn("flawless", ach.earned)
        self.assertNotIn("first_win", ach.earned)
        ach.match_over(True, 0, ai_level = 0)
        self.assertIn("flawless", ach.earned)

    def test_back_from_the_grave(self):
        state = watching(you = (1,))
        state["scores"] = (0, 5)
        ach.event("score", [2])
        state["scores"] = (11, 9)
        ach.match_over(True, 9, ai_level = 2)
        self.assertIn("comeback", ach.earned)

    def test_grand_tour_chaos_and_online(self):
        ach.reset()
        for court in COURTS[:-1]:
            ach.match_over(True, 3, ai_level = 2, court = court.name)
        self.assertNotIn("grand_tour", ach.earned)
        ach.match_over(False, 3, ai_level = 2, court = COURTS[-1].name)
        self.assertNotIn("grand_tour", ach.earned, "a win there, not a loss")
        ach.match_over(True, 3, ai_level = 2, court = COURTS[-1].name, chaos = True)
        self.assertIn("grand_tour", ach.earned)
        self.assertIn("utter_chaos", ach.earned)
        ach.match_over(True, 3, online = True)
        self.assertIn("far_away_friend", ach.earned)


class InAMatch(unittest.TestCase):
    """The match screen wires it up; practice (against the wall, or scoring off) doesn't count."""
    def setUp(self):
        ach.reset()
        ach.on_earn = lambda key: None

    def tearDown(self):
        ach.on_earn = app.earned
        ach.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)
        m.reset()

    def game(self, **rules):
        m.reset()
        for name, value in rules.items():
            setattr(m, name, value)
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        state = sm.current()
        self.assertIsInstance(state, GameState)
        return state.game

    def collapse(self, g):
        pu = g.powerups
        pu.open_hole()
        hole = pu.holes[-1]
        hole["eaten"] = PowerUps.HOLE_GROWTHS
        pu.swallow(g.ball, hole)

    def test_a_collapse_in_a_match(self):
        g = self.game(powerups = True)
        self.assertEqual(g.you(), {1})
        self.collapse(g)
        self.assertIn("collapse", [e[1] for e in g.recorder.events])
        self.assertIn("into_the_void", ach.earned)

    def test_not_in_practice(self):
        g = self.game(powerups = True, scoring = False)     # (Practice vs AI with scoring off)
        self.collapse(g)
        self.assertNotIn("into_the_void", ach.earned)

    def test_a_win_against_a_hard_ai(self):
        g = self.game(ai_difficulty = 3)
        app.state_manager.push_state("win", p1 = g.p1, p2 = g.p2, winner = g.p1, loser = g.p2)
        harness.settle(app)
        for key in ("first_match", "first_win", "beat_hard"):
            self.assertIn(key, ach.earned)

    def test_hits_carry_their_speed(self):
        g = self.game()
        g.recorder.on_hit(g.ball, g.p1, {"normal": (1, 0)})
        hit = [e for e in g.recorder.events if e[1] == "hit"][-1]
        self.assertEqual(len(hit), 6, "(frame, kind, side, x, y, speed)")


class Shown(unittest.TestCase):
    def tearDown(self):
        ach.reset()
        app.renderer._banners = []

    def test_a_banner_and_saved(self):
        ach.reset()
        played = []
        real = app.sound_manager.play
        app.sound_manager.play = lambda name, *a, **k: (played.append(name), real(name, *a, **k))[1]
        try:
            ach.earn("rocket")
        finally:
            app.sound_manager.play = real
        self.assertIn("Match/achievement.wav", played)
        self.assertEqual(len(app.renderer._banners), 1)
        app.renderer.draw_achievement(app.virtual, 0.5)
        app.loop()                                  # (not mid-rally: saved straight away)
        saved = json.loads(save_data.achievements_path().read_text())
        self.assertIn("rocket", saved["earned"])

    def test_not_saved_mid_rally(self):
        """Saving takes a few ms, enough to jolt a rally: it waits for the point to end, or a pause."""
        ach.reset()
        save_data.save(app)
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        game = sm.current().game
        game.countdown, game.paused = None, False
        try:
            ach.earn("bank_shot")
            app.loop()
            saved = json.loads(save_data.achievements_path().read_text())
            self.assertNotIn("bank_shot", saved["earned"])
            game.paused = True
            app.loop()
            saved = json.loads(save_data.achievements_path().read_text())
            self.assertIn("bank_shot", saved["earned"])
        finally:
            sm.set_state("main_menu", mute = True)
            harness.settle(app)

    def test_banners_built_ahead(self):
        from core.achievements import LIST
        keys = {job_key for job_key in [("achievement", a[0]) for a in LIST]}
        for job in app.renderer.idle_jobs():
            job()
        self.assertTrue(all(k in app.art.cache for k in keys))

    def test_banners_wait_their_turn(self):
        app.renderer._banners = []
        app.renderer.show_achievement("rocket")
        app.renderer.show_achievement("bank_shot")
        app.renderer.draw_achievement(app.virtual, 2.0)
        self.assertEqual(len(app.renderer._banners), 2)
        app.renderer.draw_achievement(app.virtual, 3.0)
        self.assertEqual(len(app.renderer._banners), 1)

    def test_the_screen(self):
        ach.reset()
        ach.earned["rocket"] = "2026-11-19"
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("stats", mute = True)
        harness.settle(app)
        stats = sm.current()
        stats.draw(app.virtual)
        self.assertIn("open_achievements", stats.ui_hitboxes)
        from tests.test_settings_menus import click
        click(stats, "open_achievements")
        harness.settle(app)
        screen = sm.current()
        self.assertEqual(screen.NAME, "achievements")
        screen.draw(app.virtual)
        self.assertIn("reset_defaults", screen.ui_hitboxes)
        sm.set_state("main_menu", mute = True)
        harness.settle(app)


class Kept(unittest.TestCase):
    def tearDown(self):
        ach.reset()

    def test_loads_back_and_an_older_version_cant_lose_them(self):
        ach.reset()
        ach.earned["flawless"] = "2026-11-19"
        ach.counts["taken"] = 42
        save_data.save(app)
        data = json.loads(save_data.save_path().read_text())
        save_data.save_path().write_text(json.dumps(data))        # (1.8 rewriting save.json its own way)
        ach.reset()
        save_data.load(app)
        self.assertEqual(ach.earned, {"flawless": "2026-11-19"})
        self.assertEqual(ach.counts["taken"], 42)

    def test_nonsense_is_dropped(self):
        ach.load_dict({"earned": {"flawless": "2026-11-19", "nope": "x", "rocket": 5},
                       "counts": {"matches": -3, "taken": 7, "kinds": ["giant", 4], "streak": True}})
        self.assertEqual(ach.earned, {"flawless": "2026-11-19"})
        self.assertEqual((ach.counts["matches"], ach.counts["taken"], ach.counts["kinds"], ach.counts["streak"]),
                         (0, 7, ["giant"], 0))


if __name__ == "__main__":
    unittest.main()

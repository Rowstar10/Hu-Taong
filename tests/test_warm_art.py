"""Art built ahead of time, 1.6 (Rowan's performance pass, 2026-11-17).

Mid-match, art drawn for the first time had to be built on the spot, and play stuttered: each
talisman's first appearance on the court (30-60 ms), the Firecracker's burst of big butterflies
(about 90 ms), the swap banner, popup names, the countdown.  Now they're built while the game loads
and while the menus are up, and the menus' share carries on through serve countdowns and goals
(never while the ball is in play), so starting a match straight away doesn't leave it to a rally.
"""
import unittest
from types import SimpleNamespace

from tests import harness

app = harness.app()

from game.game_base import Countdown                            # noqa: E402
from game.powerups import KINDS, PowerUps                       # noqa: E402

art, renderer = app.art, app.renderer
SIZES = ((64, ("red", "blue")), (48, ("red", "blue")), (44, ("red", "blue")), (40, ("red", "blue")),
         (80, ("red",)), (88, ("red",)), (32, ("red",)))


def warm_everything():
    while app.idle_jobs:
        app.idle_jobs.pop()()


class Counting:
    """Counts the art built for the first time while it's on."""

    def __enter__(self):
        self.built = []
        self.real = art.get

        def get(key, build, *a):
            if key not in art.cache:
                self.built.append(key)
            return self.real(key, build, *a)
        art.get = get
        return self

    def __exit__(self, *exc):
        art.get = self.real


class WarmedAhead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warm_everything()

    def test_talismans_on_the_court(self):
        powerups = SimpleNamespace(pickups = [{"kind": k.key, "x": 900, "y": 500, "age": 1.0, "phase": 0.0}
                                              for k in KINDS], LIFETIME = PowerUps.LIFETIME, RADIUS = PowerUps.RADIUS)
        with Counting() as c:
            renderer.draw_pickups(app.virtual, powerups, 0, 0)
        self.assertEqual(c.built, [])

    def test_the_serve_countdown(self):
        with Counting() as c:
            for shown in (3, 2, 1, 0):
                for i in range(41):
                    renderer.draw_countdown(app.virtual, Countdown(remaining = shown - 1 + i / 40, shown_value = shown))
        self.assertEqual(c.built, [])

    def test_popup_names_and_banners(self):
        names = [k.name for k in KINDS] + ["BANG!"]
        from game.powerups import FAMILY_COLOURS
        tints = [FAMILY_COLOURS[k.family] for k in KINDS] + [(255, 200, 80)]
        powerups = SimpleNamespace(popups = [[n, 900, 500, 0.2, t] for n, t in zip(names, tints)])
        with Counting() as c:
            renderer.draw_popups(app.virtual, powerups)
            renderer.draw_switch_banner(app.virtual, 1.0, "换 Switch!")
            renderer.draw_switch_banner(app.virtual, 1.0, "换 Swap!")
        self.assertEqual(c.built, [])

    def test_every_butterfly_the_game_sends_out(self):
        for size, tints in SIZES:
            for tint in tints:
                for frame in range(art.FLAP_FRAMES):
                    for turn in range(art.TURN_STEPS):
                        self.assertIn(("fly", size, frame, turn, tint), art.cache)

    def test_every_size_the_game_bursts_is_listed(self):
        """A new burst size added to the game, but not to the warm-up, would stutter again."""
        import pathlib
        import re
        sizes = {size for size, _ in SIZES}
        used = set()
        for path in pathlib.Path(harness.GAME).glob("**/*.py"):
            if "tests" in path.parts:
                continue
            text = path.read_text(encoding = "utf-8")
            used |= {int(m) for m in re.findall(r"fx\.burst\([^,]+,[^,]+,[^,]+,\s*(\d+)", text)}
        self.assertLessEqual(used, sizes, f"burst sizes not warmed: {used - sizes}")


class FirstPause(unittest.TestCase):
    """The first pause of a session built its panel and lettering, and loaded the ambience."""

    def test_the_ambience_is_loaded_at_start(self):
        import pygame
        from core.sound_manager import AMBIENCE, SOUND_CACHE
        if not pygame.mixer.get_init():
            self.skipTest("no sound here")
        for name, _ in AMBIENCE:
            self.assertIn(name, SOUND_CACHE)

    def test_the_pause_screen_is_warmed_without_showing_anything(self):
        offered = renderer.tips.offered
        renderer.warm_pause_screen()
        self.assertNotIn("pointer", app.__dict__, "the real pointer is back")
        self.assertEqual(renderer.tips.offered, offered, "no tooltip offered")
        self.assertIn(("watermark", "停", 400, 26), art.cache)
        self.assertTrue(any(isinstance(k, tuple) and k[0] == "panel" for k in art.cache))

    def test_it_is_in_the_menu_warm_up(self):
        self.assertIn(renderer.warm_pause_screen, renderer.idle_jobs())


class WarmsOnlyWhileTheBallRests(unittest.TestCase):
    def setUp(self):
        app.idle_jobs = [lambda: None] * 5000
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        self.game = sm.current().game

    def tearDown(self):
        app.idle_jobs = []
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def frame(self):
        app.state_manager.process_changes()
        app.dt = 1 / 60
        app.loop()

    def test_during_the_serve_countdown(self):
        self.assertIsNotNone(self.game.countdown)
        left = len(app.idle_jobs)
        self.frame()
        self.assertTrue(app.ball_resting())
        self.assertLess(len(app.idle_jobs), left)

    def test_not_while_the_ball_is_in_play(self):
        self.game.countdown, self.game.paused = None, False
        self.frame()
        left = len(app.idle_jobs)
        for _ in range(5):
            self.frame()
        self.assertFalse(app.ball_resting())
        self.assertEqual(len(app.idle_jobs), left)


if __name__ == "__main__":
    unittest.main()

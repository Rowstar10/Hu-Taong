"""The next background got ready ahead, 1.6 (Rowan's performance pass, 2026-11-17).

Each background change stuttered play (27-71 ms): the new picture was loaded the moment its fade
was due, often mid-rally, and the Dim settings were baked into it on the main thread.  Now the next
one is chosen ahead (still at random), and the worker loads it and bakes the dim in while nothing
is moving: the menus, a serve countdown, a goal.  It looks exactly the same.
"""
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

bg = app.backgrounds
display = app.settings.display


def wait(name, dim):
    for future in [bg.pictures.get(name), bg.dim_jobs.get((name, dim))]:
        if future is not None:
            future.result(timeout = 30)


class WorkerBakesTheDim(unittest.TestCase):
    def test_same_pixels_as_the_main_thread(self):
        name, dim = display.backgrounds[0], 0.637
        bg.dimmed.pop(name, None)
        bg.request(name, dim)
        wait(name, dim)
        self.assertTrue(bg.ready(name, dim))
        worker = bg.get(name, dim)
        main = bg._shade_main(bg.picture(name), dim)
        self.assertEqual(pygame.image.tobytes(worker, "RGB"), pygame.image.tobytes(main, "RGB"))

    def test_showing_it_costs_the_main_thread_nothing(self):
        name, dim = display.backgrounds[1], 0.42
        bg.dimmed.pop(name, None)
        bg.request(name, dim)
        wait(name, dim)
        shaded = []
        real = bg._shade_main
        bg._shade_main = lambda *a: shaded.append(a) or real(*a)
        try:
            bg.get(name, dim)
        finally:
            bg._shade_main = real
        self.assertEqual(shaded, [])

    def test_not_ready_until_baked_at_that_dim(self):
        name = display.backgrounds[2]
        bg.dimmed.pop(name, None)
        bg.request(name)
        wait(name, None)
        self.assertTrue(bg.ready(name))
        self.assertFalse(bg.ready(name, 0.33))


class ChosenAhead(unittest.TestCase):
    def setUp(self):
        display.rotate_backgrounds = True
        app.bg_next, app.bg_transition_active = None, False
        app.bg_upcoming, app.bg_upcoming_asked = None, False
        self.asked = []
        self.real = bg.request
        bg.request = lambda name, dim = None: self.asked.append((name, dim))
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        self.game = sm.current().game

    def tearDown(self):
        bg.request = self.real
        app.bg_next, app.bg_transition_active = None, False
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_not_while_the_ball_is_in_play(self):
        self.game.countdown, self.game.paused = None, False
        app.prepare_next_background(app.background_dim())
        self.assertEqual(self.asked, [])
        self.assertIsNotNone(app.bg_upcoming, "chosen already...")

    def test_while_the_ball_rests(self):
        self.game.start_countdown(3)
        app.bg_upcoming = next(n for n in display.backgrounds if n != app.bg_current)
        app.prepare_next_background(0.5)
        self.assertEqual(self.asked, [(app.bg_upcoming, 0.5)])
        app.prepare_next_background(0.5)
        self.assertEqual(len(self.asked), 1, "asked once")

    def test_the_fade_brings_the_one_got_ready(self):
        upcoming = next(n for n in display.backgrounds if n != app.bg_current)
        app.bg_upcoming, app.bg_upcoming_asked = upcoming, True
        app.start_bg_transition()
        self.assertEqual(app.bg_next, upcoming)
        self.assertIsNone(app.bg_upcoming, "the next one is chosen afresh")


class WholeFade(unittest.TestCase):
    def test_a_fade_still_runs_start_to_finish(self):
        """In the menus: the next one is got ready ahead, then the fade brings it in, and nothing
        is shaded on the main thread along the way."""
        display.rotate_backgrounds = True
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        harness.settle(app)
        app.bg_next, app.bg_transition_active = None, False
        app.bg_upcoming = next(n for n in display.backgrounds if n != app.bg_current)
        app.bg_upcoming_asked = False
        upcoming = app.bg_upcoming
        shaded = []
        real = bg._shade_main
        bg._shade_main = lambda surf, dim: shaded.append(dim) or real(surf, dim)

        def frames(n):
            for _ in range(n):
                sm.process_changes()
                app.dt = 1 / 60
                app.loop()
        try:
            frames(1)                                   # it's chosen and handed to the worker...
            wait(upcoming, app.background_dim())        # ...which gets it ready
            app.start_bg_transition()                   # the Rotate timer goes off
            frames(int(app.bg_transition_duration * 60) + 30)
        finally:
            bg._shade_main = real
        self.assertEqual(app.bg_current, upcoming)
        self.assertIsNone(app.bg_next)
        self.assertEqual(shaded, [])


if __name__ == "__main__":
    unittest.main()

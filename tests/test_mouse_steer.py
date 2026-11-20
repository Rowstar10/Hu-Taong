"""Steering with the mouse, 1.9 (Rowan, phase 3: "Also make controls for moving the paddle with
your mouse").

Settings > Controls > Mouse Steering (off unless turned on).  On, the paddle heads for the pointer,
no faster than its own speed, once the mouse moves in a match; a paddle key or a controller takes
over again until the mouse moves.  On your own it plays your paddle; two players here, the side set
in Controls.  The HUD says "Mouse" while it steers.  As the friend who joined online, the pointer
goes out as a share of full speed (as a phone's finger does): no new message.
"""
import unittest

import pygame

from tests import harness

app = harness.app()

from game.hu_taong import Hu_Taong                              # noqa: E402

m = app.settings.match
g = app.settings.gameplay
mouse = app.mouse_steer
DT = 1 / 60


def move(x, y):
    """The mouse moving to (x, y) in the game's own 1920 x 1080 (the window may be another size)."""
    pos = (int(x / app.sx), int(y / app.sy))
    for e in app.gamepads.translate(pygame.event.Event(pygame.MOUSEMOTION, pos = pos, rel = (5, 5), buttons = (0, 0, 0))):
        app.state_manager.handle_event(e)


def key(k):
    for e in app.gamepads.translate(pygame.event.Event(pygame.KEYDOWN, key = k, mod = 0, unicode = "", scancode = 0)):
        app.state_manager.handle_event(e)


class Mouse(unittest.TestCase):
    def setUp(self):
        m.reset()
        g.reset()
        m.powerups = False
        sm = app.state_manager
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        self.state = sm.current()
        self.game = self.state.game
        self.game.countdown, self.game.paused = None, False

    def tearDown(self):
        mouse.let_go()
        g.reset()
        m.reset()
        app.keys_down.clear()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def run_for(self, seconds):
        for _ in range(int(seconds / DT)):
            self.game.ball.vx = self.game.ball.vy = 0.0          # (the ball out of the way)
            self.state.update(DT)

    def test_off_by_default(self):
        self.assertFalse(g.mouse_steer)
        y0 = self.game.p1.y0
        move(200, 1000)
        self.run_for(0.3)
        self.assertEqual(self.game.p1.y0, y0, "a nudged mouse never moves your paddle")

    def test_the_paddle_heads_for_the_pointer(self):
        g.mouse_steer = True
        p = self.game.p1
        move(p.x0 + p.width / 2, 900)
        self.assertTrue(mouse.active)
        self.run_for(1.5)
        self.assertAlmostEqual((p.y0 + p.y1) / 2, 900, delta = 12)
        self.assertEqual(p.controls_label, "Mouse", "the HUD says so")

    def test_no_faster_than_the_keys(self):
        g.mouse_steer = True
        p = self.game.p1
        move(p.x0 + p.width / 2, 1050)
        self.run_for(0.1)
        self.assertLessEqual(abs(p.vy), p.speed + 1)

    def test_the_keys_take_over_till_it_moves_again(self):
        g.mouse_steer = True
        p = self.game.p1
        move(p.x0 + p.width / 2, 900)
        key(g.p1_up)
        self.assertFalse(mouse.active)
        self.assertIsNone(mouse.steer_paddle(p))
        self.run_for(0.1)
        self.assertNotEqual(p.controls_label, "Mouse")
        move(p.x0 + p.width / 2, 800)
        self.assertTrue(mouse.active)

    def test_a_controller_takes_over(self):
        g.mouse_steer = True
        app.gamepads.add(700, "Xbox 360 Controller", quiet = True)
        try:
            move(300, 900)
            app.gamepads.translate(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, instance_id = 700,
                                                      button = pygame.CONTROLLER_BUTTON_DPAD_UP))
            self.assertFalse(mouse.active)
        finally:
            app.gamepads.pads.clear()
            app.gamepads.using = "keys"

    def test_two_players_the_side_set(self):
        m.vs_ai = False
        g.mouse_steer = True
        game = Hu_Taong(app)
        game.start()
        try:
            self.assertTrue(mouse.plays(game.p1) and not mouse.plays(game.p2), "Red, by default")
            g.mouse_side = 1
            self.assertTrue(mouse.plays(game.p2) and not mouse.plays(game.p1))
        finally:
            game.stop()

    def test_not_the_ais_paddle(self):
        g.mouse_steer = True
        move(1700, 500)
        self.assertIsNone(mouse.steer_paddle(self.game.p2))


if __name__ == "__main__":
    unittest.main()

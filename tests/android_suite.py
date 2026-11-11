"""The game as it plays on a phone, run on a PC: tests/test_android.py starts this in its own
Python with HUTAONG_ANDROID=1 (one game window per Python), and fingers are made up as SDL would
send them.

Run it on its own with:   HUTAONG_ANDROID=1 python -m unittest tests.android_suite
"""
import os
import unittest
from unittest import mock

from tests import harness

assert os.environ.get("HUTAONG_ANDROID") == "1", "run through tests/test_android.py"
app = harness.app()

import pygame                                   # noqa: E402
from config import BASE_W, BASE_H               # noqa: E402
from core import net as netcode                 # noqa: E402
from core import platform                       # noqa: E402
from core.touch import OFF                      # noqa: E402
from render.renderer import touch_tip           # noqa: E402

FINGER = 0


def finger(kind, x, y, fid = None):
    """A finger event, at (x, y) in the game's own 1920 x 1080, as SDL sends it (0-1 across the
    screen)."""
    pygame.event.post(pygame.event.Event(kind, touch_id = 1, finger_id = FINGER if fid is None else fid,
                                         x = x / BASE_W, y = y / BASE_H, dx = 0.0, dy = 0.0, pressure = 1.0))


def frames(n = 1):
    for _ in range(n):
        app.state_manager.process_changes()
        app.dt = 1 / 60
        app.loop()


def tap(x, y, hold = 1):
    finger(pygame.FINGERDOWN, x, y)
    frames(hold)
    finger(pygame.FINGERUP, x, y)
    frames(3)


def centre(key):
    """Where a control is on the screen in front of us."""
    state = app.state_manager.current()
    frames(1)
    return state.ui_hitboxes[key].center


def go_to(*names):
    app.state_manager.set_state("main_menu", mute = True)
    for name in names:
        app.state_manager.push_state(name, mute = True)
    frames(2)


class Screen(unittest.TestCase):
    def test_the_game_fills_the_screen_at_its_own_size(self):
        self.assertTrue(platform.ANDROID)
        self.assertEqual(app.display.get_size(), (BASE_W, BASE_H))
        self.assertIs(app.virtual, app.display)              # no scaling copy each frame
        self.assertEqual(app.resolutions, [(BASE_W, BASE_H)])
        self.assertEqual(app.display_modes, ["fullscreen"])

    def test_display_settings_have_no_window_controls(self):
        go_to("settings", "display")
        keys = harness.buttons(app.state_manager.current(), app)
        self.assertNotIn("cycle_res_left", keys)
        self.assertNotIn("apply", keys)
        self.assertIn("cycle_max_fps_left", keys)
        self.assertEqual(app.settings.display.max_fps_options[app.settings.display.max_fps], 60)

    def test_interface_settings_have_touch_controls_not_keys(self):
        go_to("settings", "interface")
        keys = harness.buttons(app.state_manager.current(), app)
        self.assertIn("cycle_touch_steer_left", keys)
        self.assertIn("cycle_touch_sensitivity_right", keys)
        self.assertIn("toggle_vibration", keys)
        self.assertFalse([k for k in keys if k.startswith("key_")])
        self.assertNotIn("toggle_hide_cursor", keys)

    def test_saves_go_to_the_apps_own_storage(self):
        with mock.patch.dict(os.environ, {"ANDROID_PRIVATE": "/data/user/0/hu.taong/files"}):
            self.assertEqual(platform.data_dir().as_posix(), "/data/user/0/hu.taong/files/HuTaong")   # (as on the phone, on any PC)

    def test_tooltips_drop_keyboard_hints(self):
        self.assertEqual(touch_tip("Pause\nPause the match.\n~ Esc"), "Pause\nPause the match.")
        self.assertEqual(touch_tip("Seek\n~ Click or drag along the bar to jump"),
                         "Seek\n~ Tap or drag along the bar to jump")


class Menus(unittest.TestCase):
    def setUp(self):
        go_to()

    def test_a_tap_clicks_when_the_finger_lifts(self):
        x, y = centre("play")
        finger(pygame.FINGERDOWN, x, y)
        frames(3)
        self.assertEqual(app.state_manager.current().NAME, "main_menu")    # not yet
        finger(pygame.FINGERUP, x, y)
        frames(3)
        self.assertEqual(app.state_manager.current().NAME, "match_setup")
        self.assertEqual(app.pointer(), OFF)                              # nothing left hovered

    def test_a_long_press_shows_the_tooltip_and_does_not_click(self):
        app.settings.interface.tooltips = True
        x, y = centre("play")
        finger(pygame.FINGERDOWN, x, y)
        frames(45)
        self.assertTrue(app.renderer.tips.showing())
        finger(pygame.FINGERUP, x, y)
        frames(3)
        self.assertEqual(app.state_manager.current().NAME, "main_menu")

    def test_sliding_off_a_button_does_not_click_it(self):
        x, y = centre("play")
        finger(pygame.FINGERDOWN, x, y)
        frames(1)
        finger(pygame.FINGERMOTION, x, y + 200)
        frames(1)
        finger(pygame.FINGERUP, x, y + 200)
        frames(3)
        self.assertEqual(app.state_manager.current().NAME, "main_menu")

    def test_back_is_escape(self):
        go_to("settings", "display")
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_AC_BACK, mod = 0, unicode = "",
                                             scancode = 270))
        frames(3)
        self.assertEqual(app.state_manager.current().NAME, "settings")

    def test_a_slider_follows_the_finger_at_once(self):
        go_to("settings", "audio")
        state = app.state_manager.current()
        frames(1)
        rect = state.ui_hitboxes["master_volume_slider"]
        finger(pygame.FINGERDOWN, rect.left + rect.width * 0.2, rect.centery)
        frames(1)
        self.assertAlmostEqual(app.sound_manager.master_volume, 0.2, delta = 0.05)
        finger(pygame.FINGERMOTION, rect.left + rect.width * 0.7, rect.centery)
        frames(1)
        self.assertAlmostEqual(app.sound_manager.master_volume, 0.7, delta = 0.05)
        finger(pygame.FINGERUP, rect.left + rect.width * 0.7, rect.centery)
        frames(2)
        self.assertFalse(state.dragging_master_volume)

    def test_sliding_a_finger_scrolls_a_list_without_picking_from_it(self):
        go_to("settings", "display", "background_selection")
        state = app.state_manager.current()
        frames(1)
        chosen = app.settings.display.background
        state.scroll_to(0)
        x, y = state.view.center
        finger(pygame.FINGERDOWN, x, y)
        frames(1)
        for step in range(1, 9):
            finger(pygame.FINGERMOTION, x, y - 40 * step)
            frames(1)
        finger(pygame.FINGERUP, x, y - 320)
        frames(3)
        if state.max_scroll > 0:
            self.assertGreater(state.scroll_target, 0)
        self.assertEqual(app.settings.display.background, chosen)
        self.assertEqual(app.state_manager.current().NAME, "background_selection")

    def test_join_brings_up_the_keyboard_and_typing_shows(self):
        go_to("match_setup", "online")
        state = app.state_manager.current()
        frames(1)
        with mock.patch("pygame.key.start_text_input") as start, mock.patch("pygame.key.stop_text_input") as stop:
            tap(*centre("join_game"))
            self.assertEqual(state.focus, "code")
            self.assertTrue(start.called)
            self.assertTrue(app.touch.typing)
            pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text = "AB", window = None))
            frames(2)                                   # and the typing bar shows it
            self.assertEqual(state.code[-2:], "AB")
            app.state_manager.set_state("main_menu", mute = True)
            frames(2)
            self.assertTrue(stop.called)
            self.assertFalse(app.touch.typing)


class Steering(unittest.TestCase):
    def start(self, vs_ai = True):
        g = app.settings.gameplay
        self.kept = (g.vs_ai, g.play_as_blue)
        g.vs_ai, g.play_as_blue = vs_ai, False
        app.state_manager.set_state("game", mute = True)
        frames(1)
        self.state = app.state_manager.current()
        self.game = self.state.game
        self.game.countdown, self.game.paused = None, False          # straight into play
        frames(1)

    def tearDown(self):
        app.state_manager.set_state("main_menu", mute = True)
        frames(1)
        g = app.settings.gameplay
        g.vs_ai, g.play_as_blue = self.kept

    @staticmethod
    def middle(p):
        return (p.y0 + p.y1) / 2

    def test_dragging_moves_your_paddle_as_far_as_the_finger(self):
        self.start()
        app.settings.interface.touch_steer = 0
        app.settings.interface.touch_sensitivity = 1                 # Normal: one to one
        p1 = self.game.p1
        self.assertFalse(p1.ai_enabled)
        start = self.middle(p1)
        finger(pygame.FINGERDOWN, 1500, 700)                          # anywhere: it's your screen
        frames(1)
        finger(pygame.FINGERMOTION, 1500, 450)
        frames(70)
        self.assertAlmostEqual(self.middle(p1), max(p1.height / 2, start - 250), delta = 12)
        finger(pygame.FINGERUP, 1500, 450)
        frames(30)
        self.assertLess(abs(p1.vy), 30)                              # let go: it stops

    def test_follow_heads_for_the_finger_no_faster_than_the_paddle(self):
        self.start()
        app.settings.interface.touch_steer = 1
        p1 = self.game.p1
        top = 0.0
        finger(pygame.FINGERDOWN, 200, 150)
        for _ in range(80):
            frames(1)
            top = max(top, abs(p1.vy))
        finger(pygame.FINGERUP, 200, 150)
        frames(1)
        app.settings.interface.touch_steer = 0
        self.assertAlmostEqual(self.middle(p1), max(p1.height / 2, 150), delta = 12)
        self.assertLessEqual(top, p1.speed * 1.01)

    def test_two_players_each_have_their_half(self):
        self.start(vs_ai = False)
        app.settings.interface.touch_steer = 1
        p1, p2 = self.game.p1, self.game.p2
        finger(pygame.FINGERDOWN, 300, 200, fid = 1)
        finger(pygame.FINGERDOWN, 1600, 900, fid = 2)
        frames(80)
        self.assertLess(self.middle(p1), BASE_H / 2)
        self.assertGreater(self.middle(p2), BASE_H / 2)
        finger(pygame.FINGERUP, 300, 200, fid = 1)
        finger(pygame.FINGERUP, 1600, 900, fid = 2)
        frames(1)
        app.settings.interface.touch_steer = 0

    def test_the_pause_button_pauses(self):
        self.start()
        frames(1)
        x, y = self.state.ui_hitboxes["pause"].center
        finger(pygame.FINGERDOWN, x, y)
        frames(2)
        finger(pygame.FINGERUP, x, y)
        frames(2)
        self.assertEqual(app.state_manager.current().NAME, "pause")


class OnlineGuest(unittest.TestCase):
    def test_a_finger_goes_out_as_keys_that_average_to_its_speed(self):
        guest = netcode.GuestSession.__new__(netcode.GuestSession)
        guest.keys, guest.axis, guest.owed = 0, (0.3, -0.75), [0.0, 0.0]
        x = y = 0
        for _ in range(400):
            keys = guest.sent_keys()
            x += ((keys & netcode.RIGHT) > 0) - ((keys & netcode.LEFT) > 0)
            y += ((keys & netcode.DOWN) > 0) - ((keys & netcode.UP) > 0)
        self.assertAlmostEqual(x / 400, 0.3, delta = 0.01)
        self.assertAlmostEqual(y / 400, -0.75, delta = 0.01)
        guest.axis = None
        guest.keys = netcode.UP
        self.assertEqual(guest.sent_keys(), netcode.UP)              # keys alone: as ever


if __name__ == "__main__":
    unittest.main()

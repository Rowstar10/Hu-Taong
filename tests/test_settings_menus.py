"""The settings menus regrouped, 1.7 (Rowan's 1.7 plan, 2026-11-17).

Settings has five cards: Match (the rules, the same for both players: modes, points to win, the
court, talismans, the AI; the ball and paddles on a screen of their own), then your own Gameplay
(the keys, Auto-Pause), Display (now with the effects), Audio and Interface (menus, the HUD).  No
setting that changes the match is left on a personal screen.
"""
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

s = app.settings

# What only the Match screens may show: anything that changes the match for both players
MATCH_KEYS = ("toggle_mode_", "cycle_mode_chaos", "cycle_mode_switch", "cycle_win_score", "toggle_win_by_two",
              "toggle_middle_wall", "cycle_countdown", "cycle_ai", "toggle_adaptive_ai", "toggle_powerups",
              "cycle_powerup_rate", "open_powerups", "cycle_court", "ball_speed_slider", "paddle_speed_slider",
              "ball_diameter_slider", "paddle_size_slider", "pace_slider", "randomise_all", "toggle_curveball",
              "toggle_lantern_night", "cycle_chaos_mode", "cycle_chaos_switch")
PERSONAL = ("gameplay", "display", "audio", "interface")
FOOTER = ("back", "reset_defaults", "reset_all")


def open_screen(name):
    sm = app.state_manager
    sm.set_state("main_menu", mute = True)
    sm.push_state(name, mute = True)
    harness.settle(app)
    screen = sm.current()
    screen.draw(app.virtual)
    return screen


def click(screen, key):
    screen.draw(app.virtual)
    x, y = screen.ui_hitboxes[key].center
    pos = (x / app.sx, y / app.sy)
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos))


class Hub(unittest.TestCase):
    def tearDown(self):
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_five_cards_the_match_first(self):
        boxes = open_screen("settings").ui_hitboxes
        cards = sorted(("match", "gameplay", "display", "audio", "interface"), key = lambda k: boxes[k].x)
        self.assertEqual(cards, ["match", "gameplay", "display", "audio", "interface"])
        for a, b in zip(cards, cards[1:]):
            self.assertLess(boxes[a].right, boxes[b].left, f"{a} and {b} overlap")
        self.assertGreaterEqual(boxes["match"].left, 0)
        self.assertLessEqual(boxes["interface"].right, 1920)

    def test_each_card_opens_its_screen(self):
        for card in ("match", "gameplay", "display", "audio", "interface"):
            hub = open_screen("settings")
            click(hub, card)
            harness.settle(app)
            self.assertEqual(app.state_manager.current().NAME, card)


class WhatGoesWhere(unittest.TestCase):
    def tearDown(self):
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_no_match_setting_on_a_personal_screen(self):
        for name in PERSONAL:
            keys = open_screen(name).ui_hitboxes
            leaked = [k for k in keys if k.startswith(MATCH_KEYS)]
            self.assertEqual(leaked, [], f"match settings on the {name} screen")

    def test_the_match_screen_has_the_rules(self):
        keys = open_screen("match").ui_hitboxes
        for key in ("cycle_mode_chaos", "cycle_mode_switch", "toggle_mode_twin_ball", "cycle_win_score_left",
                    "toggle_win_by_two", "toggle_middle_wall", "cycle_countdown_left", "cycle_ai_left",
                    "cycle_ai_style_left", "toggle_adaptive_ai", "cycle_court_left", "toggle_powerups",
                    "cycle_powerup_rate_left", "open_powerups", "open_ball_paddles"):
            self.assertIn(key, keys)

    def test_ball_and_paddles(self):
        keys = open_screen("ball_paddles").ui_hitboxes
        for key in ("ball_speed_slider", "paddle_speed_slider", "ball_diameter_slider", "paddle_size_slider",
                    "pace_slider", "randomise_all", "reset_ball_and_paddles"):
            self.assertIn(key, keys)

    def test_gameplay_is_your_controls(self):
        keys = open_screen("gameplay").ui_hitboxes
        for key in ("key_p1_up", "key_p2_right", "toggle_auto_pause"):
            self.assertIn(key, keys)

    def test_display_has_the_effects(self):
        keys = open_screen("display").ui_hitboxes
        for key in ("cycle_effects_left", "toggle_screen_shake", "toggle_ball_trail", "cycle_max_fps_left"):
            self.assertIn(key, keys)

    def test_interface_is_menus_and_the_hud(self):
        keys = set(open_screen("interface").ui_hitboxes) - set(FOOTER)
        self.assertEqual(keys, {"toggle_tooltips", "toggle_hide_cursor", "cycle_hud_left", "cycle_hud_right",
                                "toggle_ai_banter", "cycle_instant_replay_left", "cycle_instant_replay_right"})


class Layout(unittest.TestCase):
    def tearDown(self):
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_everything_fits_and_nothing_overlaps(self):
        panel = app.ui_layout.PANEL
        for name in ("match", "ball_paddles", "gameplay", "display", "interface", "audio", "match_setup"):
            boxes = {k: r for k, r in open_screen(name).ui_hitboxes.items() if k not in FOOTER}
            for key, rect in boxes.items():
                self.assertTrue(panel.contains(rect), f"{name}: {key} spills out of the panel")
            keys = list(boxes)
            for i, a in enumerate(keys):
                for b in keys[i + 1:]:
                    if not (a.startswith("music") or b.startswith("music")):      # (the jukebox's own bar)
                        self.assertFalse(boxes[a].colliderect(boxes[b]), f"{name}: {a} overlaps {b}")


class Clicks(unittest.TestCase):
    def tearDown(self):
        for group in (s.match, s.gameplay, s.display, s.interface):
            group.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_match_screen(self):
        screen = open_screen("match")
        click(screen, "cycle_countdown_right")
        self.assertEqual(s.match.serve_seconds, 2)
        click(screen, "toggle_powerups")
        self.assertFalse(s.match.powerups)
        click(screen, "cycle_mode_switch")
        self.assertTrue(s.match.mode_switch)
        click(screen, "open_ball_paddles")
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "ball_paddles")

    def test_display_screen(self):
        screen = open_screen("display")
        click(screen, "toggle_screen_shake")
        click(screen, "cycle_effects_right")
        self.assertEqual((s.display.screen_shake, s.display.effects), (False, 1))

    def test_gameplay_screen_binds_keys(self):
        screen = open_screen("gameplay")
        click(screen, "key_p1_up")
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_i, mod = 0, unicode = "i", scancode = 0))
        self.assertEqual(s.gameplay.p1_up, pygame.K_i)
        click(screen, "toggle_auto_pause")
        self.assertFalse(s.gameplay.auto_pause)

    def test_resets_keep_to_their_own_screen(self):
        s.gameplay.bind("p1_up", pygame.K_i)
        s.match.mode_chaos = True
        app.reset_interface_settings()
        self.assertEqual(s.gameplay.p1_up, pygame.K_i, "Interface's reset left the keys alone")
        app.reset_gameplay_settings()
        self.assertEqual(s.gameplay.p1_up, pygame.K_w)
        self.assertTrue(s.match.mode_chaos, "Gameplay's reset left the match alone")
        app.reset_match_settings()
        self.assertFalse(s.match.mode_chaos)


if __name__ == "__main__":
    unittest.main()

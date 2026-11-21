"""Display, Audio and Match Setup laid out afresh, 1.9 (Rowan, 2026-11-21, from previews).

- Display: "window into background into frame rate for the top row, and then effects into dimming
  for the bottom row", then swapped about till Frame Rate, Window and Effects run across the top,
  with Background and Dimming under them.
- Audio: under Sounds, "the toggles to be whole buttons instead of label then button".
- Match Setup: the main block of choices in the middle, the court on the left and Match Settings
  and Start Match on the right; Opponent with AI Level under it (not all in one row); and "put online
  mode below practice mode and multiplayer, sitting in the middle of the two".  Then Match Settings
  and Start Match to the bottom corners level with Back, the court and the choices centred together,
  and the court on the right of the choices.  (Practice Mode was "Practice" for a moment: Rowan
  preferred Practice Mode.)  Then AI Style under AI Level (and Adaptive AI under that, briefly), with
  the three Mode buttons back on one row to make room.
"""
import unittest
from unittest import mock

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from config import BASE_W                                       # noqa: E402
from render.ui.layout import Form, Label                        # noqa: E402
from tests.test_settings_layout import harness_nodes            # noqa: E402
from tests.test_settings_menus import click, open_screen        # noqa: E402
from tests.test_talismans_not_power_ups import texts            # noqa: E402


def headings(page):
    """Each section heading on a laid-out page, by name: its rect."""
    return {n.text: n.rect for n in harness_nodes(page) if isinstance(n, Label)}


class Layouts(unittest.TestCase):
    def tearDown(self):
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_display_in_two_rows(self):
        h = headings(open_screen("display"))
        top = [h[name] for name in ("Frame Rate", "Window", "Effects")]
        self.assertEqual(len({r.top for r in top}), 1, "one row")
        self.assertLess(top[0].centerx, top[1].centerx)
        self.assertLess(top[1].centerx, top[2].centerx, "Frame Rate, Window, Effects")
        under = [h["Background"], h["Dimming"]]
        self.assertEqual(under[0].top, under[1].top)
        self.assertGreater(under[0].top, top[0].bottom, "under them")
        self.assertLess(under[0].centerx, under[1].centerx)

    def test_audio_sounds_are_whole_buttons(self):
        page = open_screen("audio")
        names = [n.text for f in harness_nodes(page) if isinstance(f, Form) for n, _ in f.rows if n is not None]
        for name in ("Paddle Sounds", "Score Sound", "Menu Sounds"):
            self.assertNotIn(name, names, "no name beside it")
        drawn = texts(page)
        for words in ("Paddle Sounds: ON", "Score Sound: ON", "Menu Sounds: ON"):
            self.assertIn(words, drawn)
        boxes = page.ui_hitboxes
        widths = {boxes[k].w for k in ("toggle_paddle_sounds", "toggle_score_sounds", "toggle_menu_sounds")}
        self.assertEqual(len(widths), 1, "one width")

    def test_match_setup_court_right_buttons_in_the_footer(self):
        """(Then: "move start match to the bottom right and match settings to the bottom left on the
        same level as the back button", the court and the choices centred together, and the court
        moved to the right of the choices.)"""
        page = open_screen("match_setup")
        boxes = page.ui_hitboxes
        self.assertGreater(boxes["cycle_court_left"].left, boxes["opponent_human"].right, "the court on the right")
        self.assertGreater(boxes["cycle_court_left"].left, boxes["cycle_ai_right"].right)
        body = page._laid[0].rect
        self.assertLess(abs(body.centerx - BASE_W // 2), 3, "the two centred together")
        back, more, start = boxes["back"], boxes["open_match_settings"], boxes["start_match"]
        self.assertEqual((more.centery, start.centery), (back.centery, back.centery), "level with Back")
        # (after 1.9's release, Rowan: Back at the bottom left, Start Match in the middle and Match
        # Settings at the right; see tests/test_back_bottom_left.py)
        self.assertLess(back.right, start.left)
        self.assertLess(start.right, more.left)
        self.assertEqual(more.size, start.size, "one size")

    def test_still_practice_mode(self):
        """(Rowan tried "Practice", then: "I do prefer it when it's called practice mode.")"""
        self.assertIn("Practice Mode", texts(open_screen("match_setup")))

    def test_ai_level_under_opponent(self):
        boxes = open_screen("match_setup").ui_hitboxes
        self.assertGreater(boxes["cycle_ai_left"].top, boxes["practice_ai"].bottom)
        self.assertGreater(boxes["cycle_win_score_left"].top, boxes["side_red"].bottom, "(not all in one row)")

    def test_online_under_the_other_two_between_them(self):
        """("put online mode below practice mode and multiplayer, sitting in the middle of the two";
        back on one row for a while to make room, then "Can you get away with enough space for
        putting online onto the second row": yes.)"""
        boxes = open_screen("match_setup").ui_hitboxes
        practice, multi, online = boxes["opponent_ai"], boxes["opponent_human"], boxes["opponent_online"]
        self.assertEqual(practice.top, multi.top)
        self.assertGreater(online.top, practice.bottom)
        self.assertLess(abs(online.centerx - (practice.left + multi.right) / 2), 3)
        self.assertEqual({practice.size, multi.size, online.size}, {practice.size}, "one size")

    def test_a_controller_reaches_online(self):
        open_screen("match_setup")
        nav = app.navigator
        nav.snapshot()
        nav.active, nav.via = True, "pad"
        try:
            for start in ("opponent_ai", "opponent_human"):
                nav.key = start
                nav.move(0, 1, via = "pad")
                self.assertEqual(nav.key, "opponent_online", f"down from {start}")
        finally:
            nav.active, nav.key = False, None

    def test_ai_style_under_ai_level(self):
        """Rowan: "I want the AI style right below the AI's level" (and Adaptive AI under that, till:
        "you can remove adaptive AI, but keep the level and the style"); then "combine the AI level
        and AI style by calling it AI level slash style ... one pretty much right below the other"."""
        page = open_screen("match_setup")
        boxes = page.ui_hitboxes
        level = boxes["cycle_ai_left"].union(boxes["cycle_ai_right"])
        style = boxes["cycle_ai_style_left"].union(boxes["cycle_ai_style_right"])
        self.assertGreater(style.top, level.bottom)
        self.assertLess(style.top - level.bottom, 20, "close under it")
        self.assertIn("AI Level / Style", headings(page))
        self.assertNotIn("AI Style", headings(page), "one heading")
        self.assertEqual(style.width, level.width, "one width")
        self.assertLess(abs(style.centerx - level.centerx), 3, "in line under it")
        self.assertNotIn("toggle_adaptive_ai", boxes, "(in Match Settings)")

    def test_ai_style_works(self):
        m = app.settings.match
        self.addCleanup(m.reset)
        m.reset()
        page = open_screen("match_setup")
        style = m.ai_style
        click(page, "cycle_ai_style_right")
        self.assertEqual(m.ai_style, (style + 1) % len(m.ai_styles))
        m.vs_wall = True                    # against the wall there's no AI: its style greyed out
        click(page, "cycle_ai_style_right")
        self.assertEqual(m.ai_style, (style + 1) % len(m.ai_styles))

    def test_choose_talismans_and_modes_under_points_to_win(self):
        """(The gap under Points to Win: Rowan chose these over the Countdown.)"""
        page = open_screen("match_setup")
        boxes = page.ui_hitboxes
        points = boxes["cycle_win_score_left"].union(boxes["cycle_win_score_right"])
        talismans, modes = boxes["open_powerups"], boxes["open_modes"]
        self.assertGreater(talismans.top, points.bottom)
        self.assertEqual((talismans.top, talismans.size), (modes.top, modes.size), "side by side, one size")
        self.assertLess(abs((talismans.left + modes.right) / 2 - points.centerx), 3, "under it")
        self.assertIn("21 of 21 on", texts(page))
        click(page, "open_modes")
        harness.settle(app)
        current = app.state_manager.current()
        self.assertEqual((current.NAME, current.view), ("powerups", "modes"))
        page = open_screen("match_setup")
        click(page, "open_powerups")
        harness.settle(app)
        current = app.state_manager.current()
        self.assertEqual((current.NAME, current.view), ("powerups", "talismans"))

    def test_the_highlight_takes_the_nearest_in_its_path(self):
        """(Online, when it sat centred under Practice Mode and Multiplayer, was skipped going down: the
        paddle buttons further down were more directly in line.)  The nearest control across the way
        the highlight moves comes first."""
        rects = {"practice": pygame.Rect(694, 339, 252, 60), "multi": pygame.Rect(972, 339, 252, 60),
                 "online": pygame.Rect(833, 407, 252, 60), "red": pygame.Rect(619, 528, 119, 60),
                 "blue": pygame.Rect(764, 528, 119, 60), "ai": pygame.Rect(1039, 528, 116, 60)}
        nav = app.navigator
        with mock.patch.object(nav, "targets", lambda: rects), mock.patch.object(nav, "rect", lambda: rects[nav.key]), \
                mock.patch.object(nav, "reveal", lambda: None):
            nav.active, nav.via = True, "pad"
            try:
                for start in ("practice", "multi"):
                    nav.key = start
                    nav.move(0, 1, via = "pad")
                    self.assertEqual(nav.key, "online", f"down from {start}")
                nav.move(0, 1, via = "pad")
                self.assertIn(nav.key, ("blue", "ai"), "and on down to the next row")
            finally:
                nav.active, nav.key = False, None

    def test_the_court_description_wraps_under_its_picture(self):
        drawn = texts(open_screen("match_setup"))
        self.assertNotIn("The open court: nothing but you, the ball and the walls.", drawn, "(not on one long line)")
        joined = " ".join(t for t in drawn if t)
        self.assertIn("The open court: nothing but", joined)


if __name__ == "__main__":
    unittest.main()

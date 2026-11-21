"""Back at the bottom left of every menu (Rowan, 2026-11-21, after 1.9's release, for 1.9 and 2.0).

- "Any menu that has the back button at the bottom in the middle, I want you to move the back button
  to the bottom left.  And then if that replaces any buttons, then move those buttons to the middle."
- Settings: Back at the bottom left, Export and Import in the middle (Reset All stays at the right).
- Stats: Back at the bottom left; Export and Import Stats out of the panel, in the footer's middle;
  Reset Stats at the bottom right, out of the panel; Replays and Achievements stay in it, centred.
- Match Setup: Back at the bottom left, Start Match in the middle, Match Settings at the bottom right.
- Match settings: Back at the left and More Settings in the middle, opening your own settings
  (Display, Audio, UI and Controls), as from the main menu.
- The Talismans page's Switch to Modes was at the bottom left: it goes to the middle.
- The "Now playing" note slid in over the bottom left and hid Back: over a menu it's at the top left.
"""
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from config import BASE_W                                       # noqa: E402
from tests.test_settings_menus import click, open_screen        # noqa: E402

PAGES = ("match", "ball_paddles", "gameplay", "emote_settings", "display", "audio", "interface", "stats",
         "achievements", "replays", "powerups", "match_setup", "online")
sm = app.state_manager


def middle(rects):
    """The middle of a row of buttons."""
    return (min(r.left for r in rects) + max(r.right for r in rects)) / 2


class BackBottomLeft(unittest.TestCase):
    def tearDown(self):
        sm.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_every_page_has_back_at_the_bottom_left(self):
        panel = app.ui_layout.PANEL
        for name in PAGES + ("settings",):
            with self.subTest(name):
                back = open_screen(name).ui_hitboxes["back"]
                self.assertEqual(back.left, panel.left, "level with the panel's left edge")
                self.assertGreater(back.top, panel.bottom, "below the panel")

    def test_the_background_picker_too(self):
        back = open_screen("background_selection").ui_hitboxes["back"]
        self.assertLess(back.centerx, BASE_W // 4)

    def test_settings_export_and_import_in_the_middle(self):
        boxes = open_screen("settings").ui_hitboxes
        pair = [boxes["export_settings"], boxes["import_settings"]]
        self.assertLess(abs(middle(pair) - BASE_W / 2), 3)
        self.assertLess(boxes["back"].right, pair[0].left)
        self.assertGreater(boxes["reset_all"].left, pair[1].right)
        self.assertEqual({r.centery for r in pair + [boxes["back"], boxes["reset_all"]]}, {boxes["back"].centery})

    def test_stats_buttons(self):
        boxes = open_screen("stats").ui_hitboxes
        panel = app.ui_layout.PANEL
        inside = [boxes["open_replays"], boxes["open_achievements"]]
        self.assertTrue(all(panel.contains(r) for r in inside), "Replays and Achievements stay in the panel")
        self.assertLess(abs(middle(inside) - BASE_W / 2), 3, "centred")
        out = [boxes["export_stats"], boxes["import_stats"]]
        self.assertTrue(all(r.top > panel.bottom for r in out + [boxes["reset_stats"]]), "out of the panel")
        self.assertLess(abs(middle(out) - BASE_W / 2), 3, "Export and Import in the middle")
        self.assertEqual(boxes["reset_stats"].right, panel.right, "Reset Stats at the bottom right")
        self.assertEqual({r.centery for r in out + [boxes["reset_stats"]]}, {boxes["back"].centery})

    def test_match_setup(self):
        boxes = open_screen("match_setup").ui_hitboxes
        back, start, more = boxes["back"], boxes["start_match"], boxes["open_match_settings"]
        self.assertLess(abs(start.centerx - BASE_W / 2), 3, "Start Match in the middle")
        self.assertLess(abs(more.right - app.ui_layout.PANEL.right), 3, "Match Settings at the bottom right")
        self.assertLess(back.right, start.left)

    def test_match_settings_more_settings(self):
        page = open_screen("match")
        boxes = page.ui_hitboxes
        self.assertLess(abs(boxes["more_settings"].centerx - BASE_W / 2), 3)
        self.assertGreater(boxes["reset_defaults"].left, boxes["more_settings"].right)
        click(page, "more_settings")
        harness.settle(app)
        hub = sm.current()
        self.assertEqual(hub.NAME, "settings")
        hub.draw(app.virtual)
        cards = {"display", "audio", "interface", "gameplay"}
        self.assertTrue(cards <= set(hub.ui_hitboxes))
        self.assertNotIn("match", hub.ui_hitboxes, "your own settings only, as from the main menu")
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_ESCAPE, mod = 0, unicode = ""))
        for event in pygame.event.get():
            sm.handle_event(event)
        harness.settle(app)
        self.assertEqual(sm.current().NAME, "match", "Back goes back to Match settings")

    def test_more_settings_in_a_match_still_has_no_match_card(self):
        """From Pause > Settings > Match, More Settings mustn't lead round to Match again."""
        sm.set_state("game", mute = True)
        sm.push_state("pause", mute = True)
        sm.push_state("settings", mute = True)
        sm.push_state("match", mute = True)
        harness.settle(app)
        sm.current().draw(app.virtual)
        click(sm.current(), "more_settings")
        harness.settle(app)
        hub = sm.current()
        hub.draw(app.virtual)
        self.assertNotIn("match", hub.ui_hitboxes)

    def test_talismans_switch_in_the_middle(self):
        boxes = open_screen("powerups").ui_hitboxes
        self.assertLess(abs(boxes["switch_view"].centerx - BASE_W / 2), 3)

    def test_now_playing_note_clear_of_back(self):
        page = open_screen("settings")
        renderer = app.renderer
        renderer.show_toast("Now playing: a long track name for the test")
        renderer._toast[1] = 1.0                    # (slid in)
        before = app.virtual.copy()
        renderer.draw_toast(app.virtual, 0.0)
        back = page.ui_hitboxes["back"]
        diff =[(x, y) for x in range(back.left, back.right, 8) for y in range(back.top, back.bottom, 8)
                if app.virtual.get_at((x, y)) != before.get_at((x, y))]
        self.assertEqual(diff, [], "the note doesn't cover Back")
        renderer._toast = None


if __name__ == "__main__":
    unittest.main()

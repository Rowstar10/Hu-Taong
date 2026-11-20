"""The settings pages' rework, 1.9 (Rowan's 1.9 plan, phase 3, step 13b).

Every settings page in rows: a small heading over each section, each setting on its own row with
its name right-aligned beside its control, more room between them, and nothing shrunk past a size
that reads.  A page that still doesn't fit (Match, and Match from the pause menu) scrolls: with the
mouse wheel, the scrollbar, a finger, the controller's right stick (the wheel again), and the menus'
highlight, which scrolls to whatever it moves to.  From the pause menu, "Changes come in at the
next serve" stays put at the top.  No new tabs, and nothing moved between pages.
"""
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

from core.touch import TouchControls                            # noqa: E402

PAGES = [("gameplay",), ("display",), ("audio",), ("interface",), ("match",), ("match", "ball_paddles"),
         ("match", "powerups"), ("game", "pause", "match")]
nav = app.navigator


def open_page(*path):
    sm = app.state_manager
    sm.set_state("main_menu", mute = True)
    for name in path:
        sm.push_state(name, mute = True)
    harness.settle(app)
    page = sm.current()
    page.draw(app.virtual)
    return page


def to_window(pos):
    return (pos[0] / app.sx, pos[1] / app.sy)


def press(page, pos):
    pos = to_window(pos)
    page.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
    page.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos))


def settle_scroll(page):
    """Let the page catch up with where it's scrolled to, and draw it there."""
    page.scroll = page.scroll_target
    page.draw(app.virtual)


class Base(unittest.TestCase):
    def tearDown(self):
        for group in (app.settings.match, app.settings.gameplay, app.settings.display, app.settings.interface):
            group.reset()
        nav.active, nav.key = False, None
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)


class EveryPage(Base):
    def test_nothing_overlaps_or_spills_out(self):
        panel = app.ui_layout.PANEL
        for path in PAGES:
            with self.subTest(page = "/".join(path)):
                page = open_page(*path)
                boxes = {k: r for k, r in harness.every_box(page).items()
                         if k not in ("back", "reset_defaults", "scrollbar")}
                keys = sorted(boxes)
                for i, a in enumerate(keys):
                    if not getattr(page, "max_scroll", 0):
                        self.assertTrue(panel.contains(boxes[a]), f"{a} spills out of the panel")
                    for b in keys[i + 1:]:
                        self.assertFalse(boxes[a].colliderect(boxes[b]), f"{a} overlaps {b}")

    def test_a_size_that_reads(self):
        """Nothing shrunk much to fit: an on/off switch is as tall as at nine tenths of full size."""
        for path in PAGES:
            if path[-1] == "powerups":
                continue                        # (the talisman tiles: unchanged)
            with self.subTest(page = "/".join(path)):
                page = open_page(*path)
                switches = [r for k, r in harness.every_box(page).items() if k.startswith("toggle_")]
                self.assertTrue(switches)
                self.assertGreaterEqual(min(r.h for r in switches), 48)

    def test_rows_line_up(self):
        """In a column, each row's control starts at the same place, and its name ends just before."""
        columns = {("match",): ("cycle_win_score_left", "toggle_win_by_two", "toggle_middle_wall",
                                "cycle_countdown_left", "cycle_ai_left", "toggle_adaptive_ai", "cycle_court_left"),
                   ("display",): ("cycle_res_left", "cycle_mode_left", "apply", "cycle_max_fps_left",
                                  "toggle_show_fps", "cycle_effects_left", "toggle_screen_shake", "toggle_ball_trail"),
                   ("interface",): ("cycle_hud_left", "toggle_ai_banter", "toggle_friend_emotes",
                                    "cycle_instant_replay_left"),
                   ("gameplay",): ("cycle_pad_first_left", "pad_pause", "pad_list", "pad_emote_1", "pad_emote_5"),
                   ("audio",): ("toggle_paddle_sounds", "toggle_score_sounds", "toggle_menu_sounds",
                                "mute_master_volume", "mute_music_volume", "mute_sfx_volume")}
        for path, keys in columns.items():
            with self.subTest(page = "/".join(path)):
                boxes = harness.every_box(open_page(*path))
                lefts = {boxes[k].left for k in keys}
                self.assertEqual(len(lefts), 1, {k: boxes[k].left for k in keys})

    def test_cycles_share_a_width(self):
        """A column's cycles are as wide as each other, so their arrows line up too."""
        boxes = harness.every_box(open_page("match"))
        rights = {boxes[k].right for k in ("cycle_win_score_right", "cycle_countdown_right", "cycle_ai_right",
                                           "cycle_ai_style_right", "cycle_court_right")}
        self.assertEqual(len(rights), 1)

    def test_a_name_explains_its_control(self):
        """Pointing at a row's name shows its control's tooltip."""
        page = open_page("interface")
        form = next(n for n in harness_nodes(page) if type(n).__name__ == "Form")
        name, control = next((n, c) for n, c in form.rows if n is not None and c.tip)
        offered = []
        real = app.renderer.tips.offer
        app.renderer.tips.offer = lambda rect, tip: offered.append(tip)
        real_pointer = app.pointer
        app.pointer = lambda: name.rect.center
        try:
            page.draw(app.virtual)
        finally:
            app.renderer.tips.offer, app.pointer = real, real_pointer
        self.assertIn(control.tip if not callable(control.tip) else control.tip(), offered)

    def test_reset_ball_and_paddles_still_under_randomise(self):
        boxes = open_page("match", "ball_paddles").ui_hitboxes
        rand, reset = boxes["randomise_all"], boxes["reset_ball_and_paddles"]
        self.assertGreater(reset.top, rand.bottom - 1)
        self.assertLess(abs(reset.centerx - rand.centerx), 5)


def harness_nodes(page):
    from tests.test_settings_menus import laid_out
    return laid_out(page._laid[0])


class OnlyMatchScrolls(Base):
    def test_which_pages_scroll(self):
        for path in PAGES:
            with self.subTest(page = "/".join(path)):
                page = open_page(*path)
                scrolls = bool(getattr(page, "max_scroll", 0))
                self.assertEqual(scrolls, path[-1] == "match", "only the Match page needs to")


class Scrolling(Base):
    def setUp(self):
        self.page = open_page("match")
        self.hidden = "open_ball_paddles"         # at the bottom of the page: out of sight at first

    def test_starts_at_the_top_with_the_rest_out_of_sight(self):
        page = self.page
        self.assertEqual(page.scroll, 0)
        self.assertIn("cycle_win_score_left", page.ui_hitboxes)
        self.assertNotIn(self.hidden, page.ui_hitboxes)
        self.assertIn(self.hidden, page.ui_whole)
        self.assertIn("scrollbar", page.ui_hitboxes)

    def test_out_of_sight_isnt_clickable(self):
        """A control scrolled out of sight can't be clicked where it would be (under the footer)."""
        page = self.page
        where = page.ui_whole[self.hidden]
        self.assertFalse(page.scroll_view.colliderect(where))
        press(page, where.center)
        harness.settle(app)
        self.assertIs(app.state_manager.current(), page)

    def test_the_wheel(self):
        page = self.page
        page.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x = 0, y = -1, flipped = False))
        self.assertGreater(page.scroll_target, 0)
        for _ in range(20):
            page.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x = 0, y = -1, flipped = False))
        self.assertEqual(page.scroll_target, page.max_scroll, "no further than the end")
        settle_scroll(page)
        self.assertIn(self.hidden, page.ui_hitboxes)
        self.assertNotIn("cycle_win_score_left", page.ui_hitboxes)
        press(page, page.ui_hitboxes[self.hidden].center)
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "ball_paddles")

    def test_it_eases_there(self):
        page = self.page
        page.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x = 0, y = -2, flipped = False))
        page.update(1 / 60)
        self.assertTrue(0 < page.scroll < page.scroll_target)
        for _ in range(60):
            page.update(1 / 60)
        self.assertEqual(page.scroll, page.scroll_target)

    def test_dragging_the_scrollbar(self):
        page = self.page
        track = page.scroll_track
        page.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = to_window(page.scroll_handle.center)))
        self.assertTrue(page.dragging_scroll)
        page.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos = to_window((track.centerx, track.bottom + 50)),
                                             rel = (0, 300), buttons = (1, 0, 0)))
        self.assertEqual(page.scroll, page.max_scroll, "the handle follows the mouse, to the end")
        page.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = to_window(track.midbottom)))
        self.assertFalse(page.dragging_scroll)
        self.assertIs(app.state_manager.current(), page, "and it clicked nothing")

    def test_a_finger_sliding(self):
        """On a phone, sliding a finger up the page scrolls it down, keeping up with the finger."""
        page = self.page
        touch = TouchControls(app)
        x, y = page.scroll_view.centerx, page.scroll_view.bottom - 40
        events = touch.translate(pygame.event.Event(pygame.FINGERDOWN, finger_id = 1, touch_id = 1,
                                                    x = x / 1920, y = y / 1080))
        for step in range(1, 7):
            events += touch.translate(pygame.event.Event(pygame.FINGERMOTION, finger_id = 1, touch_id = 1,
                                                         x = x / 1920, y = (y - 50 * step) / 1080,
                                                         dx = 0, dy = -50 / 1080))
        events += touch.translate(pygame.event.Event(pygame.FINGERUP, finger_id = 1, touch_id = 1,
                                                     x = x / 1920, y = (y - 300) / 1080))
        events += touch.flush()
        for event in events:
            page.handle_event(event)
        self.assertAlmostEqual(page.scroll_target, min(page.max_scroll, 270), delta = 1, msg = "300 px of finger")
        harness.settle(app)
        self.assertIs(app.state_manager.current(), page, "a slide isn't a tap")

    def test_the_highlight_scrolls_to_what_it_moves_to(self):
        page = self.page
        app.navigator.snapshot()
        nav.active, nav.via, nav.key = True, "pad", "open_powerups"
        self.assertNotIn("open_powerups", page.ui_hitboxes, "(out of sight to start with)")
        nav.reveal()
        self.assertGreater(page.scroll_target, 0, "it scrolls down to it")
        settle_scroll(page)
        app.navigator.snapshot()
        self.assertIsNotNone(nav.on_show(), "and it's on show")
        self.assertTrue(page.scroll_view.contains(nav.on_show()))

    def test_pressing_out_of_sight_scrolls_first(self):
        page = self.page
        app.navigator.snapshot()
        nav.active, nav.via, nav.key = True, "pad", self.hidden
        self.assertEqual(nav.activate(via = "pad"), [], "no click where it isn't")
        self.assertGreater(page.scroll_target, 0)
        settle_scroll(page)
        app.navigator.snapshot()
        events = nav.activate(via = "pad")
        for event in events:
            page.handle_event(event)
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "ball_paddles")

    def test_down_from_the_last_row_goes_to_the_footer(self):
        """Back and Reset stay below the whole page, wherever it's scrolled."""
        page = self.page
        app.navigator.snapshot()
        nav.active, nav.via, nav.key = True, "pad", "back"
        nav.move(0, -1, via = "pad")
        self.assertIn(nav.key, page.ui_whole, "up from Back: onto the page")
        nav.move(0, 1, via = "pad")
        self.assertIn(nav.key, ("back", "reset_defaults"))
        nav.key = "open_ball_paddles"               # the last control on the page, out of sight
        nav.move(0, 1, via = "pad")
        self.assertIn(nav.key, ("back", "reset_defaults"), "down from it: Back or Reset, not up the page")


class FromThePauseMenu(Base):
    def test_the_note_stays_put(self):
        page = open_page("game", "pause", "match")
        self.assertTrue(page.note)
        note = page._laid[2].note
        top = note.rect.copy()
        self.assertLessEqual(note.rect.bottom, page.scroll_view.top, "above the part that scrolls")
        page.scroll_target = page.max_scroll
        settle_scroll(page)
        self.assertEqual(note.rect, top)
        self.assertTrue(all(r.top >= page.scroll_view.top for k, r in page.ui_hitboxes.items()
                            if k in page.ui_whole), "nothing scrolls over it")


if __name__ == "__main__":
    unittest.main()

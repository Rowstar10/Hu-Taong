"""Fewer buttons on the pause and result screens, 1.7 (Rowan's playtest of 1.7, 2026-11-17).

Pause: Reset (now Reset Point) and Reset Scores (now Reset Match) live under one Reset button that
opens and closes, and Match Settings is gone (Settings has it): five buttons, from seven.  The
result screens: Highlights moved into the replay, and Replay is View Replay.  Settings' Interface
card is called UI.
"""
import unittest

from tests import harness

app = harness.app()

import pygame                                                   # noqa: E402

sm = app.state_manager
PAUSE_KEYS = {"resume", "reset", "watch_replay", "settings", "main_menu"}


def click(screen, key):
    screen.draw(app.virtual)
    x, y = screen.ui_hitboxes[key].center
    pos = (x / app.sx, y / app.sy)
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1, pos = pos))
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button = 1, pos = pos))


def buttons(screen):
    screen.draw(app.virtual)
    return set(harness.buttons(screen, app))


class Pause(unittest.TestCase):
    def setUp(self):
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        self.game = sm.current().game
        self.game.countdown, self.game.paused = None, False
        sm.push_state("pause", mute = True)
        harness.settle(app)
        self.pause = sm.current()

    def tearDown(self):
        sm.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_five_buttons(self):
        self.assertEqual(buttons(self.pause) & (PAUSE_KEYS | {"reset_point", "reset_match", "match_settings",
                                                              "reset_scores"}), PAUSE_KEYS)

    def test_reset_opens_and_closes(self):
        click(self.pause, "reset")
        self.assertLessEqual({"reset_point", "reset_match"}, buttons(self.pause))
        boxes = self.pause.ui_hitboxes
        self.assertGreater(boxes["reset_point"].top, boxes["reset"].bottom, "beneath Reset")
        self.assertLess(boxes["reset_point"].bottom, boxes["watch_replay"].top)
        click(self.pause, "reset")
        self.assertFalse({"reset_point", "reset_match"} & buttons(self.pause))

    def test_their_names(self):
        click(self.pause, "reset")
        names = {key: text for key, text, *_ in self.pause_buttons()}
        self.assertEqual(names["reset_point"], "Reset Point")
        self.assertEqual(names["reset_match"], "Reset Match")
        self.assertEqual(names["watch_replay"], "View Replay")

    def pause_buttons(self):
        shown = []
        real = app.renderer.draw_overlay
        app.renderer.draw_overlay = lambda state, screen, **k: shown.extend(k.get("buttons") or []) or real(state, screen, **k)
        try:
            self.pause.draw(app.virtual)
        finally:
            app.renderer.draw_overlay = real
        return shown

    def test_reset_point_serves_again(self):
        g = self.game
        g.p1.score = 3
        click(self.pause, "reset")
        click(self.pause, "reset_point")
        harness.settle(app)
        self.assertIsNotNone(g.countdown, "a new serve")
        self.assertEqual(g.p1.score, 3, "the score stays")

    def test_reset_match_asks_first(self):
        click(self.pause, "reset")
        click(self.pause, "reset_match")
        harness.settle(app)
        self.assertEqual(sm.current().NAME, "confirm_choice")


class Results(unittest.TestCase):
    def setUp(self):
        sm.set_state("main_menu", mute = True)
        sm.push_state("game", mute = True)
        harness.settle(app)
        game = sm.current().game
        for _ in range(240):
            game.recorder.capture(1 / 60)
        sm.push_state("win", p1 = game.p1, p2 = game.p2, winner = game.p1, loser = game.p2, mute = True)
        harness.settle(app)
        self.win = sm.current()
        self.win.reel_shown = True                              # (no highlights playing by themselves)

    def tearDown(self):
        sm.set_state("main_menu", mute = True)
        harness.settle(app)

    def test_no_highlights_button(self):
        self.assertNotIn("highlights", buttons(self.win))
        self.assertIn("watch_replay", buttons(self.win))

    def test_the_highlights_are_in_view_replay(self):
        from game.replay import Moment
        self.win.reel = lambda: [Moment("A great save", 9.0, 60, 30, 120, 1), Moment("A long rally", 8.0, 180, 150, 230, 2)]
        click(self.win, "watch_replay")
        harness.settle(app)
        viewer = sm.current()
        self.assertEqual((viewer.NAME, viewer.mode), ("replay", "viewer"))
        viewer.draw(app.virtual)
        self.assertIn("replay_highlights", viewer.ui_hitboxes)
        click(viewer, "replay_highlights")
        self.assertEqual(viewer.mode, "reel")
        self.assertEqual(viewer.caption(), "Highlight 1 of 2:  A great save")
        viewer.finished()
        viewer.finished()                                       # past the last one: back to the viewer
        self.assertEqual(viewer.mode, "viewer")
        self.assertIs(sm.current(), viewer, "still in the replay")
        click(viewer, "replay_highlights")
        viewer.handle_event(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_ESCAPE, mod = 0, unicode = "", scancode = 0))
        self.assertEqual(viewer.mode, "viewer", "Esc leaves the highlights, not the replay")

    def test_no_highlights_no_button(self):
        self.win.reel = lambda: []
        click(self.win, "watch_replay")
        harness.settle(app)
        viewer = sm.current()
        viewer.draw(app.virtual)
        self.assertNotIn("replay_highlights", viewer.ui_hitboxes)


class Words(unittest.TestCase):
    def test_settings_calls_it_ui(self):
        from render.renderer import TIPS
        self.assertTrue(TIPS["interface"].startswith("UI\n"))
        texts = []
        real = app.renderer.draw_lacquer
        app.renderer.draw_lacquer = lambda screen, mouse, rect, text, *a, **k: texts.append(text) or real(screen, mouse, rect, text, *a, **k)
        try:
            sm.set_state("settings", mute = True)
            harness.settle(app)
            sm.current().draw(app.virtual)
        finally:
            app.renderer.draw_lacquer = real
            sm.set_state("main_menu", mute = True)
            harness.settle(app)
        self.assertIn("UI", texts)
        self.assertNotIn("Interface", texts)


if __name__ == "__main__":
    unittest.main()

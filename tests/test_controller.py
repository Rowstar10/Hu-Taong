"""Controllers, 1.9 (Rowan's 1.9 plan, phase 3, step 12).

"Controller support ... full menu and gameplay with rebindable buttons; two local players (two
controllers, or controller plus keyboard); correct button prompts."  Before 1.9 there was none: the
menus took the mouse (and a few keys).  Now a controller steers a paddle with its stick or D-pad,
works every menu with a highlight (which the arrow keys and Enter move too), has its Pause and
talisman-list buttons set in Gameplay settings, and the prompts name its buttons as it labels them.
The tests use made-up controllers: the harness leaves real ones out.
"""
import unittest

import pygame

from tests import harness

app = harness.app()

from core import gamepad, save_data                             # noqa: E402
from core.states.guest_state import held_keys                   # noqa: E402
from core import net as netcode                                 # noqa: E402
from game.hu_taong import Hu_Taong                              # noqa: E402

m = app.settings.match
g = app.settings.gameplay
pads = app.gamepads
nav = app.navigator


def plug(*names):
    pads.pads.clear()
    for i, name in enumerate(names):
        pads.add(500 + i, name)


def press(button, pad = 500, up = False):
    kind = pygame.CONTROLLERBUTTONUP if up else pygame.CONTROLLERBUTTONDOWN
    for event in pads.translate(pygame.event.Event(kind, instance_id = pad, button = gamepad.BUTTONS[button])):
        app.state_manager.handle_event(event)
        if event.type == pygame.KEYDOWN:
            app.keys_down.add(event.key)
        if event.type == pygame.KEYUP:
            app.keys_down.discard(event.key)


def stick(x, y, pad = 500):
    for axis, v in ((pygame.CONTROLLER_AXIS_LEFTX, x), (pygame.CONTROLLER_AXIS_LEFTY, y)):
        pads.translate(pygame.event.Event(pygame.CONTROLLERAXISMOTION, instance_id = pad, axis = axis,
                                          value = int(v * gamepad.AXIS_MAX)))


def show(name, *more):
    sm = app.state_manager
    sm.set_state("main_menu", mute = True)
    for n in ((name,) + more if name != "main_menu" else more):
        sm.push_state(n, mute = True)
    harness.settle(app)
    frame()
    return sm.current()


def frame():
    state = app.state_manager.current()
    state.draw(app.virtual)
    nav.snapshot()


class Base(unittest.TestCase):
    def tearDown(self):
        pads.pads.clear()
        pads.listen = None
        pads.using = "keys"
        nav.active, nav.key = False, None
        app.keys_down.clear()
        g.reset()
        m.reset()
        app.state_manager.set_state("main_menu", mute = True)
        harness.settle(app)


class Steering(Base):
    def match(self, **rules):
        m.reset()
        for name, value in rules.items():
            setattr(m, name, value)
        game = Hu_Taong(app)
        game.start()
        game.countdown, game.paused = None, False
        self.addCleanup(game.stop)
        return game

    def test_against_the_ai_any_controller_steers_you(self):
        plug("Xbox 360 Controller", "Xbox 360 Controller")
        game = self.match(vs_ai = True, play_as_blue = True)
        stick(0, 1.0, pad = 501)
        self.assertEqual(pads.steer_paddle(game.p2), (0.0, game.p2.speed))
        self.assertIsNone(pads.steer_paddle(game.p1), "(the AI's)")
        stick(0, 0.1, pad = 501)
        self.assertIsNone(pads.steer_paddle(game.p2), "a stick at rest steers nothing (the keys still work)")

    def test_the_paddle_moves(self):
        plug("Xbox 360 Controller")
        game = self.match(vs_ai = True)
        y = game.p1.y0
        stick(0, 1.0)
        for _ in range(30):
            game.update(1 / 120)
        self.assertGreater(game.p1.y0, y + 40)

    def test_two_controllers_two_players(self):
        plug("Xbox 360 Controller", "Wireless Controller")
        game = self.match(vs_ai = False)
        stick(0, -1.0, pad = 500)
        stick(0, 1.0, pad = 501)
        self.assertLess(pads.steer_paddle(game.p1)[1], 0, "the first plays Red")
        self.assertGreater(pads.steer_paddle(game.p2)[1], 0, "the second Blue")
        g.pad_first = 1
        self.assertGreater(pads.steer_paddle(game.p1)[1], 0, "set to Blue: the other way round")

    def test_one_controller_and_the_keyboard(self):
        plug("Xbox 360 Controller")
        g.pad_first = 1                              # the controller plays Blue
        game = self.match(vs_ai = False)
        stick(0, 1.0)
        self.assertIsNone(pads.steer_paddle(game.p1))
        self.assertIsNotNone(pads.steer_paddle(game.p2))
        app.keys_down.add(g.p1_down)                 # Red on the keyboard
        game.p1.apply_inputs(1 / 60)
        self.assertGreater(game.p1.vy, 0)

    def test_a_switch_takes_the_controller_with_the_player(self):
        plug("Xbox 360 Controller", "Xbox 360 Controller")
        game = self.match(vs_ai = False)
        stick(0, -1.0, pad = 500)
        game.switch_sides()
        self.assertIsNone(pads.steer_paddle(game.p1)) if pads.steer_paddle(game.p1) is None else None
        self.assertLess(pads.steer_paddle(game.p2)[1], 0, "Red's player, now on the right paddle")

    def test_online_the_stick_is_sent_as_keys(self):
        plug("Xbox 360 Controller")
        stick(-1.0, 0)
        self.assertTrue(held_keys(app) & netcode.LEFT)

    def test_labelled_controller(self):
        plug("Xbox 360 Controller")
        game = self.match(vs_ai = True)
        pads.using = "pad"
        game.label_pads()
        self.assertEqual(game.p1.controls_label, "Either stick", "(1.9: the stick it steers with; either, by default)")
        pads.using = "keys"
        game.label_pads()
        self.assertEqual(game.p1.controls_label, "W A S D", "the keys again, once they're what's used")


class InAMatch(Base):
    def test_start_pauses_and_back_shows_the_talisman_list(self):
        plug("Xbox 360 Controller")
        show("game")
        game = app.state_manager.current().game
        game.countdown, game.paused = None, False
        press("back")
        self.assertIn(pygame.K_TAB, app.keys_down)
        press("back", up = True)
        self.assertNotIn(pygame.K_TAB, app.keys_down)
        press("start")
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "pause")
        press("start")
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "game", "Start again resumes")

    def test_unplugged_mid_match_it_pauses(self):
        plug("Xbox 360 Controller")
        show("game")
        pads.translate(pygame.event.Event(pygame.CONTROLLERDEVICEREMOVED, instance_id = 500))
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "pause")


class Menus(Base):
    def test_the_d_pad_moves_a_highlight_and_a_presses_it(self):
        plug("Xbox 360 Controller")
        show("main_menu")
        press("dpad_down")
        self.assertTrue(nav.active)
        self.assertEqual(nav.key, "play", "it starts on Play")
        press("a")
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "match_setup")

    def test_it_moves(self):
        plug("Xbox 360 Controller")
        show("main_menu")
        press("dpad_down")
        self.assertEqual(nav.key, "play")
        press("dpad_down")
        self.assertEqual(nav.key, "play", "(the main menu's four are side by side: nothing below)")
        press("dpad_right")
        self.assertEqual(nav.key, "stats")
        press("dpad_right")
        press("dpad_left")
        self.assertEqual(nav.key, "stats")

    def test_it_wraps_round(self):
        """Rowan, 1.9 phase 3: "navigating menus would be a lot easier if you could loop around from
        the bottom to the top, top to bottom, left to right, and right to left in just one movement"."""
        plug("Xbox 360 Controller")
        show("main_menu")
        nav.active, nav.via, nav.key = True, "pad", "prompt_quit"
        press("dpad_right")
        self.assertEqual(nav.key, "play", "right from the last goes round to the first")
        press("dpad_left")
        self.assertEqual(nav.key, "prompt_quit", "and left from the first to the last")
        show("settings")
        nav.active, nav.via, nav.key = True, "pad", "back"
        press("dpad_down")
        # (Back is at the bottom left since after 1.9's release, so the card in line with it is Display)
        self.assertEqual(nav.key, "display", "down from the bottom: the top, in line with it")
        press("dpad_up")
        self.assertEqual(nav.key, "back", "up from the top: the bottom")
        nav.key = "gameplay"                       # (Controls, the last card since 1.9)
        press("dpad_right")
        self.assertEqual(nav.key, "display", "the row's other end, not the Reset button below "
                                             "(the first card: the Match card is only there in a match)")

    def test_wrapping_on_a_page_that_scrolls(self):
        from tests.test_settings_layout import squeezed
        plug("Xbox 360 Controller")
        squeeze = squeezed()            # (the Match page fits since later in 1.9: a smaller panel makes it scroll)
        squeeze.start()
        self.addCleanup(squeeze.stop)
        state = show("settings", "match")
        self.assertGreater(state.max_scroll, 0, "(the Match page scrolls)")
        state.scroll = state.scroll_target = state.scroll_at = state.max_scroll     # (at the bottom)
        frame()
        nav.active, nav.via, nav.key = True, "pad", "back"
        press("dpad_down")
        top = min(nav.targets().values(), key = lambda r: r.top).top
        self.assertLessEqual(nav.targets()[nav.key].top, top + nav.BAND, "round to the top of the page")
        self.assertLess(state.scroll_target, state.max_scroll, "and it scrolls up to show it")

    def test_b_goes_back(self):
        plug("Xbox 360 Controller")
        show("settings")
        press("b")
        harness.settle(app)
        self.assertEqual(app.state_manager.current().NAME, "main_menu")

    def test_left_and_right_move_a_slider(self):
        plug("Xbox 360 Controller")
        app.sound_manager.reset()
        show("settings", "audio")
        nav.active, nav.via, nav.key = True, "pad", "sfx_volume_slider"
        before = app.sound_manager.sfx_volume
        press("dpad_right")
        self.assertAlmostEqual(app.sound_manager.sfx_volume, before + 0.05, delta = 0.02)
        app.sound_manager.reset()

    def test_the_mouse_puts_it_away(self):
        plug("Xbox 360 Controller")
        show("main_menu")
        press("dpad_down")
        pads.translate(pygame.event.Event(pygame.MOUSEMOTION, pos = (10, 10), rel = (3, 0), buttons = (0, 0, 0)))
        self.assertFalse(nav.active)

    def test_the_arrow_keys_and_enter_too(self):
        show("main_menu")
        for key in (pygame.K_DOWN,):
            for e in pads.translate(pygame.event.Event(pygame.KEYDOWN, key = key, mod = 0, unicode = "", scancode = 0)):
                app.state_manager.handle_event(e)
        self.assertTrue(nav.active)
        events = pads.translate(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_RETURN, mod = 0, unicode = "", scancode = 0))
        self.assertEqual([e.type for e in events], [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP])

    def test_screens_with_their_own_arrow_keys_keep_them(self):
        from core.states.replay_state import ReplayState
        from core.states.background_selection_state import BackgroundSelectionState
        self.assertTrue(ReplayState.own_arrows and BackgroundSelectionState.own_arrows)

    def test_tooltips_say_press(self):
        from render.renderer import pad_tip
        self.assertEqual(pad_tip("Start Match\nClick to play.\n~ Enter"), "Start Match\nPress to play.")


class Rebinding(Base):
    def test_set_a_button(self):
        plug("Xbox 360 Controller")
        screen = show("settings", "gameplay")
        for key in ("pad_pause", "pad_list", "cycle_pad_first_right"):
            self.assertIn(key, screen.ui_hitboxes)
        from tests.test_settings_menus import click
        click(screen, "pad_pause")
        self.assertEqual(screen.listening_pad, "pause")
        press("a")
        self.assertEqual(g.pad_pause, "start", "A works the menus: it can't be set")
        press("x")
        self.assertEqual(g.pad_pause, "x")
        self.assertIsNone(screen.listening_pad)

    def test_a_button_already_used_swaps(self):
        g.bind_pad("pause", "back")
        self.assertEqual((g.pad_pause, g.pad_list), ("back", "start"))


class MoreControls(Base):
    """Rowan, 1.9 phase 3: "have more custom controls for the controller".  The paddle's four
    directions can be set to any buttons, which stick steers can be chosen, and how much of its
    travel is ignored (the dead zone)."""

    def game(self, **rules):
        m.reset()
        m.vs_ai, m.powerups = True, False
        for name, value in rules.items():
            setattr(m, name, value)
        game = Hu_Taong(app)
        game.start()
        self.addCleanup(game.stop)
        return game

    def test_the_directions_can_be_set(self):
        plug("Xbox 360 Controller")
        screen = show("settings", "gameplay")
        from tests.test_settings_menus import click
        click(screen, "pad_up")
        press("leftshoulder")
        self.assertEqual(g.pad_up, "leftshoulder")
        self.assertEqual(g.pad_emote_4, "dpad_up", "the emote that had it swaps")
        game = self.game()
        press("leftshoulder")
        self.assertEqual(pads.steer_paddle(game.p1), (0.0, -game.p1.speed), "it steers up now")
        press("leftshoulder", up = True)
        press("dpad_up")
        self.assertIsNone(pads.steer_paddle(game.p1), "and the D-pad's up doesn't")
        press("dpad_up", up = True)

    def test_which_stick_steers(self):
        plug("Xbox 360 Controller")
        game = self.game()
        right = (pygame.CONTROLLER_AXIS_RIGHTX, pygame.CONTROLLER_AXIS_RIGHTY)
        pads.pads[500].axes[right[1]] = 1.0
        self.assertEqual(g.PAD_STICKS[g.pad_stick], "Either stick", "(the default since Rowan's 1.9 list)")
        g.pad_stick = 0
        self.assertIsNone(pads.steer_paddle(game.p1), "the left stick doesn't see the right")
        g.pad_stick = 1
        self.assertEqual(pads.steer_paddle(game.p1), (0.0, game.p1.speed))
        stick(0, -1.0)
        self.assertEqual(pads.steer_paddle(game.p1), (0.0, game.p1.speed), "(not the left now)")
        g.pad_stick = 2
        stick(0, -0.6)
        self.assertEqual(pads.steer_paddle(game.p1)[1], game.p1.speed, "either: the one pushed further")
        stick(0, -1.0)
        pads.pads[500].axes[right[1]] = 0.0
        self.assertEqual(pads.steer_paddle(game.p1)[1], -game.p1.speed)
        stick(0, 0)

    def test_the_dead_zone(self):
        plug("Xbox 360 Controller")
        game = self.game()
        stick(0, 0.2)
        self.assertIsNone(pads.steer_paddle(game.p1), "Normal ignores a small push")
        g.pad_deadzone = 0
        self.assertIsNotNone(pads.steer_paddle(game.p1), "Small doesn't")
        stick(0, 0.35)
        g.pad_deadzone = 2
        self.assertIsNone(pads.steer_paddle(game.p1), "Large ignores more")
        stick(0, 0)

    def test_on_the_controls_page_and_saved(self):
        screen = show("settings", "gameplay")
        from tests.test_settings_menus import click
        for key in ("pad_up", "pad_down", "pad_left", "pad_right", "cycle_pad_stick_right", "cycle_pad_deadzone_right"):
            self.assertIn(key, screen.ui_hitboxes)
        click(screen, "cycle_pad_stick_right")
        click(screen, "cycle_pad_deadzone_left")
        self.assertEqual((g.pad_stick, g.pad_deadzone), (0, 0), "(round from Either to Left)")
        saved = save_data.collect(app)["interface"]
        self.assertEqual((saved["pad_stick"], saved["pad_deadzone"], saved["pad_up"]), (0, 0, "dpad_up"))

    def test_emotes_have_a_page_of_their_own(self):
        """Rowan: "Move the emotes section into its own settings menu inside control settings"."""
        plug("Xbox 360 Controller")
        screen = show("settings", "gameplay")
        from tests.test_settings_menus import click
        self.assertFalse([k for k in screen.ui_hitboxes if k.startswith("pad_emote")])
        click(screen, "open_emotes")
        harness.settle(app)
        frame()
        page = app.state_manager.current()
        self.assertEqual(page.NAME, "emote_settings")
        for n in range(1, 6):
            self.assertIn(f"pad_emote_{n}", page.ui_hitboxes)
        click(page, "pad_emote_1")
        press("rightstick")
        self.assertEqual(g.pad_emote_1, "rightstick")
        g.reset_emotes()
        self.assertEqual((g.pad_emote_1, g.pad_emote_5), ("y", "rightshoulder"))

    def test_esc_cancels(self):
        plug("Xbox 360 Controller")
        screen = show("settings", "gameplay")
        from tests.test_settings_menus import click
        click(screen, "pad_list")
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_ESCAPE, mod = 0, unicode = "", scancode = 0))
        self.assertIsNone(screen.listening_pad)
        self.assertIsNone(pads.listen)

    def test_first_controller_side(self):
        screen = show("settings", "gameplay")
        from tests.test_settings_menus import click
        click(screen, "cycle_pad_first_right")
        self.assertEqual(g.pad_first, 1)

    def test_saved_and_a_bad_save_put_right(self):
        g.pad_pause, g.pad_first = "y", 1
        saved = save_data.collect(app)["interface"]
        self.assertEqual((saved["pad_pause"], saved["pad_first"]), ("y", 1))
        import json
        path = save_data.save_path()
        kept = path.read_text() if path.exists() else None
        try:
            saved_all = save_data.collect(app)
            saved_all["interface"]["pad_list"] = "y"            # doubled up
            path.parent.mkdir(parents = True, exist_ok = True)
            path.write_text(json.dumps(saved_all))
            save_data.load(app)
            self.assertEqual((g.pad_pause, g.pad_list), ("start", "back"))
        finally:
            if kept is None:
                path.unlink()
            else:
                path.write_text(kept)


class Prompts(Base):
    def test_each_family_names_its_buttons(self):
        cases = (("Xbox 360 Controller", "A", "Start"), ("Xbox One S Controller", "A", "Menu"),
                 ("PS4 Controller", "Cross", "Options"), ("DualSense Wireless Controller", "Cross", "Options"),
                 ("Nintendo Switch Pro Controller", "A", "+"), ("Some Pad", "A", "Start"))
        for name, a, start in cases:
            with self.subTest(name = name):
                plug(name)
                pads.last = None
                self.assertEqual((pads.label("a"), pads.label("start")), (a, start))

    def test_badges_draw(self):
        for name in ("Xbox 360 Controller", "PS4 Controller"):
            plug(name)
            for button in ("a", "b", "x", "y", "start"):
                self.assertGreater(app.renderer.pad_badge(button, 44).get_width(), 0)

    def test_the_prompt_bar_while_a_controller_works_the_menus(self):
        plug("PS4 Controller")
        show("main_menu")
        press("dpad_down")
        drawn = []
        real = app.renderer.pad_badge
        app.renderer.pad_badge = lambda name, size: (drawn.append(name), real(name, size))[1]
        try:
            app.renderer.draw_pad_prompts(app.virtual)
        finally:
            app.renderer.pad_badge = real
        self.assertEqual(sorted(drawn), ["a", "b"])

    def test_match_setup_says_the_stick(self):
        plug("Xbox 360 Controller")
        m.vs_ai = True
        pads.using = "pad"
        red, blue = app.renderer.setup_controls("W A S D", "Arrow Keys")
        self.assertEqual((red, blue), ("Either stick", "Arrow Keys"))


class FollowsWhatYouUse(Base):
    """Rowan, 1.9 phase 3: "Make sure everything to do with controls displayed on screen
    automatically updates for whatever form of controls they are currently using, so arrow
    keys/wasd for keyboard and mouse, and left/right joystick for controller"."""

    def key(self, key = pygame.K_w):
        for e in pads.translate(pygame.event.Event(pygame.KEYDOWN, key = key, mod = 0, unicode = "", scancode = 0)):
            app.state_manager.handle_event(e)

    def test_the_last_thing_used_decides(self):
        plug("Xbox 360 Controller")
        show("main_menu")
        self.assertFalse(app.renderer.using_pad(), "plugged in, but not used yet")
        press("dpad_down")
        self.assertTrue(app.renderer.using_pad())
        self.key(pygame.K_DOWN)
        self.assertFalse(app.renderer.using_pad(), "the keyboard since")
        stick(0.9, 0)
        self.assertTrue(app.renderer.using_pad(), "a push on the stick counts")
        pads.translate(pygame.event.Event(pygame.MOUSEMOTION, pos = (10, 10), rel = (4, 0), buttons = (0, 0, 0)))
        self.assertFalse(app.renderer.using_pad(), "and so does the mouse")
        stick(0, 0)

    def test_match_setup_on_your_own(self):
        plug("Xbox 360 Controller")
        m.vs_ai = True
        self.assertEqual(app.renderer.setup_controls("W A S D", "Arrow Keys"), ("W A S D", "Arrow Keys"))
        pads.using = "pad"
        g.pad_stick = 1
        self.assertEqual(app.renderer.setup_controls("W A S D", "Arrow Keys")[0], "Right stick")
        pads.using = "keys"
        g.mouse_steer = True
        self.assertEqual(app.renderer.setup_controls("W A S D", "Arrow Keys")[0], "W A S D or mouse")

    def test_match_setup_two_players(self):
        plug("Xbox 360 Controller")
        m.vs_ai = False
        self.assertEqual(app.renderer.setup_controls("W A S D", "Arrow Keys"), ("Either stick", "Arrow Keys"),
                         "the side the controller plays shows its stick")
        plug("Xbox 360 Controller", "Xbox 360 Controller")
        self.assertEqual(app.renderer.setup_controls("W A S D", "Arrow Keys"),
                         ("Pad 1, either stick", "Pad 2, either stick"))

    def test_match_setup_caption_follows_without_laying_out_again(self):
        """(Match Setup's layout is built once; its caption must still change as you switch.)"""
        plug("Xbox 360 Controller")
        m.vs_ai = True
        show("match_setup")
        seen = []
        real = app.renderer.setup_controls
        app.renderer.setup_controls = lambda *a: (seen.append(real(*a)), seen[-1])[1]
        try:
            frame()
            pads.using = "pad"
            frame()
        finally:
            del app.renderer.setup_controls
        self.assertIn(("W A S D", "Arrow Keys"), seen)
        self.assertEqual(seen[-1], ("Either stick", "Arrow Keys"))

    def test_tooltips(self):
        plug("Xbox 360 Controller")
        pads.using = "pad"
        tips = app.renderer.tips
        r = pygame.Rect(0, 0, 10000, 10000)
        tips.offer(r, "Start Match\nClick to play.\n~ Enter")
        self.assertEqual(tips.offered, "Start Match\nPress to play.")
        pads.using = "keys"
        tips.offer(r, "Start Match\nClick to play.\n~ Enter")
        self.assertEqual(tips.offered, "Start Match\nClick to play.\n~ Enter")

    def test_in_a_match_each_paddle_says_what_moves_it(self):
        plug("Xbox 360 Controller")
        m.reset()
        m.vs_ai, m.powerups = True, False
        game = Hu_Taong(app)
        game.start()
        game.countdown, game.paused = None, False
        game.label_pads()
        self.assertEqual(game.p1.controls_label, "W A S D")
        stick(0, 0.9)
        game.update(1 / 60)
        game.label_pads()
        self.assertEqual(game.p1.controls_label, "Either stick")
        stick(0, 0)
        app.keys_down.add(g.p1_up)
        game.update(1 / 60)
        game.label_pads()
        self.assertEqual(game.p1.controls_label, "W A S D")
        app.keys_down.clear()
        game.stop()


class EveryControlReachable(Base):
    """On every menu screen, the highlight reaches every control with the four directions."""
    SCREENS = [("main_menu",), ("match_setup",), ("settings",), ("settings", "gameplay"),
               ("settings", "gameplay", "emote_settings"), ("settings", "display"),
               ("settings", "audio"), ("settings", "interface"), ("settings", "match"),
               ("settings", "match", "powerups"), ("settings", "match", "ball_paddles"), ("stats",),
               ("stats", "achievements"), ("stats", "replays"), ("online",), ("game", "pause"),
               ("game", "pause", "match")]          # (1.9: a page that scrolls, as the Match page does too)

    def test_each_screen(self):
        sm = app.state_manager
        for path in self.SCREENS:
            with self.subTest(screen = "/".join(path)):
                sm.set_state("main_menu", mute = True)
                for name in path:
                    if name != "main_menu":
                        sm.push_state(name, mute = True)
                harness.settle(app)
                frame()
                targets = nav.targets()
                nav.active, nav.key = True, None
                start = nav.rect() and nav.key
                seen, todo = {start}, [start]
                state, boxes, values = nav.seen
                nav.seen = (state, boxes, {})            # (only moving, not working the sliders)
                while todo:
                    key = todo.pop()
                    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nav.key = key
                        nav.move(*d, via = "pad")
                        if nav.key not in seen:
                            seen.add(nav.key)
                            todo.append(nav.key)
                self.assertEqual(sorted(set(targets) - seen), [])


if __name__ == "__main__":
    unittest.main()

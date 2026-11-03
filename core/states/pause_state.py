import pygame

from core.states.game_state import GameState
from core.states.base_state import State
from render import theme

class PauseState(State):
    NAME = "pause"
    is_menu = True
    is_overlay = True

    TIPS = {"resume": "Back to the match. (Esc)",
            "reset": "Restart this match from 0-0.",
            "settings": "Change settings without leaving the match.",
            "main_menu": "Leave this match.",
            "p1_ai": "Let the AI play the red paddle, or take it back.",
            "p2_ai": "Let the AI play the blue paddle, or take it back."}

    def __init__(self, app):
        super().__init__(app)
        self.game_state = self.app.state_manager.get_state(GameState)
        self.ui_cols = 2

    def enter(self, **kwargs):
        sound_manager = self.app.sound_manager
        sound_manager.play("startup2.wav")
        sound_manager.multiplier = 0.1
        sound_manager.update_music_volume()

    def exit(self, **kwargs):
        super().exit(**kwargs)
        sound_manager = self.app.sound_manager
        sound_manager.multiplier = 1
        sound_manager.update_music_volume()

    def update(self, dt):
        pass

    def draw(self, screen):
        super().draw(screen)
        buttons = [("resume", "Resume", theme.GREEN, theme.GREEN_HOVER),
                   ("reset", "Reset", theme.BLUE, theme.BLUE_HOVER),
                   ("settings", "Settings", theme.ORANGE, theme.ORANGE_HOVER),
                   ("main_menu", "Main Menu", theme.RED, theme.RED_HOVER)]

        # The AI toggles live here only, so a match itself stays uncluttered
        toggles = None
        if self.game_state and self.game_state.game:
            game = self.game_state.game
            toggles = [("p1_ai", "Red AI", lambda: game.p1.ai_enabled),
                       ("p2_ai", "Blue AI", lambda: game.p2.ai_enabled)]

        self.app.renderer.draw_overlay(self, screen,
                                       title = "Paused", buttons = buttons, mark = "停",
                                       toggles = toggles, tips = self.TIPS)

    def handle_event(self, event):
        super().handle_event(event)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.pop_state(mute = True)
            self.app.sound_manager.play("shutdown.wav")

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state(mute = True)
            self.app.sound_manager.play("shutdown.wav")

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            sound_manager = self.app.sound_manager
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)

            if key == "p1_ai":
                self.game_state.game.p1.ai_enabled = not self.game_state.game.p1.ai_enabled
                self.game_state.game.p1.ai.reset()

            if key == "p2_ai":
                self.game_state.game.p2.ai_enabled = not self.game_state.game.p2.ai_enabled
                self.game_state.game.p2.ai.reset()

            if key == "resume":
                self.pop_state(mute = True)
                self.app.sound_manager.play("shutdown.wav")

            if key == "reset":
                if self.game_state:
                    action = lambda: (self.game_state.restart(),
                                      self.pop_state(mute = True),
                                      self.pop_state(mute = True),
                                      sound_manager.play("enter_state.wav"))

                    self.push_state("confirm_choice", action = action, header = "Reset Game?", mute = True)

            if key == "settings":
                self.push_state("settings")

            if key == "main_menu":
                action = lambda: (sound_manager.play("exit_state.wav"), self.set_state("main_menu", mute = True))
                self.push_state("confirm_choice", action = action, header = "Return to Main Menu?", mute = True)

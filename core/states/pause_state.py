import pygame

from core.state_registry import StateRegistry
from core.states.base_state import State
from render import theme

@StateRegistry.register_state("pause")
class PauseState(State):
    is_overlay = True
    is_menu = True

    def __init__(self, app):
        super().__init__(app)
        self.app.apply_display_mode()
        self.ui_cols = 2
        self.app.sound.update_music_volume(multiplier = 0.1)

    def exit(self, **kwargs):
        super().exit(**kwargs)
        self.app.sound.update_music_volume()
        
    def update(self, dt):
        pass

    def draw(self, screen):
        super().draw(screen)
        W, H = self.app.base_w, self.app.base_h
        
        panel_w = int(W * 0.45)
        panel_h = int(H * 0.25)
        panel_rect = pygame.Rect(W // 2 - panel_w // 2,
                                 H // 2 - panel_h // 2,
                                 panel_w, panel_h)
        
        buttons = [("resume", "Resume", theme.GREEN, theme.GREEN_HOVER),
                   ("reset", "Reset", theme.BLUE, theme.BLUE_HOVER),
                   ("settings", "Settings", theme.ORANGE, theme.ORANGE_HOVER),
                   ("main_menu", "Main Menu", theme.RED, theme.RED_HOVER)]
        
        self.app.renderer.draw_overlay(self, screen,
                                       title = "Paused", buttons = buttons,
                                       title_size = 0.35,
                                       title_y = 0.25, btn_y = 0.8,
                                       panel_rect = panel_rect)

    def handle_event(self, event):
        super().handle_event(event)
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = self.app.window_to_base(event.pos)
            key = self.hit_test(mouse_pos)

            if key == "resume":
                self.pop_state(mute = True)
            if key == "reset":
                self.push_state("confirm_choice", action = lambda: self.set_state("game"), header = "Reset Game?")
            if key == "settings":
                self.push_state("settings")
            if key == "main_menu":
                action = lambda: (self.app.sound.play("exit_state.wav"), self.set_state("main_menu", mute = True))
                self.push_state("confirm_choice", action = action, header = "Return to Main Menu?", mute = True)
                self.app.sound.play("exit_state.wav")
